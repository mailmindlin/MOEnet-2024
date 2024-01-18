from typing import TypeVar, Callable, Optional, List, TYPE_CHECKING, Generic, Protocol, overload, Any, Union
from ntcore import (
	NetworkTableInstance,
	PubSubOptions,
)
from wpimath.geometry import Pose3d, Transform3d
import logging
try:
	import psutil
except ImportError:
	psutil = None

from typedef.cfg import LocalConfig
from typedef.geom import Pose
from typedef.worker import MsgDetection
from typedef.net import Status

if TYPE_CHECKING:
	from .main import MoeNet


P = TypeVar("P", bool, int, float, str, List[bool], List[int], List[float], List[str])
T = TypeVar("T")

logging.basicConfig(level=logging.DEBUG)

class ProtoPublisher(Protocol, Generic[P]):
	"Interface for NetworkTables' XXXPublisher"
	def close(self) -> None: ...
	# def getTopic(self) -> 'ProtoTopic[P]': ...
	def set(self, value: P, time: int = 0) -> None: ...
	def setDefault(self, value: P) -> None: ...

class ProtoTsValue(Protocol, Generic[P]):
	"Interface for NetworkTables' TimeStampedXXX"
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
	"Interface for NetworkTables' XXXSubscriber"
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

class LogHandler(logging.Handler):
	def __init__(self, comms: 'Comms') -> None:
		super().__init__()
		self.comms = comms
	
	def emit(self, record: LogRecord) -> None:
		try:
			msg = self.format(record)
			if record.levelno >= logging.ERROR:
				self.comms.tx_error(msg)
			else:
				self.comms.tx_log(msg)
		except RecursionError:  # See issue 36272
			raise
		except Exception:
			self.handleError(record)


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
		self._pub_telem_cpu  = DynamicPublisher(lambda: self.table.getSubTable('client_telemetry').getDoubleTopic("cpu").publish(PubSubOptions(periodic=0.5)))
		self._pub_telem_ram  = DynamicPublisher(lambda: self.table.getSubTable('client_telemetry').getDoubleTopic("ram").publish(PubSubOptions(periodic=0.5)))
		self._pub_tf_field_odom: DynamicPublisher[Pose3d]  = DynamicPublisher(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_field_odom", Pose3d).publish(PubSubOptions(periodic=0.01)))
		self._pub_tf_field_robot: DynamicPublisher[Pose3d] = DynamicPublisher(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_field_robotodom", Pose3d).publish(PubSubOptions(periodic=0.01)))
		self._pub_tf_odom_robot: DynamicPublisher[Transform3d]  = DynamicPublisher(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_odom_robot", Transform3d).publish(PubSubOptions(periodic=0.1)))

		self._pub_det_rs = DynamicPublisher(lambda: self.table.getDoubleArrayTopic("client_det_rs").publish(PubSubOptions(periodic=0.01)))
		self._pub_det_fs = DynamicPublisher(lambda: self.table.getDoubleArrayTopic("client_det_fs").publish(PubSubOptions(periodic=0.01)))

		self._sub_tf_field_odom: DynamicSubscriber[Pose3d]  = DynamicSubscriber(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_field_odom", Pose3d).subscribe(PubSubOptions(periodic=0.01, disableLocal=True)))
		self._sub_tf_field_robot: DynamicSubscriber[Pose3d] = DynamicSubscriber(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_field_robot", Pose3d).subscribe(PubSubOptions(periodic=0.01, disableLocal=True)))
		self._sub_tf_odom_robot: DynamicSubscriber[Transform3d]  = DynamicSubscriber(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_odom_robot", Transform3d).subscribe(PubSubOptions(periodic=0.1, disableLocal=True)))

		self._sub_config = DynamicSubscriber(lambda: self.table.getStringTopic("rio_config").subscribe("", PubSubOptions()))
		self._sub_sleep  = DynamicSubscriber(lambda: self.table.getBooleanTopic("rio_sleep").subscribe(False, PubSubOptions()))
		
		# self._handler = LogHandler(self)

		if not self.config.nt.enabled:
			self.log.warn("NetworkTables is disabled")
			self.nt = None
			self.table = None
			return
		
		# Connect to NT
		self.nt = NetworkTableInstance.create()
		self.log.info("Setting NetworkTables identity to %s", config.nt.client_id)
		nt_id = config.nt.client_id
		
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

		self._pub_config.set(config.model_dump_json())

		root_log = logging.getLogger()
		# root_log.addHandler(self._handler)
	
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
		self._pub_telem_cpu.enabled = ntc.publishSystemInfo
		self._pub_telem_ram.enabled = ntc.publishSystemInfo
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
		
		# Check for new config
		if (new_cfg := self._sub_config.get_fresh(None)) is not None:
			self.moenet.update_config(new_cfg)
		
		# Check for sleep
		if self._sub_sleep.enabled:
			sleep = self._sub_sleep.get()
			self.moenet.sleeping = sleep
		
		# Publish telemetry
		if psutil is not None:
			try:
				if self._pub_telem_cpu.enabled:
					self._pub_telem_cpu.set(psutil.cpu_percent())
				if self._pub_telem_ram.enabled:
					self._pub_telem_ram.set(psutil.virtual_memory().percent)
			except Exception:
				self.log.exception("Error publishing telemetry to NT")
		
		# Get odometry
		if (tf_field_odom := self._sub_tf_field_odom.get_fresh(None)) is not None:
			# Probably a better way to do this
			timestamp = self._sub_tf_field_odom._handle.getAtomic().time * 1_000
			self.moenet.pose_estimator.record_f2o(timestamp, tf_field_odom)
		
		# Get field-to-robot
		if (tf_field_robot := self._sub_tf_field_robot.get_fresh(None)) is not None:
			pass

		# Publish transforms
		if self._pub_tf_odom_robot.enabled:
			tf_odom_robot = self.moenet.pose_estimator.odom_to_robot()

	
	def tx_error(self, message: str):
		"Send error message to NetworkTables"
		self._pub_error.set(message)
		# self.log.warn("NT Error: %s", message)
	
	def tx_log(self, message: str):
		"Send error message to NetworkTables"
		self._pub_log.set(message)

	def tx_status(self, status: Status):
		"Send status"
		self._pub_status.set(int(status))
		self.log.info("NT send status: %s", status)

	def tx_pose(self, pose: Pose):
		self._pub_tf_field_robot.set([
			pose.translation.x,
			pose.translation.y,
			pose.translation.z,
			pose.rotation.w,
			pose.rotation.x,
			pose.rotation.y,
			pose.rotation.z,
		])
		#TODO: compute other transforms

	def tx_detections(self, detections: List[MsgDetection]):
		#TODO: fixme
		self._pub_det_rs.set([
			len(detections)
		])

	def rx_sleep(self) -> bool:
		return self._sub_sleep.get(False)

	def close(self):
		self.nt.stopClient()
		del self.moenet