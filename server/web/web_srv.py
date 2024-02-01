from typing import TYPE_CHECKING, TypeVar
from queue import Full
from . import msg as ty
from util.subproc import Subprocess

if TYPE_CHECKING:
    from ..moenet import MoeNet

def app_main(config, msgq, cmdq, vidq):
    # Lazy import
    from .app import app_main
    app_main(config, msgq, cmdq, vidq)


T = TypeVar('T')

class RemoteWebServer(Subprocess[ty.WMsgAny, ty.WCmdAny]):
    "Cross-process comms to WebServer"

    target = app_main

    def __init__(self, moenet: 'MoeNet') -> None:
        self.moenet = moenet
        if not moenet.config.web.enabled:
            self.vidq = None
            return
        
        super().__init__(
            'web',
            daemon=True,
            msg_queue=10,
            cmd_queue=10,
        )
        self.add_handler(ty.WMsgRequestConfig, self._process_request_config)
        self.add_handler(ty.WMsgRequestStreams, self._process_request_streams)
        self.add_handler(ty.WMsgStreamCtl, self._process_streamctl)

        self.vid_queue = self._make_queue(4)

        self.start()
    
    def close_queues(self):
        self.vid_queue.close()
        return super().close_queues()
    
    @property
    def enabled(self):
        return self.moenet.config.web.enabled
    
    def _get_args(self):
        return [
            self.moenet.config.web,
            self.msg_queue,
            self.cmd_queue,
            self.vid_queue,
        ]
    
    def _respond(self, request: ty.WMsgRequest[T], payload: T):
        cmd = ty.WCmdResponse(
            request_id=request.request_id,
            target=request.target,
            payload=payload
        )

        try:
            self.cmd_queue.put(
                cmd,
                block=True,
                timeout=.1
            )
        except Full:
            print("Queue full")
    

    def _process_request_config(self, msg: ty.WMsgRequestConfig):
        self._respond(msg, self.moenet.config)

    def _process_request_streams(self, msg: ty.WMsgRequestStreams):
        streams = []
        if workers := self.moenet.camera_workers:
            for worker in workers:
                if pipeline := worker.config.pipeline:
                    if pipeline.debugLeft: streams.append(ty.StreamInfo(worker=worker.name, name='left'))
                    if pipeline.debugRight: streams.append(ty.StreamInfo(worker=worker.name, name='right'))
                    if pipeline.debugRgb: streams.append(ty.StreamInfo(worker=worker.name, name='rgb'))
        # Append 'fake' stream
        streams.append(ty.StreamInfo(worker='fake', name='fake'))

        self._respond(msg, ty.Streams(streams))
    
    def _process_streamctl(self, msg: ty.WMsgStreamCtl):
        if workers := self.moenet.camera_workers:
            workers.enable_stream(msg.worker, msg.name, msg.enable)
    
    def close1(self):
        self.close()
        del self.moenet
    
    def stop(self, *, ask = True, timeout: float | None = None):
        try:
            return super().stop(ask=ask, timeout=timeout)
        finally:
            del self.moenet