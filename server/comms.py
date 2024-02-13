from typing import TYPE_CHECKING, TypeVar, Optional
import logging
from dataclasses import dataclass

from ntcore import NetworkTableInstance, PubSubOptions
try:
	import psutil
except ImportError:
	psutil = None

from util.timestamp import Timestamp
from util.log import child_logger
from typedef.cfg import LocalConfig, NetworkTablesDirection
from typedef.geom import Pose3d, Transform3d
from typedef import net
from wpi_compat.nt import DynamicPublisher, DynamicSubscriber, ProtobufTopic
from wpiutil import wpistruct

if TYPE_CHECKING:
	from .__main__ import MoeNet


P = TypeVar("P", bool, int, float, str, list[bool], list[int], list[float], list[str])
T = TypeVar("T")


@wpistruct.make_wpistruct(name="ObjectDetection")
@dataclass
class SimpleObjectDetection:
	classsification: wpistruct.dataclass.int32
	confidence: wpistruct.dataclass.double
	objectPose: Pose3d


class LogHandler(logging.Handler):
	def __init__(self, comms: 'Comms') -> None:
		super().__init__()
		self.comms = comms
	
	def emit(self, record: logging.LogRecord) -> None:
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
	def __init__(self, moenet: 'MoeNet', config: LocalConfig, log: Optional[logging.Logger] = None):
		self.moenet = moenet
		self.config = config
		self.log = child_logger('comms', log)
		self.ping_id = 0

		self.labels = list()

		self._pub_ping   = DynamicPublisher(lambda: self.table.getIntegerTopic("client_ping"))
		self._pub_error  = DynamicPublisher(lambda: self.table.getStringTopic("client_error"), PubSubOptions(sendAll=True))
		self._pub_log    = DynamicPublisher(lambda: self.table.getStringTopic("client_log"), PubSubOptions(sendAll=True))
		self._pub_status = DynamicPublisher(lambda: self.table.getIntegerTopic("client_status"), PubSubOptions(sendAll=True))
		self._pub_config = DynamicPublisher(lambda: self.table.getStringTopic("client_config"), PubSubOptions(sendAll=True, periodic=1))
		"Publish config"
		self._pub_telem_cpu  = DynamicPublisher(lambda: self.table.getSubTable('client_telemetry').getDoubleTopic("cpu"), PubSubOptions(periodic=0.5))
		self._pub_telem_ram  = DynamicPublisher(lambda: self.table.getSubTable('client_telemetry').getDoubleTopic("ram"), PubSubOptions(periodic=0.5))
		self._pub_tf_field_odom: DynamicPublisher[Pose3d]  = DynamicPublisher(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_field_odom", Pose3d), PubSubOptions(periodic=0.01))
		self._pub_tf_field_robot: DynamicPublisher[Pose3d] = DynamicPublisher(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_field_robot", Pose3d), PubSubOptions(periodic=0.01))
		self._pub_tf_field_robot2: DynamicPublisher[list[float]] = DynamicPublisher(lambda: self.nt.getDoubleArrayTopic(self.table.getPath() + "/tf_field_robot2"), PubSubOptions(periodic=0.01))
		self._pub_tf_odom_robot: DynamicPublisher[Transform3d]  = DynamicPublisher(lambda: self.nt.getStructTopic(self.table.getPath() + "/tf_odom_robot", Transform3d), PubSubOptions(periodic=0.1))

		self._pub_detections_full = DynamicPublisher(lambda: ProtobufTopic.wrap(self.table, "client_detections_full", net.ObjectDetections), PubSubOptions(periodic=0.05))
		self._pub_detections = DynamicPublisher(lambda: self.table.getStructArrayTopic("client_detections", SimpleObjectDetection), PubSubOptions(periodic=0.05))

		tf_sub_options = PubSubOptions(periodic=0.01, disableLocal=True)
		self._sub_tf_field_odom = DynamicSubscriber(lambda: self.table.getStructTopic('tf_field_odom', Pose3d), Pose3d(), tf_sub_options)
		self._sub_tf_field_robot = DynamicSubscriber(lambda: self.table.getStructTopic('tf_field_robot', Pose3d), Pose3d(), tf_sub_options)
		self._sub_tf_odom_robot = DynamicSubscriber(lambda: self.table.getStructTopic('tf_odom_robot', Transform3d), Transform3d(), tf_sub_options)
		self._sub_pose_override = DynamicSubscriber(lambda: self.table.getStructTopic('rio_pose_override', Pose3d), Pose3d(), PubSubOptions(keepDuplicates=True))

		self._sub_config = DynamicSubscriber(lambda: self.table.getStringTopic("rio_config"), "")
		self._sub_sleep  = DynamicSubscriber(lambda: self.table.getBooleanTopic("rio_sleep"), False)

		# Field2d
		self._pub_f2d_type = DynamicPublisher(lambda: self.nt.getTable("SmartDashboard/MoeNet").getStringTopic(".type"))
		self._pub_f2d_f2o = DynamicPublisher(lambda: self.nt.getTable("SmartDashboard/MoeNet").getDoubleArrayTopic("Odometry"))
		self._pub_f2d_f2r = DynamicPublisher(lambda: self.nt.getTable("SmartDashboard/MoeNet").getDoubleArrayTopic("Robot"))
		self._pub_f2d_dets = DynamicPublisher(lambda: self.nt.getTable("SmartDashboard/MoeNet").getDoubleArrayTopic("Notes"))


		if not self.config.nt.enabled:
			self.log.warning("NetworkTables is disabled")
			self.nt = None
			self.table = None
			return
		
		# Connect to NT
		self.nt = NetworkTableInstance.create()
		self.log.info("Setting NetworkTables identity to %s", config.nt.client_id)
		nt_id = config.nt.client_id
		
		if config.nt.host is not None:
			self.log.info("Starting client with host %s (port=%d)", config.nt.host, config.nt.port)
			self.nt.setServer(config.nt.host, config.nt.port)
		else:
			self.log.info("Starting client for team %s (port=%d)", config.nt.team, config.nt.port)
			self.nt.setServerTeam(config.nt.team, config.nt.port)
		
		self.nt.startClient4(nt_id)
		self.table = self.nt.getTable(config.nt.table)
		self._reset()

		self._pub_config.set(config.model_dump_json())

	def update_config(self, config: LocalConfig):
		self.config = config
		self._reset()

		if self._pub_config.enabled:
			self._pub_config.set(config.model_dump_json())
	
	def _reset(self):
		"Reset NT handles based on config"
		if self.table is None:
			return
		
		ntc = self.config.nt
		self._pub_ping.enabled   = ntc.publishPing
		self._pub_error.enabled  = ntc.publishErrors
		self._pub_log.enabled    = ntc.publishLog
		self._pub_status.enabled = ntc.publishStatus
		self._pub_config.enabled = ntc.publishConfig
		self._pub_telem_cpu.enabled = ntc.publishSystemInfo
		self._pub_telem_ram.enabled = ntc.publishSystemInfo
		self._pub_tf_field_odom.enabled   = (ntc.tfFieldToOdom  == NetworkTablesDirection.PUBLISH)
		self._pub_tf_field_robot.enabled  = (ntc.tfFieldToRobot == NetworkTablesDirection.PUBLISH)
		self._pub_tf_field_robot2.enabled = (ntc.tfFieldToRobot == NetworkTablesDirection.PUBLISH)
		self._pub_tf_odom_robot.enabled   = (ntc.tfOodomToRobot == NetworkTablesDirection.PUBLISH)

		self._pub_detections.enabled      = ntc.publishDetections
		self._pub_detections_full.enabled = ntc.publishDetections

		self._sub_tf_field_odom.enabled = (ntc.tfFieldToOdom == NetworkTablesDirection.SUBSCRIBE)
		self._sub_tf_field_robot.enabled = (ntc.tfFieldToRobot == NetworkTablesDirection.SUBSCRIBE)
		self._sub_tf_odom_robot.enabled = (ntc.tfOodomToRobot == NetworkTablesDirection.SUBSCRIBE)
		self._sub_pose_override.enabled = ntc.subscribePoseOverride

		self._pub_f2d_type.enabled = (ntc.publishField2dF2R or ntc.publishField2dF2O or ntc.publishField2dDets)
		self._pub_f2d_f2o.enabled = ntc.publishField2dF2O
		self._pub_f2d_f2r.enabled = ntc.publishField2dF2R
		self._pub_f2d_dets.enabled = ntc.publishField2dDets

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
					val = psutil.cpu_percent()
					if val != 0:
						self._pub_telem_cpu.set(val)
				if self._pub_telem_ram.enabled:
					self._pub_telem_ram.set(psutil.virtual_memory().percent)
			except Exception:
				self.log.exception("Error publishing telemetry to NT")
		
		# Get odometry
		if (tf_field_odom := self._sub_tf_field_odom.get_fresh_ts()) is not None:
			# Probably a better way to do this
			timestamp = Timestamp.from_wpi(tf_field_odom[1])
			self.moenet.estimator.record_f2o(timestamp, tf_field_odom[0])
			if self._pub_f2d_f2o.enabled:
				self._pub_f2d_f2o.set([tf_field_odom[0].translation().x, tf_field_odom[0].translation().y, tf_field_odom[0].rotation().z])
		
		# Check pose override
		if (pose_override := self._sub_pose_override.get_fresh(None)) is not None:
			self.moenet.pose_override(pose_override)
		
		# Get field-to-robot
		if (tf_field_robot := self._sub_tf_field_robot.get_fresh(None)) is not None:
			pass

		if self._pub_f2d_type.enabled:
			self._pub_f2d_type.set("Field2d")

	
	def tx_error(self, message: str):
		"Send error message to NetworkTables"
		self._pub_error.set(message)
	
	def tx_log(self, message: str):
		"Send error message to NetworkTables"
		self._pub_log.set(message)

	def tx_status(self, status: net.Status):
		"Send status"
		self._pub_status.set(int(status))
		self.log.info("NT send status: %s", net.Status(status).name)

	def tx_pose(self, pose: Pose3d):
		self._pub_tf_field_robot.set(pose)

		q = pose.rotation().getQuaternion()
		self._pub_tf_field_robot2.set([
			pose.x,
			pose.y,
			pose.z,
			q.W(),
			q.X(),
			q.Y(),
			q.Z(),
		])
		if self._pub_f2d_f2r.enabled:
			self._pub_f2d_f2r.set([pose.translation().x, pose.translation().y, pose.rotation().z])
	
	def tx_correction(self, pose: Transform3d):
		self._pub_tf_odom_robot.set(pose)

	def tx_detections(self, detections: net.ObjectDetections):
		self.log.debug("Sending %d detections", len(detections.detections))
		self._pub_detections.set([
			SimpleObjectDetection(
				classsification=0,
				confidence=det.confidence,
				objectPose=Pose3d().transformBy(det.positionField),
			)
			for det in detections.detections or []
		])
		if self._pub_f2d_dets.enabled:
			data = [
				e
				for det in (detections.detections or [])
				if det.positionField is not None
				for e in (det.positionField.x, det.positionField.y, det.label_id)
			]
			self._pub_f2d_dets.set(data)

	def rx_sleep(self) -> bool:
		return self._sub_sleep.get(False)

	def close(self):
		del self.moenet
		if self.nt is not None:
			self.nt.disconnect()
			self.nt = None