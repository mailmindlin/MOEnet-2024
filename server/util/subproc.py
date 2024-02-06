from typing import TYPE_CHECKING, Optional, TypeVar, Callable, Type, Any, Generic, Union
from multiprocessing import Process, get_context
from abc import ABC, abstractproperty
from queue import Full, Empty
import time

if TYPE_CHECKING:
	import logging
	from multiprocessing.context import BaseContext
	from multiprocessing.queues import Queue
	from multiprocessing.process import BaseProcess

T = TypeVar('T')

M = TypeVar('M')
"Message type"

C = TypeVar('C')
"Command type"

class Subprocess(Generic[M, C], ABC):
	proc: Process
	cmd_queue: 'Queue[C]'
	msg_queue: 'Queue[M]'

	enabled = True

	def __init__(self, name: str, *, log: Optional['logging.Logger'] = None, cmd_queue: Union['Queue[C]', int, None] = None, msg_queue: Union['Queue[M]', int, None] = None, daemon: bool = True, ctx: Optional['BaseContext'] = None) -> None:
		if ctx is None:
			self._ctx = get_context('spawn')
		else:
			self._ctx = ctx
		
		self.log = log
		self.name = name
		self.daemon = daemon

		self.cmd_queue = self._make_queue(cmd_queue)
		self.msg_queue = self._make_queue(msg_queue)
		self._handlers: list[tuple[Type[Any], Callable[[Any], None]]] = []
		self.proc = None
	
	def _make_queue(self, arg: Union['Queue[T]', int, None]) -> 'Queue[T]':
		if arg is None:
			return self._ctx.Queue()
		elif isinstance(arg, int):
			return self._ctx.Queue(arg)
		else:
			return arg
	
	def add_handler(self, msg: Type[M], callback: Callable[[M], None]):
		self._handlers.append((msg, callback))
	
	def handle_default(self, msg: M):
		"Default message handler"
		print("Unknown message:", repr(msg))
	
	def handle_dead(self):
		pass

	def _get_args(self):
		"Get args for subprocess"
		return [self.cmd_queue, self.msg_queue]

	def make_stop_command(self) -> C:
		raise NotImplementedError()
	
	@abstractproperty
	def target(self): ...
	
	def _make_process(self) -> 'BaseProcess':
		return self._ctx.Process(
			target=self.target,
			name=self.name,
			args=self._get_args(),
			daemon=self.daemon,
		)

	def __enter__(self):
		self.start()
		return self
	
	def __exit__(self, *args):
		self.stop()
	
	def send(self, command: C, block: bool = True, timeout: float = 1.0):
		try:
			self.cmd_queue.put(
				command,
				block=block,
				timeout=timeout
			)
		except Full:
			pass

	def start(self):
		"Start subprocess"
		if self.proc is not None:
			# self.log.warning('Started twice!')
			return False
		
		if not self.enabled:
			return
		
		self.proc = self._make_process()
		self.proc.start()
		return True
	
	def _handle(self, msg: M):
		for (msg_type, handler) in self._handlers:
			if not isinstance(msg, msg_type):
				continue
			res = handler(msg)
			if res is not None:
				pass
	
	def poll(self):
		"Process messages from worker"
		if self.proc is None:
			return
		
		is_alive = True
		while True:
			if is_alive:
				is_alive = self.proc.is_alive()
			
			try:
				# We want to process any remaining packets even if the process died
				# but we know we don't need to block on the queue then
				msg = self.msg_queue.get(block=is_alive, timeout=0.01)
			except Empty:
				break
			else:
				for msg_type, handler in self._handlers:
					if isinstance(msg, msg_type):
						res = handler(msg)
						break
				else:
					res = self.handle_default(msg)

				if res is not None:
					yield res
		if not is_alive:
			self.handle_dead()

	def close_queues(self):
		self.cmd_queue.close()
		self.msg_queue.close()
	
	def stop(self, *, ask: bool = True, timeout: Optional[float] = None):
		if self.proc is None:
			return
		
		t0 = time.time()
		def timeout_remaining(default: Optional[float] = None):
			if timeout is None:
				return default
			elapsed = time.time() - t0
			return timeout - elapsed
		
		try:
			self.log.info('Stopping...')
			if ask and self.proc.is_alive():
				# Try stopping nicely
				try:
					cmd_stop = self.make_stop_command()
				except NotImplementedError:
					if self.log: self.log.debug('Unable to send stop command: not implemented')
				else:
					try:
						self.cmd_queue.put(cmd_stop, block=(timeout is not None), timeout=timeout)
					except Full:
						if self.log: self.log.info('Unable to send stop command: queue full')
			
			# Now join nicely
			if (timeout_join := timeout_remaining(1.0)) > 0:
				try:
					self.proc.join(timeout_join)
				except:
					self.log.exception("Error on join")
			
			# Kill it
			if self.proc.is_alive():
				self.proc.kill()
			
			try:
				self.proc.join()
			except:
				self.log.exception('Exception on join')
		finally:
			self.log.debug("close")
			self.proc.close()
			self.close_queues()
		
		self.proc = None
		self.log.info("Stopped")