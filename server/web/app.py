import asyncio
import json
import logging
import os, time
from pathlib import Path
import platform
import ssl
from typing import Any, Coroutine, Optional, Union, Awaitable, Any, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, Lock
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse

from yarl import URL
from . import typedef as ty
from queue import Queue, Empty, Full

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import VideoStreamTrack, VIDEO_TIME_BASE
from aiortc.contrib.media import MediaRelay
from aiortc.rtcrtpsender import RTCRtpSender
from dataclasses import dataclass
from av.video.frame import VideoFrame

if TYPE_CHECKING:
	from ..typedef.cfg import LocalConfig

ROOT = os.path.dirname(__file__)


class IPCTrack(VideoStreamTrack):
	def __init__(self) -> None:
		super().__init__()
		self._queue: asyncio.Queue[ty.MsgFrame] = asyncio.Queue(40)
	
	def provide_frame(self, frame: ty.MsgFrame):
		try:
			self._queue.put_nowait(frame)
		except (asyncio.QueueFull, asyncio.TimeoutError):
			pass
	
	def get_raw(self):
		return self._queue.get()

	async def recv(self):
		raw = await self.get_raw()
		time_ex = time.time_ns()
		print((raw.timestamp_recv - raw.timestamp)/1e6, (raw.timestamp_insert - raw.timestamp_recv)/1e6, (raw.timestamp_extract - raw.timestamp_insert) / 1e6, (time_ex - raw.timestamp_extract)/1e6)
		if raw.data.shape[-1] == 3:
			frame = VideoFrame.from_ndarray(raw.data, 'bgr24')
		else:
			frame = VideoFrame.from_ndarray(raw.data, 'gray8')
		frame.pts = raw.sequence
		frame.time_base = VIDEO_TIME_BASE
		# print(frame, frame.width, frame.height)
		return frame

	def stop(self) -> None:
		return super().stop()

@dataclass
class StreamInfo:
	track: IPCTrack
	relay: MediaRelay
	subscribers: int = 0

	async def provide_frame(self, frame: ty.MsgFrame):
		return self.track.provide_frame(frame)

	def subscribe(self):
		# self.subscribers += 1
		# return self.relay.subscribe(self.track)
		return self.track


def force_codec(pc: RTCPeerConnection, sender: RTCRtpSender, forced_codec: str):
	kind = forced_codec.split("/")[0]
	codecs = RTCRtpSender.getCapabilities(kind).codecs
	transceiver = next(t for t in pc.getTransceivers() if t.sender == sender)
	transceiver.setCodecPreferences(
		[codec for codec in codecs if codec.mimeType == forced_codec]
	)

async def index(request):
	content = open(os.path.join(ROOT, "static/index.html"), "r").read()
	return web.Response(content_type="text/html", text=content)

class JsStatic(web.StaticResource):
	def url_for(self, *, filename: str | Path, append_version: bool | None = None) -> URL:
		filename = Path(filename)
		if not filename.endswith('.js'):
			filename = filename.with_suffix('.js')
		return super().url_for(filename=filename, append_version=append_version)
	def _handle(self, request: Request) -> Coroutine[Any, Any, StreamResponse]:
		rel_url = request.match_info["filename"]
		if not rel_url.endswith('.js'):
			request.match_info['filename'] = rel_url + '.js'
		return super()._handle(request)

class JsStaticDef(web.StaticDef):
	def register(self, router: web.UrlDispatcher) -> list[web.AbstractRoute]:
		prefix = self.prefix
		assert prefix.startswith("/")
		if prefix.endswith("/"):
			prefix = prefix[:-1]
		resource = JsStatic(
			prefix,
			self.path,
			**self.kwargs
		)
		router.register_resource(resource)
		routes = resource.get_info().get("routes", {})
		return list(routes.values())


async def web_get_schema(req: web.Request):
	from typedef.cfg import LocalConfig
	schema = LocalConfig.model_json_schema()
	return web.Response(
		content_type='application/json',
		text=json.dumps(schema),
	)

class WebServer:
	def __init__(self, config: ty.WebConfig, msgq: Queue, cmdq: Queue, vidq: Queue[ty.MsgFrame]) -> None:
		self.config = config
		self.msgq = msgq
		self.cmdq = cmdq
		self.rsp_dispatch: dict[int, asyncio.Future] = dict()
		"Dispatch CmdResponse's"
		self.vidq = vidq
		self.stream_info: dict[tuple[str, str], StreamInfo] = dict()
		"Dispatch video frames"
		self._dispatch_lock = Lock()
		self._last_id = 0
		self._executor = ThreadPoolExecutor(max_workers=1)
		self._loop = asyncio.get_event_loop()
		self._cmd_thread = Thread(
			name='read_cmd',
			target=self.read_cmd,
			daemon=True,
		)
		self._vid_thread = Thread(
			name='read_vid',
			target=self.read_frame,
			daemon=True,
		)
		self.pcs: set[RTCPeerConnection] = set()
	
	def read_cmd(self):
		while True:
			cmd = self.cmdq.get()
			if isinstance(cmd, ty.CmdResponse):
				if handler := self.rsp_dispatch.pop(cmd.id, None):
					handler.set_result(cmd.payload)
	
	def read_frame(self):
		while True:
			frame = self.vidq.get()
			frame.timestamp_extract = time.time_ns()
			if handler := self.stream_info[(frame.worker, frame.stream)]:
				self._loop.run_until_complete(handler.provide_frame(frame))
	
	async def send_msg(self, msg):
		loop = asyncio.get_event_loop()
		return await loop.run_in_executor(self._executor, self.msgq.put, msg)
	
	async def await_response(self, msg, id: int, timeout: float = 1):
		loop = asyncio.get_event_loop()
		future = asyncio.Future(loop=asyncio.get_event_loop())
		if not await loop.run_in_executor(self._executor, lambda: self._dispatch_lock.acquire(timeout=timeout)):
			raise TimeoutError()
		try:
			self.rsp_dispatch[id] = future
		finally:
			self._dispatch_lock.release()

		try:
			async with asyncio.timeout(1):
				await self.send_msg(msg)
				return await future
		finally:
			if await loop.run_in_executor(self._executor, lambda: self._dispatch_lock.acquire(timeout=timeout)):
				try:
					self.rsp_dispatch.pop(id, None)
				finally:
					self._dispatch_lock.release()
	
	def request(self, type: str, timeout: float = 1):
		"Request data from parent"
		id = self._last_id
		self._last_id += 1
		msg = ty.MsgRequest(
			id=id,
			target=type
		)
		return self.await_response(msg, id, timeout=timeout)

	async def web_get_config(self, request: web.Request):
		try:
			rsp: 'LocalConfig' = await self.request('config')
		except asyncio.TimeoutError:
			return web.Response(
				status=500,
				text='{"error": "timeout"}'
			)
		text = rsp.model_dump_json()
		
		return web.Response(
			content_type='application/json',
			text=rsp.model_dump_json(),
		)

	async def web_list_streams(self, request: web.Request):
		try:
			rsp = await self.request('streams')
			rsp = ty.Streams(rsp)
		except asyncio.TimeoutError:
			return web.Response(
				status=500,
				text='{"error": "timeout"}'
			)
		
		return web.Response(
			content_type='application/json',
			text=rsp.model_dump_json(),
		)
	
	async def get_stream(self, worker: str, name: str) -> StreamInfo:
		if prev := self.stream_info.get((worker, name), None):
			return prev
		
		info = StreamInfo(
			relay=MediaRelay(),
			track=IPCTrack(),
		)
		self.stream_info[(worker, name)] = info
		await self.send_msg(ty.MsgRequestStream(
			worker=worker,
			name=name,
			enable=True
		))
		return info
		
	async def web_offer(self, request: web.Request):
		params = await request.json()
		offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

		pc = RTCPeerConnection()
		self.pcs.add(pc)

		@pc.on("connectionstatechange")
		async def on_connectionstatechange():
			for _ in range(10):
				print("Connection state is %s" % pc.connectionState)
			if pc.connectionState == "failed":
				await pc.close()
				self.pcs.discard(pc)

		# open media source
		info = await self.get_stream(params['worker'], params['stream'])
		video = info.subscribe()

		pc.addTrack(video)

		await pc.setRemoteDescription(offer)

		answer = await pc.createAnswer()
		await pc.setLocalDescription(answer)

		return web.Response(
			content_type="application/json",
			text=json.dumps(
				{"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
			),
		)
	
	async def on_shutdown(self, app):
		# close peer connections
		coros = [pc.close() for pc in self.pcs]
		await asyncio.gather(*coros)
		self.pcs.clear()
	
	def run(self):
		if self.config.cert_file:
			ssl_context = ssl.SSLContext()
			ssl_context.load_cert_chain(self.config.cert_file, self.config.key_file)
		else:
			ssl_context = None

		app = web.Application()
		app.on_shutdown.append(self.on_shutdown)
		app.add_routes([
			web.get('/', index),
			JsStaticDef('/js', os.path.join(ROOT, "static/js"), {'append_version': False}),
			web.static('/node_modules', os.path.join(ROOT, "static/node_modules"), append_version=True),
			web.static('/ts', os.path.join(ROOT, "static/ts"), append_version=True),
			web.static('/css', os.path.join(ROOT, "static/css")),
			web.post('/api/stream', self.web_offer),
			web.get('/api/schema', web_get_schema),
			web.get('/api/config', self.web_get_config),
			web.get('/api/streams', self.web_list_streams),
		])
		self._cmd_thread.start()
		self._vid_thread.start()
		web.run_app(app, host=self.config.host, port=self.config.port, ssl_context=ssl_context)

def app_main(config: ty.WebConfig, msgq: Queue, cmdq: Queue, vidq: Queue):
	app = WebServer(config, msgq, cmdq, vidq)
	app.run()

if __name__ == "__main__":
	import argparse
	msgq = Queue(1)
	cmdq = Queue(1)
	parser = argparse.ArgumentParser(description="WebRTC webcam demo")
	parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
	parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
	parser.add_argument("--play-from", help="Read the media from a file and sent it.")
	parser.add_argument(
		"--play-without-decoding",
		help=(
			"Read the media without decoding it (experimental). "
			"For now it only works with an MPEGTS container with only H.264 video."
		),
		action="store_true",
	)
	parser.add_argument(
		"--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
	)
	parser.add_argument(
		"--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
	)
	parser.add_argument("--verbose", "-v", action="count")
	parser.add_argument(
		"--audio-codec", help="Force a specific audio codec (e.g. audio/opus)"
	)
	parser.add_argument(
		"--video-codec", help="Force a specific video codec (e.g. video/H264)"
	)

	args = parser.parse_args()

	config = ty.WebConfig(
		enabled=True,
		host=args.host,
		port=args.port,
		video_codec=args.video_codec,
		cert_file=args.cert_file,
		key_file=args.key_file
	)

	if args.verbose:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig(level=logging.INFO)
	
	app = WebServer(config, msgq, cmdq)
	app.run()