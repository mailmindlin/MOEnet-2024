from __future__ import annotations
from multiprocessing.context import BaseContext
from multiprocessing.queues import Queue
from typing import TYPE_CHECKING, Optional, Union
import logging
from multiprocessing import Process, get_context
from queue import Empty
from pathlib import Path
from logging import Logger

from wpiutil.log import DataLog, StringLogEntry, IntegerLogEntry

from . import msg as worker
from .resolver import WorkerConfigResolver
from typedef.cfg import LocalConfig
from util.subproc import Subprocess
from util.log import child_logger

if TYPE_CHECKING:
	from multiprocessing.context import BaseContext
	from queue import Queue

class WorkerManager:
	def __init__(self, log: Logger, config: LocalConfig, config_path: Optional[Path] = None, datalog: Optional['DataLog'] = None, vidq: Optional['Queue'] = None) -> None:
		self.log = log.getChild('worker')
		self.config = WorkerConfigResolver(self.log, config, config_path)
		self._workers: list['WorkerHandle'] = list()
		self.datalog = datalog
		self.ctx = get_context('spawn')
		self.video_queue = vidq

	def start(self):
		"Start all camera processes"
		for i, cfg in enumerate(self.config):
			name = cfg.name if cfg.name is not None else f'cam_{i}'
			wh = WorkerHandle(name, cfg, log=self.log, datalog=self.datalog, ctx=self.ctx, vidq=self.video_queue)
			self._workers.append(wh)
			wh.start()
	
	def stop(self):
		"Stop camera subprocesses"
		self.log.info("Sending stop command to workers")
		for child in self._workers:
			try:
				child.cmd_queue.put(worker.CmdChangeState(target=worker.WorkerState.STOPPED), block=True, timeout=1.0)
			except ValueError:
				# Command queue was closed
				pass
		
		self.log.info("Stopping workers")
		for child in self._workers:
			child.close()
		self.log.info("Workers stopped")
		self._workers.clear()

		self.config.cleanup()
	
	def enable_stream(self, worker_name: str, stream: str, enable: bool):
		for worker in self._workers:
			if worker.config.name == worker_name:
				worker.enable_stream(stream, enable)
				return True
		return False
	
	def __iter__(self):
		"Iterate through camera handles"
		return self._workers.__iter__()


class WorkerHandle(Subprocess[worker.WorkerMsg, worker.AnyCmd, worker.AnyMsg]):
	def __init__(self, name: str, config: worker.WorkerInitConfig, *, log: logging.Logger | None = None, ctx: BaseContext | None = None, datalog: Optional['DataLog'] = None, vidq: Optional['Queue'] = None):
		if ctx is None:
			ctx = get_context('spawn')
		
		super().__init__(
			name,
			log=child_logger(name, log),
			cmd_queue=0,
			msg_queue=0,
			daemon=True, ctx=ctx)

		self.datalog = datalog
		if datalog is not None:
			logConfig = StringLogEntry(self.datalog, f'worker/{name}/config')
			logConfig.append(config.model_dump_json())
			logConfig.finish()
			del logConfig

			self.logStatus = IntegerLogEntry(self.datalog, f'worker/{name}/status')
			self.logLog = StringLogEntry(self.datalog, f'worker/{name}/log')

		self.config = config
		self.video_queue = vidq
		self._require_flush_id = 0
		self._last_flush_id = 0
		self._restarts = 0
		self.robot_to_camera = config.robot_to_camera
		self.child_state = None
		self._child_state_recv = None
		self._source_pose = None
		self._source_apriltag = None
		self._source_imu = None
		self._source_odom = None
		self.add_handler(worker.MsgLog, self._handle_log)
		self.add_handler(worker.MsgFlush, self._handle_flush)
		self.add_handler(worker.MsgChangeState, self._handle_changestate)

	def _get_args(self):
		return (
			self.config,
			self.msg_queue,
			self.cmd_queue,
			self.video_queue,
		)
	@property
	def target(self):
		from worker.worker import main as worker_main
		return worker_main
	
	def make_stop_command(self) -> worker.AnyCmd:
		return worker.CmdChangeState(target=worker.WorkerState.STOPPED)
	def enable_stream(self, stream: str, enable: bool):
		self.send(worker.CmdEnableStream(stream=stream, enable=enable))
	
	def flush(self):
		self._require_flush_id += 1
		self.send(worker.CmdFlush(id=self._require_flush_id))
	
	# Message handlers
	def _handle_log(self, packet: worker.MsgLog):
		log = self.log if packet.name == 'root' else self.log.getChild(packet.name)
		log.log(packet.level, packet.msg)
		if self.datalog is not None:
			self.logLog.append(f'[{logging.getLevelName(packet.level)}]{packet.name}:{packet.msg}')
	
	def _handle_flush(self, packet: worker.MsgFlush):
		self.log.debug('Finished flush %d', packet.id)
		self._last_flush_id = max(self._last_flush_id, packet.id)
	
	def _handle_changestate(self, packet: worker.MsgChangeState):
		self.child_state = packet.current
		self._child_state_recv = packet.current
		if self.datalog is not None:
			self.logStatus.append(int(self.child_state))
	
	def handle_default(self, msg: worker.WorkerMsg) -> worker.AnyMsg | None:
		if self._last_flush_id < self._require_flush_id:
			# Packets are invalidated by a flush
			self.log.info("Skipping packet (flushed)")
			return None
		else:
			return msg
	
	def handle_dead(self):
		optional = self.config.retry.optional
		self._restarts += 1
		restart_tries = self.config.retry.restart_tries
		can_retry = (restart_tries == -1) or (self._restarts < self.config.retry.restart_tries)
		expected = self._child_state_recv in (worker.WorkerState.STOPPED, worker.WorkerState.FAILED)
		if optional:
			self.log.warning("Exited" if expected else 'Unexpectedly exited')
			self.child_state = worker.WorkerState.STOPPING
		else:
			self.log.error("Exited" if expected else 'Unexpectedly exited')
		# Cleanup process
		self.stop(ask=False)
		self._child_state_recv = None

		if can_retry:
			self.child_state = worker.WorkerState.STOPPED
			self.log.info("Restarting (%d of %s)", self._restarts, restart_tries - 1 if restart_tries >= 0 else '?')
			# TODO: honor connection_delay?
			self.start()
			self.log.info("Restarted")
		elif optional:
			self.child_state = worker.WorkerState.STOPPED
		else:
			self.child_state = worker.WorkerState.FAILED
			raise RuntimeError(f'Camera {self.name} unexpectedly exited')
