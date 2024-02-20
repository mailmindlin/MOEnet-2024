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

class RemoteWebServer(Subprocess[ty.WMsgAny, ty.WCmdAny, None]):
    "Cross-process comms to WebServer"

    @staticmethod
    def target(config, msgq, cmdq, vidq):
        # Lazy import
        from .app import app_main
        app_main(config, msgq, cmdq, vidq)

    def __init__(self, moenet: 'MoeNet') -> None:
        self.moenet = moenet
        self.proc = None
        if not moenet.config.web.enabled:
            self.vid_queue = None
            return
        
        super().__init__(
            'web',
            daemon=True,
            msg_queue=10,
            cmd_queue=10,
            log=moenet.log.getChild('web'),
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
        config = ty.AppConfig(
            **dict(self.moenet.config.web),
            logs=self.moenet.config.datalog,
        )
        return [
            config,
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
                pipeline = worker.config.pipeline
                if not pipeline: continue

                for stage in pipeline:
                    if stage.stage != 'web': continue
                    if not stage.enabled: continue

                    streams.append(ty.StreamInfo(worker=worker.name, name=stage.target))
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