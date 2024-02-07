from typing import TYPE_CHECKING, Literal, Union
from pathlib import Path

import depthai as dai

from typedef import pipeline as cfg
from typedef.geom import Translation3d
from .builder import XOutNode
from ..msg import ObjectDetection, MsgDetections

if TYPE_CHECKING:
	from .video import RgbBuilder, DepthBuilder

class ObjectDetectionNode(XOutNode[dai.SpatialImgDetections, cfg.ObjectDetectionStage]):
	stream_name = 'nn'
	requires = [
		('rgb', False),
		('depth', False),
	]
	
	def get_input(self, pipeline: dai.Pipeline, rgb: 'RgbBuilder', depth: 'DepthBuilder', *args, **kwargs) -> dai.Node.Output:
		spatialDetectionNetwork = pipeline.createYoloSpatialDetectionNetwork()
		nnConfig = self.config.config
		nnBlobPath = Path(self.config.blobPath).resolve().absolute()
		if not nnBlobPath.exists():
			raise RuntimeError(f"nnBlobPath not found: {nnBlobPath}")
		spatialDetectionNetwork.setBlobPath(nnBlobPath)
		spatialDetectionNetwork.input.setBlocking(False)

		spatialDetectionNetwork.setConfidenceThreshold(nnConfig.confidence_threshold)
		spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
		spatialDetectionNetwork.setDepthLowerThreshold(nnConfig.depthLowerThreshold)
		spatialDetectionNetwork.setDepthUpperThreshold(nnConfig.depthUpperThreshold)

		# Yolo specific parameters
		spatialDetectionNetwork.setNumClasses(nnConfig.classes)
		spatialDetectionNetwork.setCoordinateSize(nnConfig.coordinateSize)
		spatialDetectionNetwork.setAnchors(nnConfig.anchors)
		spatialDetectionNetwork.setAnchorMasks(nnConfig.anchor_masks)
		spatialDetectionNetwork.setIouThreshold(nnConfig.iou_threshold)
		self.labels = nnConfig.labels

		# Linking
		rgb.node.preview.link(spatialDetectionNetwork.input)

		depth.node.depth.link(spatialDetectionNetwork.inputDepth)
		
		self.node = spatialDetectionNetwork
		return spatialDetectionNetwork.out
	
	def handle(self, packet: dai.SpatialImgDetections):
		if packet.getTimestamp() < self._device_require_ts:
			self.log.info('Skip detection frame (before FLUSH threshold)')
			return None
		
		ts = self.context.local_timestamp(packet)

		# Convert detections
		SCALE = 1000 # DepthAI output is in millimeters
		detections = list()
		for raw_det in packet.detections:
			try:
				label = self.config.config.labels[raw_det.label]
			except KeyError:
				self.log.warning('Unknown label %s', raw_det.label)
				label = f'unknown_{raw_det.label}'
			
			detections.append(ObjectDetection(
				label=label,
				confidence=raw_det.confidence,
				position=Translation3d(
					x=raw_det.spatialCoordinates.x / SCALE,
					y=raw_det.spatialCoordinates.y / SCALE,
					z=raw_det.spatialCoordinates.z / SCALE,
				),
			))
		return MsgDetections(
			timestamp=ts.nanos,
			detections=detections,
		)
		return super().handle(packet)