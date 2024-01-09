from typing import TypeVar, Callable, Optional, List, TYPE_CHECKING, Generic, Protocol, overload, Any, Union
from typedef.cfg import LocalConfig, RemoteConfig
from ntcore import (
	NetworkTableInstance,
	PubSubOptions,
	IntegerPublisher,
	IntegerSubscriber,
	StringPublisher,
	StringSubscriber,
	BooleanPublisher,
	BooleanSubscriber,
	RawPublisher,
	RawSubscriber,
	TimestampedInteger,
	NetworkTable,
)
from enum import IntEnum
import logging

if TYPE_CHECKING:
	from .main import MoeNet

P = TypeVar("P", bool, int, float, str, List[bool], List[int], List[float], List[str])
T = TypeVar("T")

logging.basicConfig(level=logging.DEBUG)

class Status(IntEnum):
	NOT_READY = 0
	INITIALIZING = 1
	SLEEPING = 2
	READY = 2
	ERROR = 3

class ProtoPublisher(Protocol, Generic[P]):
	def close(self) -> None: ...
	# def getTopic(self) -> 'ProtoTopic[P]': ...
	def set(self, value: P, time: int = 0) -> None: ...
	def setDefault(self, value: P) -> None: ...

class ProtoTsValue(Protocol, Generic[P]):
	@overload
	def __init__(self) -> None: ...
	@overload
	def __init__(self, time: int, serverTime: int, value: P) -> None: ...
	def __repr__(self) -> str: ...
	@property
	def serverTime(self) -> int: ...
	@serverTime.setter
	def serverTime(self, arg0: int) -> None: ...
	@property
	def time(self) -> int: ...
	@time.setter
	def time(self, arg0: int) -> None: ...
	@property
	def value(self) -> P: ...
	@value.setter
	def value(self, arg0: P) -> None: ...

class ProtoSubscriber(Protocol, Generic[P]):
	def __enter__(self) -> 'ProtoSubscriber[P]': ...
	def __exit__(self, *args) -> None: ...
	def close(self) -> None: ...
	@overload
	def get(self) -> P: ...
	@overload
	def get(self, defaultValue: P) -> P: ...
	@overload
	def getAtomic(self) -> ProtoTsValue[P]: ...
	@overload
	def getAtomic(self, defaultValue: P) -> ProtoTsValue[P]: ...
	# def getTopic(self) -> 'ProtoTopic[P]': ...
	def readQueue(self) -> List[Any]: ...

class ProtoEntry(ProtoSubscriber[P], ProtoPublisher[P], Protocol, Generic[P]):
	# def __enter__(self) -> 'ProtoEntry[P]': ...
	# def __exit__(self, *args) -> None: ...
	# def close(self) -> None: ...
	# def getTopic(self) -> 'ProtoTopic[P]': ... 
	# def unpublish(self) -> None: ...
	...

class ProtoTopic(Protocol, Generic[P]):
	def close(self) -> None:
		...
	def getEntry(self, defaultValue: P, options: PubSubOptions = ...) -> ProtoEntry[P]: 
		...
	def getEntryEx(self, typeString: str, defaultValue: P, options: PubSubOptions = ...) -> ProtoEntry[P]: 
		...
	def publish(self, options: PubSubOptions = ...) -> ProtoPublisher[P]: 
		...
	# def publishEx(self, typeString: str, properties: json, options: PubSubOptions = ...) -> ProtoPublisher[P]: 
	# 	...
	def subscribe(self, defaultValue: P, options: PubSubOptions = ...) -> ProtoSubscriber[P]: 
		...
	def subscribeEx(self, typeString: str, defaultValue: P, options: PubSubOptions = ...) -> ProtoSubscriber[P]: 
		...

class DynamicPublisher(Generic[P]):
	def __init__(self, builder: Callable[[], ProtoPublisher[P]]) -> None:
		super().__init__()
		self._builder = builder
		self._handle = None
	
	@property
	def enabled(self) -> bool:
		return (self._handle is not None)

	@enabled.setter
	def enabled(self, enabled: bool):
		if enabled == (self.enabled):
			return
		elif enabled:
			self._handle = self._builder()
		else:
			self._handle.close()
			self._handle = None
	
	def close(self):
		self.enabled = False

	def set(self, value: P, time: int = 0):
		if self._handle:
			self._handle.set(value, time)

class DynamicSubscriber(Generic[P]):
	def __init__(self, builder: Callable[[], ProtoSubscriber[P]]) -> None:
		super().__init__()
		self._builder = builder
		self._handle = None
		self._fresh_time = None
	
	@property
	def enabled(self) -> bool:
		return (self._handle is not None)

	@enabled.setter
	def enabled(self, enabled: bool):
		if enabled == (self.enabled):
			return
		elif enabled:
			self._handle = self._builder()
		else:
			self._handle.close()
			self._handle = None
			self._fresh_time = None
	
	def close(self):
		self.enabled = False
	
	def get(self, default: Optional[T] = None) -> Union[P, T]:
		if self._handle is None:
			return default
		else:
			return self._handle.get(default)
	
	@overload
	def get_fresh(self) -> Optional[P]: ...
	@overload
	def get_fresh(self, default: T) -> Union[P, T]: ...
	def get_fresh(self, default: T = None) -> Union[P, T]:
		if self._handle is None:
			return default
		at = self._handle.getAtomic()
		if (at.serverTime != self._fresh_time):
			self._fresh_time = at.serverTime
			return at.value
		else:
			return default

class Comms:
	def __init__(self, moenet: 'MoeNet', config: LocalConfig):
		self.moenet = moenet
		self.config = config
		self.log = logging.Logger('Comms', level=logging.DEBUG)
		self.ping_id = 0

		self._pub_ping   = DynamicPublisher(lambda: self.table.getIntegerTopic("client_ping").publish(PubSubOptions()))
		self._pub_error  = DynamicPublisher(lambda: self.table.getStringTopic("client_error").publish(PubSubOptions(sendAll=True)))
		self._pub_log    = DynamicPublisher(lambda: self.table.getStringTopic("client_log").publish(PubSubOptions(sendAll=True)))
		self._pub_status = DynamicPublisher(lambda: self.table.getIntegerTopic("client_status").publish(PubSubOptions(sendAll=True)))
		self._pub_config = DynamicPublisher(lambda: self.table.getStringTopic("client_config").publish(PubSubOptions(sendAll=True, periodic=1)))
		self._pub_telem  = DynamicPublisher(lambda: self.table.getIntegerTopic("client_telemetry").publish(PubSubOptions(periodic=0.5)))
		self._pub_tf_field_odom  = DynamicPublisher(lambda: self.table.getIntegerTopic("tf_field_odom").publish(PubSubOptions(periodic=0.01)))
		self._pub_tf_field_robot = DynamicPublisher(lambda: self.table.getIntegerTopic("tf_field_robot").publish(PubSubOptions(periodic=0.01)))
		self._pub_tf_odom_robot  = DynamicPublisher(lambda: self.table.getIntegerTopic("tf_odom_robot").publish(PubSubOptions(periodic=0.01)))

		self._pub_det_rs = DynamicPublisher(lambda: self.table.getDoubleArrayTopic("client_det_rs").publish(PubSubOptions(periodic=0.01)))
		self._pub_det_fs = DynamicPublisher(lambda: self.table.getDoubleArrayTopic("client_det_fs").publish(PubSubOptions(periodic=0.01)))

		self._sub_tf_field_odom  = DynamicSubscriber(lambda: self.table.getIntegerTopic("tf_field_odom").subscribe(PubSubOptions(periodic=0.01, disableLocal=True)))
		self._sub_tf_field_robot = DynamicSubscriber(lambda: self.table.getIntegerTopic("tf_field_robot").subscribe(PubSubOptions(periodic=0.01, disableLocal=True)))
		self._sub_tf_odom_robot  = DynamicSubscriber(lambda: self.table.getIntegerTopic("tf_odom_robot").subscribe(PubSubOptions(periodic=0.01, disableLocal=True)))

		self._sub_config = DynamicSubscriber(lambda: self.table.getStringTopic("rio_config").subscribe("", PubSubOptions()))
		self._sub_sleep  = DynamicSubscriber(lambda: self.table.getBooleanTopic("rio_sleep").subscribe(False, PubSubOptions()))

		if not self.config.nt.enabled:
			self.log.warn("NetworkTables is disabled")
			self.nt = None
			self.table = None
			return
		
		self.nt = NetworkTableInstance.create()
		if config.nt.client_id is not None:
			self.log.info("Setting NetworkTables identity to %s", config.nt.client_id)
			# self.nt.setNetworkIdentity(config.client_id)
			nt_id = config.nt.client_id
		else:
			nt_id = 'moenet'
		
		if config.nt.host is not None:
			self.log.info("Starting client with host %s (port=%d)", config.nt.host, config.nt.port)
			# self.nt.startClient((config.nt.host, config.nt.port))
			self.nt.setServer(config.nt.host, config.nt.port)
		else:
			self.log.info("Starting client for team %s (port=%d)", config.nt.team, config.nt.port)
			# self.nt.startClientTeam(config.nt.team, config.nt.port)
			self.nt.setServerTeam(config.nt.team, config.nt.port)
		
		self.nt.startClient4(nt_id)
		
		self.table = self.nt.getTable(config.nt.table)
		self._reset()

		if (self._pub_config is not None):
			self._pub_config.set(config.json())
	
	def update_config(self, config: LocalConfig):
		self.config = config
		self._reset()

		if self._pub_config.enabled:
			self._pub_config.set(config.json())
	
	def _reset(self):
		"Reset NT handles based on config"
		if self.table is None:
			return
		
		ntc = self.config.nt
		self._pub_ping.enabled = ntc.publishPing
		self._pub_error.enabled = ntc.publishErrors
		self._pub_log.enabled = ntc.publishLog
		self._pub_status.enabled = ntc.publishStatus
		self._pub_config.enabled = ntc.publishConfig
		self._pub_telem.enabled = ntc.publishSystemInfo
		self._pub_tf_field_odom.enabled = ntc.tfFieldToOdom == 'pub'
		self._pub_tf_field_robot.enabled = ntc.tfFieldToRobot == 'pub'
		self._pub_tf_odom_robot.enabled = ntc.tfOodomToRobot == 'pub'
		self._pub_det_rs.enabled = ntc.publishDetectionsRs
		self._pub_det_fs.enabled = ntc.publishDetectionsFs

		self._sub_tf_field_odom.enabled = ntc.tfFieldToOdom == 'sub'
		self._sub_tf_field_robot.enabled = ntc.tfFieldToRobot == 'sub'
		self._sub_tf_odom_robot.enabled = ntc.tfOodomToRobot == 'sub'

		self._sub_config.enabled = ntc.subscribeConfig
		self._sub_sleep.enabled  = ntc.subscribeSleep

	def update(self):
		# Send ping
		if self._pub_ping is not None:
			self._pub_ping.set(self.ping_id)
			self.ping_id += 1
		
		if (new_cfg := self._sub_config.get_fresh(None)) is not None:
			try:
				new_cfg = RemoteConfig.parse_raw(new_cfg)
			except:
				logging.exception("Error parsing client config")
			else:
				self.moenet.update_config(new_cfg)
		
		if self._sub_sleep.enabled:
			sleep = self._sub_sleep.get()
			self.moenet.sleeping = sleep

	
	def tx_error(self, message: str):
		self._pub_error.set(message)
		self.log.warn("NT Error: %s", message)

	def tx_status(self, status: Status):
		self._pub_status.set(int(status))
		self.log.info("NT send status: %s", status)

	def tx_pose(self, pose):
		pass

	def tx_detections(self, detections: List):
		pass

	def rx_sleep(self) -> bool:
		return self._sub_sleep.get(False)