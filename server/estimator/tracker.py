import numpy as np
from multidict import MultiDict

from worker.msg import MsgDetections
from typedef.geom import Transform3d, Translation3d, Rotation3d, Pose3d
from typedef.cfg import ObjectTrackerConfig
from util.timestamp import Timestamp

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
		if self.n_detections < config.object_min_detections and self.last_seen < now - config.object_detected_duration:
			return True
		if self.last_seen < now - config.object_history_duration:
			return True
		return False

	def __str__(self):
		return f'{self.label}@{self.id}'


class ObjectTracker:
	tracked_objects: MultiDict[TrackedObject]

	def __init__(self, config: ObjectTrackerConfig) -> None:
		self.tracked_objects = MultiDict()
		self._next_id = 0
		self.config = config

	def _find_best_match(self, new_obj: TrackedObject, field_to_camera: Pose3d):
		new_cs = new_obj.position_rel(field_to_camera)

		best = None
		best_dist = self.config.object_clustering_distance
		for old in self.tracked_objects.getall(new_obj.label):
			# ignore depth difference in clustering
			old_cs = new_obj.position_rel(field_to_camera)

			# Distance away from camera
			z = max(self.config.object_min_depth, old_cs.z, new_cs.z)
			dist: float = np.hypot(old_cs.x - new_cs.x, old_cs.y - new_cs.y) / z

			if dist < best_dist:
				best_dist = dist
				best = old
		# if best: print(f'matched with {best} (seen {best.n_detections} time(s))')
		return best

	def track(self, t: Timestamp, detections: MsgDetections, field_to_robot: Pose3d, robot_to_camera: Transform3d):
		"Track some objects"
		field_to_camera = field_to_robot + robot_to_camera

		for detection in detections:
			cam_to_obj = Translation3d(
				x=detection.position.x,
				y=-detection.position.y, # Flipped y (it was in the SAI example)
				z=detection.position.z,
			)
			field_to_obj = (field_to_camera + Transform3d(cam_to_obj, Rotation3d())).translation()
			label = detection.label

			id = self._next_id
			new_obj = TrackedObject(id, t, field_to_obj, label, confidence=detection.confidence)
			if existing := self._find_best_match(new_obj, field_to_camera):
				existing.update(new_obj, alpha=self.config.object_alpha)
			else:
				self._next_id += 1 # Only bump IDs for new objects
				self.tracked_objects.add(label, new_obj)
		
		self.cleanup(t)
	
	def cleanup(self, t: Timestamp):
		"Remove objects that haven't been seen for a while"
		# remove cruft
		self.tracked_objects = MultiDict(
			(key, value)
			for key, value in self.tracked_objects.items()
			if not value.should_remove(t, self.config)
		)
	
	def items(self):
		"Get all currently tracked objects"
		return (
			obj
			for obj in self.tracked_objects.values()
			if obj.n_detections >= self.config.object_min_detections
		)

	def clear(self):
		"Clear all tracks"
		self.tracked_objects.clear()