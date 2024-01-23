from typing import Optional, Any, TYPE_CHECKING
from pathlib import Path
from dataclasses import dataclass
from functools import cached_property

import numpy as np

from clock import FixedOffsetMapper, MonoClock, WallClock
from typedef.worker import ObjectDetectionConfig
import depthai as dai

if TYPE_CHECKING:
    # import spectacularAI.depthai.Pipeline as SaiPipeline
    from typedef.sai_types import VioSession, MapperOutput, Pipeline as SaiPipeline
    from server.typedef.geom import Pose3d

@dataclass
class PipelineConfig:
    syncNN: bool
    outputRGB: bool
    vio: bool
    slam: bool
    apriltag_path: Optional[Path]
    nn: Optional[ObjectDetectionConfig]


class MoeNetPipeline:
    config: PipelineConfig

    pipeline: dai.Pipeline

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipeline = dai.Pipeline()
        self.labels = []
        self.build()

    def onMappingOutput(self, x):
        print("onMappingOutput!")
        pass
    
    @cached_property
    def vio_pipeline(self) -> Optional['SaiPipeline']:
        if not (self.config.vio or self.config.slam):
            return None

        import spectacularAI as sai
        sai_config = sai.depthai.Configuration()
        if (self.config.apriltag_path is not None) and self.config.slam:
            sai_config.aprilTagPath = self.config.apriltag_path
        sai_config.internalParameters = {
            # "ffmpegVideoCodec": "libx264 -crf 15 -preset ultrafast",
            # "computeStereoPointCloud": "true",
            # "computeDenseStereoDepthKeyFramesOnly": "true",
            # "alreadyRectified": "true"
        }
        sai_config.useSlam = self.config.slam
        sai_config.useFeatureTracker = True
        sai_config.useVioAutoExposure = True
        sai_config.inputResolution = '800p'
        # sai_config.useColor = True
        return sai.depthai.Pipeline(self.pipeline, sai_config, self.onMappingOutput)
    
    @cached_property
    def node_mono_left(self) -> dai.node.MonoCamera:
        vio_pipeline = self.vio_pipeline
        if vio_pipeline is not None:
            return vio_pipeline.monoLeft
        # Left IR
        monoLeft = self.pipeline.createMonoCamera()
        monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
        monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        return monoLeft

    @cached_property
    def node_mono_right(self) -> dai.node.MonoCamera:
        vio_pipeline = self.vio_pipeline
        if vio_pipeline is not None:
            return vio_pipeline.monoRight
        # Right IR
        monoRight = self.pipeline.createMonoCamera()
        monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)
        monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        return monoRight

    @cached_property
    def node_depth(self) -> dai.node.StereoDepth:
        vio_pipeline = self.vio_pipeline
        if (vio_pipeline is not None) and False:
            node = vio_pipeline.stereo
            # node.setDepthAlign(dai.CameraBoardSocket.RGB)
            return node
        
        stereo = self.pipeline.createStereoDepth()
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)

        # Align depth map to the perspective of RGB camera, on which inference is done
        stereo.setDepthAlign(dai.CameraBoardSocket.RGB)

        monoLeft = self.node_mono_left
        monoRight = self.node_mono_right
        stereo.setOutputSize(monoRight.getResolutionWidth(), monoRight.getResolutionHeight())

        # Linking
        monoLeft.out.link(stereo.left)
        monoRight.out.link(stereo.right)
        return stereo

    @cached_property
    def node_rgb(self) -> dai.node.ColorCamera:
        #TODO: is this right?
        vio_pipeline = self.vio_pipeline
        if (vio_pipeline is not None) and (getattr(vio_pipeline, 'color', None) is not None):
            node: dai.node.ColorCamera = vio_pipeline.color
            return node

        camRgb = self.pipeline.createColorCamera()
        camRgb.setPreviewSize(416, 416)
        camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        camRgb.setInterleaved(False)
        camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        return camRgb
    
    @cached_property
    def node_yolo(self) -> Optional[dai.node.YoloSpatialDetectionNetwork]:
        if self.config.nn is None:
            return None
        
        spatialDetectionNetwork = self.pipeline.createYoloSpatialDetectionNetwork()
        nnConfig = self.config.nn
        nnBlobPath = Path(nnConfig.blobPath).resolve().absolute()
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
        camRgb = self.node_rgb
        camRgb.preview.link(spatialDetectionNetwork.input)

        stereo = self.node_depth
        stereo.depth.link(spatialDetectionNetwork.inputDepth)
        
        return spatialDetectionNetwork
    
    @property
    def node_out_rgb(self) -> Optional[dai.node.XLinkOut]:
        if not self.config.outputRGB:
            return None
        
        xoutRgb = self.pipeline.createXLinkOut()
        xoutRgb.setStreamName('rgb')

        if self.config.syncNN and (self.node_yolo is not None):
            nn = self.node_yolo
            nn.passthrough.link(xoutRgb.input)
        else:
            color = self.node_rgb
            color.preview.link(xoutRgb.input)
        
        return xoutRgb
    
    @cached_property
    def node_out_nn(self) -> Optional[dai.node.XLinkOut]:
        nn = self.node_yolo
        if nn is None:
            return None
        
        xoutNN = self.pipeline.createXLinkOut()
        xoutNN.setStreamName('nn')
        nn.out.link(xoutNN.input)
        return xoutNN

    def build(self):
        "Build all nodes in this pipeline"
        self.vio_pipeline
        self.node_out_nn
        self.node_out_rgb


class FakeQueue:
    def has(self):
        return False
    def get(self):
        raise RuntimeError()
    def tryGet(self):
        return None
class FakeVioSession:
    def hasOutput(self):
        return False
    def getOutput(self) -> Any:
        return None
    def addTrigger(self, *args):
        return
    def close(self):
        pass

class MoeNetSession:
    def __init__(self, device: dai.Device, pipeline: MoeNetPipeline) -> None:
        self.device = device
        self.pipeline = pipeline
        node_out_nn = pipeline.node_out_nn
        self.labels = pipeline.labels
        print("Streams: ", device.getOutputQueueNames())
        if node_out_nn is not None:
            queue_dets = device.getOutputQueue(node_out_nn.getStreamName(), maxSize=4, blocking=False)
        else:
            queue_dets = FakeQueue()
        self.queue_dets = queue_dets
        
        vio_pipeline = pipeline.vio_pipeline
        if vio_pipeline is not None:
            self.vio_session: 'VioSession' = vio_pipeline.startSession(device)
        else:
            self.vio_session: 'VioSession' = FakeVioSession()
        
        self.clock = FixedOffsetMapper(MonoClock(), WallClock())

        self._vio_require_tag = 0
        self._vio_last_tag = 0
        self._device_require_ts = 0
    
    def onMappingOutput(self, mapping: 'MapperOutput'):
        #TODO: is this useful?
        pass

    def close(self):
        self.vio_session.close()
    
    def _poll_dets(self):
        "Poll object detection queue"
        from typedef.worker import MsgDetections, MsgDetection
        from typedef.geom import Translation3d

        dets: Optional[dai.SpatialImgDetections] = self.queue_dets.tryGet()
        if dets is None:
            return None
        ts = self.clock.a_to_b(self.clock.clock_a + dets.getTimestamp())
        SCALE = 1000 # DepthAI output is in millimeters
        return MsgDetections(
            timestamp=ts,
            detections=[
                MsgDetection(
                    label=self.pipeline.labels[detection.label],
                    confidence=detection.confidence,
                    position=Translation3d(
                        x=detection.spatialCoordinates.x / SCALE,
                        y=detection.spatialCoordinates.y / SCALE,
                        z=detection.spatialCoordinates.z / SCALE,
                    ),
                )
                for detection in dets.detections
            ]
        )

    def _poll_vio(self):
        "Poll VIO queue"
        if not self.vio_session.hasOutput():
            return None
        vio_out = self.vio_session.getOutput()

        if vio_out.tag > 0:
            self._vio_last_tag = vio_out.tag
        
        # Ensure we've completed all VIO flushes
        if self._vio_last_tag < self._vio_require_tag:
            print("Skipped frame")
            return
        # cam = vio_out.getCameraPose(0)

        pc = np.asarray(vio_out.positionCovariance)
        vc = np.asarray(vio_out.velocityCovariance)

        timestamp = self.clock.a_to_b(self.clock.clock_a.now() + int(vio_out.pose.time * 1e9))

        from typedef.geom import Pose3d, Translation3d, Rotation3d, Quaternion, Twist3d
        from typedef.worker import MsgPose

        # Why is orientation covariance 1e-4?
        # Because I said so
        ROTATION_COV = 1e-4
        ANG_VEL_COV = 1e-3

        return MsgPose(
            timestamp=timestamp,
            # Not sure if we need this property
            view_mat=vio_out.pose.asMatrix(),
            # I wish there was a better way to do this, but spectacularAI types are native wrappers,
            # and they can't be nicely shared between processes
            pose=Pose3d(
                translation=Translation3d(
                    x = vio_out.pose.position.x,
                    y = vio_out.pose.position.y,
                    z = vio_out.pose.position.z,
                ),
                rotation=Rotation3d(Quaternion(
                    w = vio_out.pose.orientation.w,
                    x = vio_out.pose.orientation.x,
                    y = vio_out.pose.orientation.y,
                    z = vio_out.pose.orientation.z,
                ))
            ),
            poseCovariance=np.asarray([
                [pc[0, 0], pc[0, 1], pc[0, 2], 0, 0, 0],
                [pc[1, 0], pc[1, 1], pc[1, 2], 0, 0, 0],
                [pc[2, 0], pc[2, 1], pc[2, 2], 0, 0, 0],
                [0, 0, 0, ROTATION_COV, 0, 0],
                [0, 0, 0, 0, ROTATION_COV, 0],
                [0, 0, 0, 0, 0, ROTATION_COV],
            ], dtype=np.float32),
            twist=Twist3d(
                dx = vio_out.velocity.x,
                dy = vio_out.velocity.y,
                dz = vio_out.velocity.z,
                rx = vio_out.angularVelocity.x,
                ry = vio_out.angularVelocity.y,
                rz = vio_out.angularVelocity.z,
            ),
            twistCovariance=np.asarray([
                [vc[0, 0], vc[0, 1], vc[0, 2], 0, 0, 0],
                [vc[1, 0], vc[1, 1], vc[1, 2], 0, 0, 0],
                [vc[2, 0], vc[2, 1], vc[2, 2], 0, 0, 0],
                [0, 0, 0, ANG_VEL_COV, 0, 0],
                [0, 0, 0, 0, ANG_VEL_COV, 0],
                [0, 0, 0, 0, 0, ANG_VEL_COV],
            ], dtype=np.float32),
        )

    def flush(self):
        "Flush all previously-enqueued data from the device"
        dev_ts = dai.Clock.now()
        self._device_require_ts = max(self._device_require_ts, dev_ts) # Ignore any object detection packets from before now
        self._vio_require_tag += 1
        self.vio_session.addTrigger(dev_ts, self._vio_require_tag)
    
    def override_pose(self, pose: 'Pose3d'):
        if isinstance(self.vio_session, FakeVioSession):
            return
        #TODO
        # self.vio_session.addAbsolutePose()

    def poll(self):
        did_work = True
        while did_work:
            did_work = False

            msg_dets = self._poll_dets()
            msg_vio = self._poll_vio()
            if msg_dets is not None:
                did_work = True
                yield msg_dets
            if msg_vio is not None:
                did_work = True
                yield msg_vio
            # cmx = self.device.getCmxMemoryUsage()
            # ddr = self.device.getDdrMemoryUsage()
            # print("Device CMX %f DDR %f LEON CSS %f MSS %f" % (
            #               100.0 * cmx.used / cmx.total,
            #               100.0 * ddr.used / ddr.total,
            #               100.0 * self.device.getLeonCssCpuUsage().average,
            #               100.0 * self.device.getLeonMssCpuUsage().average))