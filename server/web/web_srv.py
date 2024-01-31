from typing import TYPE_CHECKING
import multiprocessing as mp
from queue import Full, Empty
from . import typedef as ty

if TYPE_CHECKING:
    from ..moenet import MoeNet

def app_main(config, msgq, cmdq, vidq):
    # Lazy import
    from .app import app_main
    app_main(config, msgq, cmdq, vidq)


class RemoteWebServer:
    "Cross-process comms to WebServer"
    def __init__(self, moenet: 'MoeNet') -> None:
        self.moenet = moenet
        if not moenet.config.web.enabled:
            self.vidq = None
            return
        
        self.ctx = mp.get_context('spawn')
        self.msgq = self.ctx.Queue(10)
        self.cmdq = self.ctx.Queue(10)
        self.vidq = self.ctx.Queue(4)
        self.proc = self.ctx.Process(
            name='web',
            target=app_main,
            args=(
                moenet.config.web,
                self.msgq,
                self.cmdq,
                self.vidq,
            )
        )
        self.proc.start()
    
    def poll(self):
        if not self.moenet.config.web.enabled:
            return
        try:
            msg = self.msgq.get_nowait()
        except Empty:
            return
        
        if isinstance(msg, ty.MsgRequest):
            if msg.target == 'config':
                payload = self.moenet.config
            elif msg.target == 'streams':
                payload = []
                for worker in (self.moenet.camera_workers or []):
                    if pipeline := worker.config.pipeline:
                        if pipeline.debugLeft: payload.append(ty.StreamInfo(worker=worker.name, name='left'))
                        if pipeline.debugRight: payload.append(ty.StreamInfo(worker=worker.name, name='right'))
                        if pipeline.debugRgb: payload.append(ty.StreamInfo(worker=worker.name, name='rgb'))
                payload.append(ty.StreamInfo(worker='fake', name='fake'))
            else:
                payload = None
            try:
                self.cmdq.put(
                    ty.CmdResponse(
                        id=msg.id,
                        target=msg.target,
                        payload=payload
                    ),
                    block=True,
                    timeout=1.0
                )
            except Full:
                print('CmdQueue full')
        elif isinstance(msg, ty.MsgRequestStream):
            if workers := self.moenet.camera_workers:
                workers.enable_stream(msg.worker, msg.name, msg.enable)
        else:
            print(f"[web] Unknown message: {repr(msg)}")
    
    def close(self):
        self.proc.close()
        del self.moenet