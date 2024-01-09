from typing import List, Optional, Literal, Union, Tuple
from pydantic import BaseModel, Field
from networktables import NetworkTablesInstance
if __name__ == '__main__':
    from common import NNConfig, SlamConfigBase, OakSelector, AprilTagFieldJSON, FieldLayoutJSON, FieldTagJSON
    from geom import Pose
else:
    from .common import NNConfig, SlamConfigBase, OakSelector, AprilTagFieldJSON, FieldLayoutJSON, FieldTagJSON
    from .geom import Pose

class NetworkTablesConfig(BaseModel):
    "Configure NetworkTables. Must be provided locally"
    team: int = Field(365, description="FRC team number")
    port: int = NetworkTablesInstance.DEFAULT_PORT
    
    "FRC team number"
    enabled: bool = True
    host: Optional[str] = Field(description="NetworkTables host IP")
    client_id: str = Field("MOEnet", description="Client connection name")
    "Connection client name"
    table: str = Field("moenet", description="Root table name")
    "Root table name"

    log_level: str = Field("error", description="Minimum level to send logs")
    log_lines: int = Field(10, description="Number of log lines to retain")

    subscribeSleep: bool = Field(True, description="Should we listen for sleep control at `/moenet/rio_request_sleep`?")
    subscribeConfig: bool = Field(True, description="Should we listen for config updates at `/moenet/rio_dynamic_config`?")

    publishLog: bool = Field(True, description="Should we publish logs to `/moenet/client_log`?")
    publishPing: bool = Field(True, description="Should we publish ping updates to `/moenet/client_ping`?")
    publishErrors: bool = Field(True, description="Should we publish errors updates to `/moenet/client_error`?")
    publishStatus: bool = Field(True)
    publishConfig: bool = Field(True, description="Should we publish this config to `/moenet/client_config`?")
    publishSystemInfo: bool = Field(True, description="Should we publish system info to `/moenet/client_telemetry`?")
    publishDetectionsRs: bool = Field(True, description="Publish object detections in robot-space to `/moenet/client_det_rs`")
    publishDetectionsFs: bool = Field(True, description="Publish object detections in field-space to `/moenet/client_det_fs`")
    tfFieldToRobot: Literal["sub", "pub", False] = Field("pub", description="field -> robot transform (absolute pose)")
    tfFieldToOdom: Literal["sub", "pub", False] = Field("pub", description="field -> odom transform (odometry estimate)")
    tfOodomToRobot: Literal["sub", "pub", False] = Field("pub", description="odom->robot transform (odometry correction)")

class ObjectDetectionDefinition(BaseModel):
    "Configure an object detection pipeline"
    id: str
    blobPath: str
    configPath: Optional[str]
    "Configuration path (relative to file)"
    config: Optional[NNConfig]

class NavXConfig(BaseModel):
    "NavX configuration"
    port: str

class AprilTagFieldRef(BaseModel):
    format: Literal["frc"]
    path: str = Field(description="Path to AprilTag configuration")
    tagFamily: str
    tagSize: float

class Vec4(BaseModel):
    __root__: Tuple[float, float, float, float]
class Mat44(BaseModel):
    __root__: Tuple[Vec4, Vec4, Vec4, Vec4]

class AprilTagInfo(BaseModel):
    id: str
    size: float
    family: str
    tagToWorld: Mat44

class AprilTagList(BaseModel):
    __root__: List[AprilTagInfo]

class AprilTagFieldConfig(BaseModel):
    field: FieldLayoutJSON
    tags: AprilTagList

class SlamConfig(SlamConfigBase):
    apriltag: Union[AprilTagFieldRef, AprilTagFieldConfig, None]

class CameraConfig(BaseModel):
    id: Optional[str] = Field(None, description="Human-readable name")
    selector: Union[str, OakSelector] = Field(description="Which camera are we referencing?")
    max_usb: Optional[Literal["FULL", "HIGH", "LOW", "SUPER", "SUPER_PLUS", "UNKNOWN"]]
    optional: bool = Field(False, description="Is it an error if this camera is not detected?")
    pose: Optional[Pose] = Field(description="Camera pose (in robot-space)")
    slam: Union[bool, SlamConfig] = Field(True, description="Enable SLAM on this camera")
    object_detection: Optional[str] = Field(None, description="Which object detection pipeline should we use?")

class LogConfig(BaseModel):
    level: str

class CameraSelectorConfig(OakSelector):
    id: str = Field(description="Human-readable ID")
    pose: Optional[Pose]

class LocalConfig(BaseModel):
    "Local config data"
    nt: NetworkTablesConfig
    timer: Union[Literal["system"], NavXConfig] = Field("system", description="Timer for synchronizing with RoboRIO")
    log: Optional[LogConfig]
    "Timer for synchronizing with RoboRIO"
    pipelines: List[ObjectDetectionDefinition]
    camera_selectors: Optional[List[CameraSelectorConfig]]
    cameras: List[CameraConfig]
    slam: Optional[SlamConfig] = None

    def merge(self, update: 'RemoteConfig') -> 'LocalConfig':
        result = self.copy()
        if update.slam is not None:
            result.slam = update.slam
        if update.cameras is not None:
            result.cameras

class RemoteConfig(BaseModel):
    slam: Optional[SlamConfig] = None
    cameras: List[CameraConfig]

def load_config(path: str) -> LocalConfig:
    "Load local config"
    return LocalConfig.parse_file(path)

if __name__ == '__main__':
    import json
    print(json.dumps(LocalConfig.schema(), indent=2))