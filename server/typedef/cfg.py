"Type definitions for parsing the configuration"

from typing import List, Optional, Literal, Union, Tuple, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, RootModel, root_validator
from ntcore import NetworkTableInstance

if __name__ == '__main__':
    from common import NNConfig, SlamConfigBase, OakSelector, FieldLayoutJSON
    from geom import Pose
else:
    from .common import NNConfig, SlamConfigBase, OakSelector, FieldLayoutJSON
    from .geom import Pose

class NetworkTablesConfig(BaseModel):
    "Configure NetworkTables. Must be provided locally"
    enabled: bool = Field(True, "Should anything be sent to NetworkTables?")

    # Connection info
    team: int = Field(365, description="FRC team number")
    port: int = Field(NetworkTableInstance.kDefaultPort4, description="Which port should we connect to?")
    host: Optional[str] = Field(None, description="NetworkTables host IP")
    client_id: str = Field("MOEnet", description="Client connection name")
    
    table: str = Field("moenet", description="Root table name")

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
    blobPath: Path = Field(description="Path to NN blob")
    configPath: Optional[Path] = Field(None, description="Path to NN config")
    "Configuration path (relative to file)"
    config: Optional[NNConfig] = Field(None, description="Inline NN config")

    @root_validator()
    def check_config_once(cls, values: Dict[str, Any]):
        if (values.get('configPath') is None) == (values.get("config") is None):
            raise ValueError('Exactly ONE of `config` and `configPath` are required')
        return values

class NavXConfig(BaseModel):
    "NavX configuration"
    port: str = Field(description="NavX serial port path")
    update_rate: int = Field(60, description="NavX poll rate (in hertz)", gt=0, le=255)

class AprilTagFieldRef(BaseModel):
    "Reference to a WPIlib AprilTag JSON file"
    format: Literal["frc"]
    path: Path = Field(description="Path to AprilTag configuration")
    tagFamily: Literal['16h5', '25h9', '36h11'] = Field(description="AprilTag family")
    tagSize: float = Field(description="AprilTag side length, in meters")

Vec4 = RootModel[Tuple[float, float, float, float]]
Mat44 = RootModel[Tuple[Vec4, Vec4, Vec4, Vec4]]

class AprilTagInfo(BaseModel):
    id: int
    size: float
    family: str
    tagToWorld: Mat44

AprilTagList = RootModel[List[AprilTagInfo]]

class AprilTagFieldConfig(BaseModel):
    field: FieldLayoutJSON
    tags: AprilTagList

class PoseEstimatorConfig(BaseModel):
    "Configuration for "
    pass

class SlamConfig(SlamConfigBase):
    apriltag: Union[AprilTagFieldRef, AprilTagFieldConfig, None]

class CameraConfig(BaseModel):
    id: Optional[str] = Field(None, description="Human-readable name")
    selector: Union[str, OakSelector] = Field(description="Which camera are we referencing?")
    max_usb: Optional[Literal["FULL", "HIGH", "LOW", "SUPER", "SUPER_PLUS", "UNKNOWN"]] = Field(None)
    optional: bool = Field(False, description="Is it an error if this camera is not detected?")
    pose: Optional[Pose] = Field(description="Camera pose (in robot-space)")
    slam: Union[bool, SlamConfig] = Field(False, description="Enable SLAM on this camera")
    object_detection: Optional[str] = Field(None, description="Which object detection pipeline should we use?")

class LogConfig(BaseModel):
    """
    Configuration for logging output
    """
    level: Literal['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'] = Field('DEBUG')
    file: Optional[str]

class CameraSelectorConfig(OakSelector):
    id: str = Field(description="Human-readable ID")
    pose: Optional[Pose] = None

class LocalConfig(BaseModel):
    "Local config data"
    nt: NetworkTablesConfig
    timer: Union[Literal["system"], NavXConfig] = Field("system", description="Timer for synchronizing with RoboRIO")
    log: Optional[LogConfig]
    pipelines: List[ObjectDetectionDefinition]
    camera_selectors: List[CameraSelectorConfig] = Field(default_factory=list)
    cameras: List[CameraConfig]
    slam: Optional[SlamConfig] = Field(None)

    def merge(self, update: 'RemoteConfig') -> 'LocalConfig':
        "Merge in a remote configuration"
        result = self.model_copy()
        if update.slam is not None:
            result.slam = update.slam
        if update.cameras is not None:
            for i, camera in enumerate(update.cameras):
                if isinstance(camera.slam, SlamConfig) and isinstance(camera.slam.apriltag, AprilTagFieldRef):
                    raise ValueError(f'Invalid remote config: camera #{i} has a file reference')
            result.cameras = update.cameras

class RemoteConfig(BaseModel):
    slam: Optional[SlamConfig] = None
    cameras: List[CameraConfig]

if __name__ == '__main__':
    import json
    print(json.dumps(LocalConfig.model_json_schema(), indent='\t'))