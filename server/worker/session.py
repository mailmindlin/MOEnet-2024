from typing import Optional, TYPE_CHECKING, Generic, TypeVar, Any, Protocol
import depthai as dai
import numpy as np
from datetime import timedelta

from typedef.geom import Pose3d, Translation3d, Rotation3d, Quaternion, Twist3d
from util.clock import WallClock
from util.timestamp import Timestamp

from .msg import MsgFrame, ObjectDetection, MsgDetections, MsgPose

if TYPE_CHECKING:
    import logging
    from .node import MoeNetPipeline, XLinkOut
    from typedef.sai_types import VioOutput, VioSession, MapperOutput

T = TypeVar('T')

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
    "Matches DepthAI packets with timestamps"
    def getTimestamp(self) -> timedelta: ...
    def getTimestampDevice(self) -> timedelta: ...


class MoeNetSession:
    _device_require_ts: 'timedelta'

    def __init__(self, device: dai.Device, pipeline: 'MoeNetPipeline', log: Optional['logging.Logger'] = None) -> None:
        self.device = device
        self.pipeline = pipeline
        self.log = (log.getChild if log is not None else logging.getLogger)('sesson')
        self.clock = WallClock()

        self.labels = pipeline.labels
        self.log.info("Streams: %s", device.getOutputQueueNames())

        def make_queue(node: Optional['XLinkOut[T]'], *, maxSize: int = 4) -> QueueLike[T]:
            if node is None:
                return QueueLike()
            return device.getOutputQueue(node.getStreamName(), maxSize=maxSize, blocking=False)
        self.queue_dets = make_queue(pipeline.node_out_nn)
        self.queue_sysinfo = make_queue(pipeline.node_out_sysinfo, maxSize=1)

        # Video streams
        self.queue_rgb = make_queue(pipeline.node_out_rgb, maxSize=1)
        self.queue_left = make_queue(pipeline.node_out_left, maxSize=1)
        self.queue_right = make_queue(pipeline.node_out_right, maxSize=8)
        self.queue_depth = make_queue(pipeline.node_out_depth, maxSize=1)
        
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
        now_dai: timedelta = dai.Clock.now()
        now_wall = self.clock.now()
        latency = now_dai - ts_dai

        # Update system -> device time
        self._offset_dev_to_dai = ts_dev - ts_dai

        return now_wall - latency

    def _poll_rgb(self):
        raw_rgb = self.queue_rgb.tryGet()
        recv = self.clock.now_ns()
        if raw_rgb is None or ('rgb' not in self.streams):
            return None
        raw_frame = raw_rgb.getCvFrame()
        ts = self.local_timestamp(raw_rgb)
        return MsgFrame(
            worker='',
            stream='rgb',
            timestamp=ts.nanos,
            timestamp_recv=recv,
            sequence=raw_rgb.getSequenceNum(),
            data=raw_frame,
        )

    def _poll_left(self):
        raw_frame = self.queue_left.tryGet()
        recv = self.clock.now_ns()
        if raw_frame is None or ('left' not in self.streams):
            return None
        ts = self.local_timestamp(raw_frame)
        return MsgFrame(
            worker='',
            stream='left',
            timestamp=ts.nanos,
            timestamp_recv=recv,
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