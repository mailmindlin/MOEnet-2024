"Message typedefs for comms between main/worker processes"

from typing import Literal, Any, Generic, TypeVar, Union
from pydantic import BaseModel, Field, RootModel

from typedef.cfg import WebConfig, LocalConfig, RemoteConfig
from typedef.worker import MsgFrame

R = TypeVar('R')
"Response type"

def auto_increment():
    last_id = 0
    def generator():
        nonlocal last_id
        result = last_id
        last_id += 1
        return result
    return generator

class StreamInfo(BaseModel):
    "Info about a single stream"
    worker: str
    name: str
Streams = RootModel[list[StreamInfo]]

request_idgen = auto_increment()

class WMsgRequest(BaseModel, Generic[R]):
    "Base class for WebServer to request data from main process"
    request_id: int = Field(default_factory=auto_increment(), description="Request id (for matching responses)")
    target: Literal['config', 'streams']

class WMsgRequestConfig(WMsgRequest[LocalConfig]):
    target: Literal['config'] = Field('config')

class WMsgRequestStreams(WMsgRequest[Streams]):
    target: Literal['streams'] = Field('streams')

class WMsgStreamCtl(BaseModel):
    """
    Message to control a video stream
    """
    worker: str
    name: str
    enable: bool = Field(True)

WMsgAny = RootModel[Union[WMsgRequestConfig, WMsgRequestStreams, WMsgStreamCtl]]

class WCmdResponse(BaseModel, Generic[R]):
    "Response to a [WMsgRequest]"
    request_id: int
    target: str
    payload: R

WCmdAny = WCmdResponse