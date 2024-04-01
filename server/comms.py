from typing import TYPE_CHECKING, Optional
import logging
from dataclasses import dataclass

from ntcore import NetworkTable, NetworkTableInstance, PubSubOptions
from wpiutil import wpistruct

from util.timestamp import Timestamp
from util.log import child_logger
from typedef.cfg import LocalConfig, NetworkTablesDirection
from typedef.geom import Pose3d, Transform3d, Translation3d
from typedef import net
from wpi_compat.nt import DynamicPublisher, DynamicSubscriber

if TYPE_CHECKING:
	from .__main__ import MoeNet

@wpistruct.make_wpistruct(name="CpuTimes")
@dataclass
class CpuTimes:
	percent: float
	user: float
	system: float
	children_user: float
	children_system: float

@wpistruct.make_wpistruct(name="MoenetTelemetry")
@dataclass
class MoenetTelemetry:
	cpu: CpuTimes
	memory_percent: float
	threads: int


@wpistruct.make_wpistruct(name="ObjectDetection")
@dataclass
class SimpleObjectDetection:
	classsification: wpistruct.dataclass.int32
	confidence: wpistruct.dataclass.double
	objectPose: Translation3d


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

class TelemetryPublisher:
	def __init__(self) -> None:
		pass

	def fetch(self):
		try:
			import psutil
		except ImportError:
			return
		import os
		p = psutil.Process(os.getpid())
		with p.oneshot():
			ct = p.cpu_times()
			cpu = CpuTimes(
				percent=p.cpu_percent(),
				user=ct.user,
				system=ct.system,
				children_user=ct.children_user,
				children_system=ct.children_system,
			)
			ram_percent = p.memory_percent()
			threads = p.num_threads()
		return MoenetTelemetry(
			cpu=cpu,
			memory_percent=ram_percent,
			threads=threads,
		)
	
	def poll(self):
		pass

class Comms:
	nt: NetworkTableInstance
	table: NetworkTable
	
	def __init__(self, moenet: 'MoeNet', config: LocalConfig, log: Optional[logging.Logger] = None):
		self.moenet = moenet
		self.config = config
		self.log = child_logger('comms', log)
		self.ping_id = 0

		self.labels = list()

		table_lazy = lambda: self.table

		self._pub_ping   = DynamicPublisher.create(table_lazy, "client_ping", int)
		self._pub_error  = DynamicPublisher.create(table_lazy, "client_error", str, PubSubOptions(sendAll=True))
		self._pub_log    = DynamicPublisher.create(table_lazy, "client_log", str, PubSubOptions(sendAll=True))
		self._pub_status = DynamicPublisher.create(table_lazy, "client_status", int, PubSubOptions(sendAll=True))
		self._pub_config = DynamicPublisher.create(table_lazy, "client_config", str, PubSubOptions(sendAll=True, periodic=1))
		"Publish config JSON"
		self._pub_telem  = DynamicPublisher.create(table_lazy, "client_telemetry", MoenetTelemetry, PubSubOptions(periodic=0.5, keepDuplicates=True), mode='struct')

		# Publish transforms
		self._pub_tf_field_odom  = DynamicPublisher.create(table_lazy, "tf_field_odom", Pose3d, PubSubOptions(periodic=0.01), mode='struct')
		self._pub_tf_field_robot = DynamicPublisher.create(table_lazy, "tf_field_robot", Pose3d, PubSubOptions(periodic=0.01), mode='struct')
		# self._pub_tf_field_robot2 = DynamicPublisher.create(lambda: self.nt.getDoubleArrayTopic(self.table.getPath() + "/tf_field_robot2"), PubSubOptions(periodic=0.01))
		self._pub_tf_odom_robot  = DynamicPublisher.create(table_lazy, "tf_odom_robot", Transform3d, PubSubOptions(periodic=0.1), mode='struct')

		dets_lazy = lambda: self.table.getSubTable("client_detections")
		self._pub_detections_full = DynamicPublisher.create(dets_lazy, "full", net.ObjectDetections, PubSubOptions(periodic=0.05), mode='proto')
		"Object detections, in protobuf format (self-contained)"
		self._pub_detections = DynamicPublisher.create(dets_lazy, "simple", list[SimpleObjectDetection], PubSubOptions(periodic=0.05), mode='struct')
		"Object detections, in simple format"
		self._pub_detections_labels = DynamicPublisher.create(dets_lazy, "labels", list[str])
		"Object detection labels"

		tf_sub_options = PubSubOptions(periodic=0.01, disableLocal=True)
		self._sub_tf_field_odom = DynamicSubscriber.create(table_lazy, 'tf_field_odom', Pose3d, Pose3d(), tf_sub_options)
		self._sub_tf_field_robot = DynamicSubscriber.create(table_lazy, 'tf_field_robot', Pose3d, Pose3d(), tf_sub_options)
		self._sub_tf_odom_robot = DynamicSubscriber.create(table_lazy, 'tf_odom_robot', Transform3d, Transform3d(), tf_sub_options)
		self._sub_pose_override = DynamicSubscriber.create(table_lazy, 'rio_pose_override', Pose3d, Pose3d(), PubSubOptions(keepDuplicates=True))

		self._sub_config = DynamicSubscriber.create(table_lazy, "rio_config", str, "")
		self._sub_sleep  = DynamicSubscriber.create(table_lazy, "rio_sleep", bool, False)

		# Field2d
		f2d_lazy = lambda: self.nt.getTable("SmartDashboard").getSubTable("MOEnet")
		self._pub_f2d_type = DynamicPublisher.create(f2d_lazy, ".type", str)
		self._pub_f2d_f2o  = DynamicPublisher.create(f2d_lazy, "Odometry", list[float])
		self._pub_f2d_f2r  = DynamicPublisher.create(f2d_lazy, "Robot", list[float])
		self._pub_f2d_dets = DynamicPublisher.create(f2d_lazy, "Notes", list[float])

		self._telemetry = TelemetryPublisher()

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
		self._pub_telem.enabled = ntc.publishSystemInfo
		self._pub_tf_field_odom.enabled   = (ntc.tfFieldToOdom  == NetworkTablesDirection.PUBLISH)
		self._pub_tf_field_robot.enabled  = (ntc.tfFieldToRobot == NetworkTablesDirection.PUBLISH)
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
		try:
			if self._pub_telem.enabled and (telem := self._telemetry.fetch()) is not None:
				self._pub_telem.set(telem)
		except Exception:
			self.log.exception("Error publishing telemetry to NT")
		
		# Get odometry
		for odom_msg in self._sub_tf_field_odom.readQueue():
			# Probably a better way to do this
			timestamp = Timestamp.from_wpi(odom_msg.time)
			pose = odom_msg.value
			self.moenet.estimator.observe_f2o(timestamp, pose)
			# Re-publish to Field2d
			if self._pub_f2d_f2o.enabled:
				self._pub_f2d_f2o.set([pose.translation().x, pose.translation().y, pose.rotation().z])
		
		# Check pose override
		for pose_msg in self._sub_pose_override.readQueue():
			timestamp = Timestamp.from_wpi(pose_msg.time)
			pose = pose_msg.value
			self.moenet.pose_override(pose, timestamp)
		
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

		if self._pub_f2d_f2r.enabled:
			self._pub_f2d_f2r.set([pose.translation().x, pose.translation().y, pose.rotation().z])
	
	def tx_correction(self, pose: Transform3d):
		self._pub_tf_odom_robot.set(pose)

	def tx_detections(self, detections: net.ObjectDetections):
		self.log.debug("Sending %d detections", len(detections.detections) if detections.detections is not None else 0)
		self._pub_detections.set([
			SimpleObjectDetection(
				classsification=0,
				confidence=wpistruct.double(det.confidence) if det.confidence is not None else 1.0,
				objectPose=Translation3d(
					x=det.positionField.x or 0,
					y=det.positionField.y or 0,
					z=det.positionField.z or 0,
				)
			)
			for det in detections.detections or []
			if det.positionField is not None
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