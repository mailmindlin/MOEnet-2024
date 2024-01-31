from typing import Optional, Any, TYPE_CHECKING, Protocol, Union, Generic, TypeVar, Iterable
import logging, time
from pathlib import Path
from functools import cached_property
from datetime import timedelta

import numpy as np
import depthai as dai

from util.timestamp import Timestamp
from util.clock import WallClock
from typedef.geom import Pose3d, Translation3d, Rotation3d, Quaternion, Twist3d
from typedef.worker import MsgPose, MsgFrame, MsgDetections, MsgDetection, WorkerPipelineConfig as PipelineConfig

if TYPE_CHECKING:
    # import spectacularAI.depthai.Pipeline as SaiPipeline
    from typedef.sai_types import VioSession, MapperOutput, Pipeline as SaiPipeline
    from server.typedef.geom import Pose3d

T = TypeVar('T')
class XLinkOut(dai.node.XLinkOut, Generic[T]):
    "Typed version of XLinkOut (not a real class)"
    ...


class MoeNetPipeline:
    "Pipeline builder"

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
        if (self.config.apriltagPath is not None) and self.config.slam:
            sai_config.aprilTagPath = self.config.apriltagPath
        sai_config.internalParameters = {
            # "ffmpegVideoCodec": "libx264 -crf 15 -preset ultrafast",
            # "computeStereoPointCloud": "true",
            # "computeDenseStereoDepthKeyFramesOnly": "true",
            "alreadyRectified": "true"
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
        camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_4_K)
        camRgb.setInterleaved(False)
        camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        return camRgb
    
    @cached_property
    def node_yolo(self) -> Optional[dai.node.YoloSpatialDetectionNetwork]:
        if self.config.object_detection is None:
            return None
        
        spatialDetectionNetwork = self.pipeline.createYoloSpatialDetectionNetwork()
        nnConfig = self.config.object_detection
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

    @cached_property
    def node_sysinfo(self) -> Optional[dai.node.SystemLogger]:
        "System logger (for telemetry)"
        if not self.config.telemetry:
            return None
        syslog = self.pipeline.createSystemLogger()
        syslog.setRate(1)
        return syslog
    
    @cached_property
    def node_out_rgb(self) -> Optional[XLinkOut[dai.ImgFrame]]:
        "Get XLinkOut for rgb camera"
        if not self.config.debugRgb:
            return None
        
        xoutRgb = self.pipeline.createXLinkOut()
        xoutRgb.setStreamName('rgb')
        xoutRgb.setFpsLimit(self.config.debugImageRate or 30)

        if self.config.syncNN and (self.node_yolo is not None):
            nn = self.node_yolo
            nn.passthrough.link(xoutRgb.input)
        else:
            color = self.node_rgb
            color.video.link(xoutRgb.input)
        
        return xoutRgb

    @cached_property
    def node_out_left(self) -> Optional[XLinkOut[dai.ImgFrame]]:
        "Get XLinkOut for left camera"
        if not self.config.debugLeft:
            return None
        
        xoutLeft = self.pipeline.createXLinkOut()
        xoutLeft.setStreamName('left')
        xoutLeft.setFpsLimit(self.config.debugImageRate or 30)

        monoLeft = self.node_mono_left
        monoLeft.out.link(xoutLeft.input)
        
        return xoutLeft
    
    @cached_property
    def node_out_right(self) -> Optional[XLinkOut[dai.ImgFrame]]:
        "Get XLinkOut for right camera"
        if not self.config.debugRight:
            return None
        
        xoutRight = self.pipeline.createXLinkOut()
        xoutRight.setStreamName('right')
        xoutRight.setFpsLimit(self.config.debugImageRate or 30)

        monoRight = self.node_mono_right
        monoRight.out.link(xoutRight.input)
        
        return xoutRight
    
    @cached_property
    def node_out_depth(self) -> Optional[XLinkOut[dai.ImgFrame]]:
        "Get XLinkOut for depth"
        if not self.config.debugDepth:
            return None
        
        xoutDepth = self.pipeline.createXLinkOut()
        xoutDepth.setStreamName('depth')
        xoutDepth.setFpsLimit(self.config.debugImageRate or 30)

        depth = self.node_depth
        depth.preview.link(xoutDepth.input)
        
        return xoutDepth
    
    @cached_property
    def node_out_nn(self) -> Optional[XLinkOut[dai.SpatialImgDetections]]:
        nn = self.node_yolo
        if nn is None:
            return None
        
        xoutNN = self.pipeline.createXLinkOut()
        xoutNN.setStreamName('nn')
        nn.out.link(xoutNN.input)
        return xoutNN
    
    @cached_property
    def node_out_sysinfo(self) -> Optional[XLinkOut[dai.SystemInformation]]:
        sysinfo = self.node_sysinfo
        if sysinfo is None:
            return None
        
        xout_sysinfo = self.pipeline.createXLinkOut()
        xout_sysinfo.setStreamName('sysinfo')
        xout_sysinfo.setFpsLimit(2)
        sysinfo.out.link(xout_sysinfo)
        return xout_sysinfo

    def build(self):
        "Build all nodes in this pipeline"
        self.vio_pipeline
        self.node_out_nn

        self.node_out_sysinfo
        self.node_out_depth

        self.node_out_rgb
        self.node_out_left
        self.node_out_right


class QueueLike(Generic[T]):
    def has(self):
        return False
    def get(self) -> T:
        raise RuntimeError()
    def tryGet(self) -> Optional[T]:
        return None
    def tryGetAll(self) -> list[T]:
        return list()

class FakeVioSession:
    def hasOutput(self):
        return False
    def getOutput(self) -> Any:
        return None
    def addTrigger(self, *args):
        return
    def close(self):
        pass

class StampedPacket(Protocol):
    def getTimestamp(self) -> 'timedelta': ...
    def getTimestampDevice(self) -> 'timedelta': ...


class MoeNetSession:
    _device_require_ts: 'timedelta'

    def __init__(self, device: dai.Device, pipeline: MoeNetPipeline, log: Optional['logging.Logger'] = None) -> None:
        self.device = device
        self.pipeline = pipeline
        self.log = (log.getChild if log is not None else logging.getLogger)('sesson')
        self.clock = WallClock()

        self.labels = pipeline.labels
        self.log.info("Streams: %s", device.getOutputQueueNames())

        def make_queue(node: Optional[XLinkOut[T]], *, maxSize: int = 4) -> QueueLike[T]:
            if node is None:
                return QueueLike()
            return device.getOutputQueue(node.getStreamName(), maxSize=maxSize, blocking=False)
        self.queue_dets = make_queue(pipeline.node_out_nn)
        self.queue_rgb = make_queue(pipeline.node_out_rgb, maxSize=1)
        self.queue_left = make_queue(pipeline.node_out_left, maxSize=1)
        self.queue_right = make_queue(pipeline.node_out_right, maxSize=8)
        self.queue_depth = make_queue(pipeline.node_out_depth, maxSize=1)
        self.queue_sysinfo = make_queue(pipeline.node_out_sysinfo, maxSize=1)

        self.streams = set()
        
        # Start sai
        if (vio_pipeline := pipeline.vio_pipeline) is not None:
            self.vio_session: 'VioSession' = vio_pipeline.startSession(device)
        else:
            self.vio_session: 'VioSession' = FakeVioSession()

        self._vio_require_tag = 0
        self._vio_last_tag = 0
        self._device_require_ts = dai.Clock.now()
        self._offset_dev_to_dai = None # dev_ts - dai_ts (for SAI conversion)
    
    def onMappingOutput(self, mapping: 'MapperOutput'):
        #TODO: is this useful?
        pass

    def close(self):
        self.vio_session.close()
    
    def local_timestamp(self, packet: StampedPacket) -> 'Timestamp':
        "Convert device time to wall time"
        ts_dai = packet.getTimestamp()
        ts_dev = packet.getTimestampDevice()
        now_dai: 'timedelta' = dai.Clock.now()
        now_wall = self.clock.now()
        latency = now_dai - ts_dai

        # Update system -> device time
        self._offset_dev_to_dai = ts_dev - ts_dai

        return now_wall - latency

    def _poll_rgb(self):
        raw_rgb = self.queue_rgb.tryGet()
        if raw_rgb is None or ('rgb' not in self.streams):
            return None
        raw_frame = raw_rgb.getCvFrame()
        ts = self.local_timestamp(raw_rgb)
        return MsgFrame(
            worker='',
            stream='rgb',
            timestamp=ts.nanos,
            timestamp_recv=time.time_ns(),
            sequence=raw_rgb.getSequenceNum(),
            data=raw_frame,
        )

    def _poll_left(self):
        raw_frame = self.queue_left.tryGet()
        if raw_frame is None or ('left' not in self.streams):
            return None
        ts = self.local_timestamp(raw_frame)
        return MsgFrame(
            worker='',
            stream='left',
            timestamp=ts.nanos,
            timestamp_recv=time.time_ns(),
            timestamp_insert=0,
            sequence=raw_frame.getSequenceNum(),
            data=raw_frame.getCvFrame()
        )
    
    def _poll_right(self):
        raw_frame = self.queue_right.tryGet()
        recv = self.clock.now_ns()
        if raw_frame is None or ('right' not in self.streams):
            return None
        ts = self.local_timestamp(raw_frame)
        return MsgFrame(
            worker='',
            stream='right',
            timestamp=ts.nanos,
            timestamp_recv=recv,
            timestamp_insert=0,
            sequence=raw_frame.getSequenceNum(),
            data=raw_frame.getCvFrame()
        )
    
    def _poll_dets(self):
        "Poll object detection queue"
        raw_dets = self.queue_dets.tryGet()
        if raw_dets is None:
            return None
        
        if raw_dets.getTimestamp() < self._device_require_ts:
            self.log.info('Skip detection frame (before FLUSH threshold)')
            return None
        
        ts = self.local_timestamp(raw_dets)

        # Convert detections
        SCALE = 1000 # DepthAI output is in millimeters
        detections = list()
        for raw_det in raw_dets.detections:
            try:
                label = self.pipeline.labels[raw_det.label]
            except KeyError:
                self.log.warning('Unknown label %s', raw_det.label)
                label = f'unknown_{raw_det.label}'
            
            detections.append(MsgDetection(
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
    
    def _poll_sysinfo(self):
        sysinfo = self.queue_sysinfo.tryGet()
        if sysinfo is None:
            return None
        # We don't flush sysinfo packets
        #TODO
        return None

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

        # SAI uses device-time, so we have to do some conversion
        latency = dai.Clock.now() - timedelta(seconds=vio_out.pose.time)
        timestamp = int(vio_out.pose.time * 1e9)

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
        dai_ts: 'timedelta' = dai.Clock.now()
        self._device_require_ts = max(self._device_require_ts, dai_ts) # Ignore any object detection packets from before now
        if self._offset_dev_to_dai is not None:
            self._vio_require_tag += 1
            dev_ts = dai_ts.total_seconds() - self._offset_dev_to_dai
            self.vio_session.addTrigger(dev_ts, self._vio_require_tag)
    
    def override_pose(self, pose: 'Pose3d'):
        if isinstance(self.vio_session, FakeVioSession):
            return
        #TODO
        # self.vio_session.addAbsolutePose()

    def poll(self) -> Iterable[Union[MsgFrame, MsgPose, MsgDetections]]:
        did_work = True
        while did_work:
            did_work = False

            for supplier in [self._poll_dets, self._poll_vio, self._poll_rgb, self._poll_left, self._poll_right, self._poll_sysinfo]:
                msg = supplier()
                if msg is not None:
                    did_work = True
                    yield msg