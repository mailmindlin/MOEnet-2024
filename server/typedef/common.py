from typing import Literal, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field, RootModel
from datetime import timedelta
if TYPE_CHECKING:
	import depthai as dai

Vec4 = RootModel[tuple[float, float, float, float]]
Mat44 = RootModel[tuple[Vec4, Vec4, Vec4, Vec4]]

class RetryConfig(BaseModel):
	"Configure restart/retry logic"
	optional: bool = Field(False, description="Is it an error if this camera is not detected?")
	connection_tries: int = Field(1)
	connection_delay: timedelta = Field(timedelta(seconds=1))
	restart_tries: int = Field(2)


class OakSelector(BaseModel):
	ordinal: Optional[int] = Field(None, description="Pick the n-th camera found (unstable, starts at 1)", ge=1)
	mxid: Optional[str] = Field(None, description="Filter camera by mxid")
	devname: Optional[str] = Field(None, description="Filter camera by device name")
	platform: Literal["X_LINK_ANY_PLATFORM", "X_LINK_MYRIAD_2", "X_LINK_MYRIAD_X", None] = Field(None)
	protocol: Literal["X_LINK_ANY_PROTOCOL", "X_LINK_IPC", "X_LINK_NMB_OF_PROTOCOLS", "X_LINK_PCIE", "X_LINK_TCP_IP", "X_LINK_USB_CDC", "X_LINK_USB_VSC", None] = Field(None)

	@property
	def platform_dai(self) -> 'dai.XLinkPlatform':
		"Get platform as DepthAI type"
		raw = self.platform
		if raw is None:
			return None
		from depthai import XLinkPlatform
		return XLinkPlatform.__members__[raw]
	
	@property
	def protocol_dai(self) -> 'dai.XLinkProtocol':
		"Get platform as DepthAI type"
		raw = self.protocol
		if raw is None:
			return None
		from depthai import XLinkProtocol
		return XLinkProtocol.__members__[raw]
