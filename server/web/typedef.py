from pydantic import BaseModel, Field, RootModel
from typing import Literal, Any
from typedef.cfg import WebConfig
from typedef.worker import MsgFrame

class MsgRequest(BaseModel):
    id: int
    target: Literal['config', 'streams']

class StreamInfo(BaseModel):
    worker: str
    name: str

Streams = RootModel[list[StreamInfo]]

class CmdResponse(BaseModel):
    id: int
    target: str
    payload: Any

class MsgRequestStream(BaseModel):
    worker: str
    name: str
    enable: bool = Field(True)