from typing import TYPE_CHECKING
from logging import Logger
if TYPE_CHECKING:
	from .camera_tracker import CamerasTracker
from datetime import timedelta
from dataclasses import dataclass

import numpy as np
from multidict import MultiDict

from worker.msg import ObjectDetection as MsgObjectDetection
from typedef.geom import Transform3d, Translation3d, Rotation3d, Pose3d
from typedef.cfg import ObjectTrackerConfig
from util.timestamp import Timestamp
from .tf import TfTracker, ReferenceFrame
from .util.cascade_replay import CascadingReplayFilter
from .util.cascade import Tracked, Derived
from .util.replay import ReplayableFilter, ReplayFilter

class TrackedObject:
	def __init__(self, id: int, timestamp: Timestamp, position: Translation3d, label: str, confidence: float):
		self.id = id
		"Tracking ID"
		self.position = position
		"Estimated object position"
		self.label = label
		"Detection label"
		self.last_seen = timestamp
		self.n_detections = 1
		self.confidence = confidence
		"Detection confidence"
		self._position_rs_cache = None

	def update(self, other: 'TrackedObject', alpha: float = 0.2):
		self.last_seen = other.last_seen

		# LERP (TODO: use confidence?)
		self.position = (other.position * alpha) + (self.position * (1.0 - alpha))
		self.n_detections += 1
	
	@property
	def pose(self):
		"Get position as Pose3d"
		return Pose3d(self.position, Rotation3d())
	
	def position_rel(self, reference_pose: Pose3d) -> Translation3d:
		"Get position relative to some reference"
		# Cache position_rs, as we'll probably compute the same transforms a lot
		if (self._position_rs_cache is None) or (self._position_rs_cache[0] != reference_pose):
			position_rs = self.pose.relativeTo(reference_pose).translation()
			self._position_rs_cache = (reference_pose, position_rs)
		
		return self._position_rs_cache[1]
	
	def should_remove(self, now: Timestamp, config: ObjectTrackerConfig):
		if self.n_detections < config.min_detections and self.last_seen < now - config.detected_duration:
			return True
		if self.last_seen < now - config.history_duration:
			return True
		return False

	def __str__(self):
		return f'{self.label}@{self.id}'
	
	def copy(self):
		res = TrackedObject(
			self.id,
			self.last_seen,
			self.position,
			self.label,
			self.confidence,
		)
		res.n_detections = self.n_detections
		return res

@dataclass
class ObjectDetectionMeasurement:
	ts: Timestamp
	detections: list[MsgObjectDetection]
	field_to_camera: Pose3d

	@staticmethod
	def derived(ts: Timestamp, detections: list[MsgObjectDetection], field_to_camera: Tracked[Pose3d]) -> Tracked['ObjectDetectionMeasurement']:
		return field_to_camera.map(lambda field_to_camera: ObjectDetectionMeasurement(ts, detections, field_to_camera))


class Snapshot:
	tracked_objects: MultiDict[TrackedObject]
	def __init__(self, config: ObjectTrackerConfig) -> None:
		self.next_id = 0
		self.tracked_objects = MultiDict()
		self.last_measurement_ts = Timestamp.invalid()
		self.config = config
	
	def copy(self):
		res = Snapshot(self.config)
		res.next_id = self.next_id
		res.last_measurement_ts = self.last_measurement_ts
		for k, v in self.tracked_objects.items():
			res.tracked_objects.add(k, v.copy())
		return res
	
	def cleanup(self, t: Timestamp):
		"Remove objects that haven't been seen for a while"
		# remove cruft
		self.tracked_objects = MultiDict(
			(key, value)
			for key, value in self.tracked_objects.items()
			if not value.should_remove(t, self.config)
		)

class ObjectTrackerFilter(ReplayableFilter[ObjectDetectionMeasurement, Snapshot]):
	def __init__(self, config: ObjectTrackerConfig):
		super().__init__()
		self.config = config
		self.state = Snapshot(self.config)
		self.sensor_timeout = config.history_duration
	
	# @property
	# def is_initialized(self):
	# 	return self.state.last_measurement_ts.is_valid
	
	@property
	def last_measurement_ts(self):
		return self.state.last_measurement_ts
	
	def snapshot(self) -> Snapshot:
		return self.state.copy()
	
	def restore(self, state: Snapshot):
		self.state = state.copy()
	
	def _find_best_match(self, new_obj: TrackedObject, field_to_camera: Pose3d):
		new_cs = new_obj.position_rel(field_to_camera)

		best = None
		best_dist = self.config.clustering_distance
		for old in self.state.tracked_objects.getall(new_obj.label, []):
			# ignore depth difference in clustering
			old_cs = new_obj.position_rel(field_to_camera)

			# Distance away from camera
			z = max(self.config.min_depth, old_cs.z, new_cs.z)
			dist: float = np.hypot(old_cs.x - new_cs.x, old_cs.y - new_cs.y) / z

			if dist < best_dist:
				best_dist = dist
				best = old
		# if best: print(f'matched with {best} (seen {best.n_detections} time(s))')
		return best

	def predict(self, now: Timestamp, delta: timedelta):
		self.state.cleanup(now)

	def observe(self, measurement: ObjectDetectionMeasurement):
		field_to_camera = measurement.field_to_camera
		# field_to_camera = field_to_robot + robot_to_camera

		for detection in measurement.detections:
			cam_to_obj = Translation3d(
				x=detection.position.x,
				y=-detection.position.y, # Flipped y (it was in the SAI example)
				z=detection.position.z,
			)
			
			field_to_obj = (field_to_camera + Transform3d(cam_to_obj, Rotation3d())).translation()
			label = detection.label

			id = self.state.next_id
			new_obj = TrackedObject(id, measurement.ts, field_to_obj, label, confidence=detection.confidence)
			if existing := self._find_best_match(new_obj, field_to_camera):
				existing.update(new_obj, alpha=self.config.alpha)
			else:
				self.state.next_id += 1 # Only bump IDs for new objects
				self.state.tracked_objects.add(label, new_obj)
		
		self.state.last_measurement_ts = max(self.state.last_measurement_ts, measurement.ts) if self.state.last_measurement_ts.is_valid else measurement.ts

	def clear(self):
		self.state = Snapshot(self.config)

	def items(self):
		return [
			obj
			for obj in self.state.tracked_objects.values()
			if obj.n_detections >= self.config.min_detections
		]

class ObjectTracker:
	def __init__(self, config: ObjectTrackerConfig, tf: TfTracker, log: Logger) -> None:
		self.config = config
		self.tf = tf # tf provides field->robot and robot->camera
		self._raw_filter = ObjectTrackerFilter(config)
		self._filter = CascadingReplayFilter(self._raw_filter, config.history_duration, log=log)

	def observe_detections(self, detections: list[MsgObjectDetection], dets_frame: ReferenceFrame, timestamp: Timestamp):
		"Track some objects"
		field_to_robot = self.tf.track_pose(ReferenceFrame.ROBOT, timestamp)
		robot_to_camera = self.tf.track_tf(ReferenceFrame.ROBOT, dets_frame, timestamp)
		field_to_camera = Derived[Pose3d](Pose3d.__add__, field_to_robot, robot_to_camera)

		self._filter.observe(
			ObjectDetectionMeasurement.derived(
				timestamp,
				detections,
				field_to_camera,
			)
		)
	
	def predict(self, now: Timestamp):
		self._filter.predict(now)
	
	def items(self):
		"Get all currently tracked objects"
		return self._raw_filter.items()

	def clear(self):
		"Clear all tracks"
		self._filter.clear()