from typing import TYPE_CHECKING, Any, List, Dict, Optional
if TYPE_CHECKING:
    import numpy as np

    class Vector3d:
        x: float
        y: float
        z: float
    
    class Quaternion:
        w: float
        x: float
        y: float
        z: float
    
    class Pose:
        orientation: Quaternion
        position: Vector3d
        time: float
        def asMatrix(self) -> np.ndarray:
            ...
    
    class Camera:
        def getIntrinsicMatrix(self) -> np.ndarray:
            ...
    
    class CameraPose:
        pose: Pose
        camera: Camera
    
    class VioOutput:
        angularVelocity: Vector3d
        pose: Pose
        poseTrail: List[Pose]
        positionCovariance: np.ndarray
        tag: int
        velocity: Vector3d
        velocityCovariance: np.ndarray

        def getCameraPose(self, id: int) -> CameraPose:
            ...
    
    class WgsCoordinates:
        "Represents the pose (position & orientation) of a device at a given time."
        altitude: float
        latitude: float
        longitude: float
    
    class VioSession:
        def hasOutput(self) -> bool:
            pass
        def getOutput(self) -> VioOutput:
            pass
        def addAbsolutePose(self, arg0: Pose, arg1: List[List[float[3]][3]], arg2: float) -> None:
            "Add external pose information.VIO will correct its estimates to match the pose."
        def addGnss(self, arg0: float, arg1: WgsCoordinates, arg2: List[List[float[3]][3]]) -> None:
            "Add GNSS input (for GNSS-VIO fusion)"

        def addTrigger(self, arg0: float, arg1: int) -> None:
            "Add an external trigger input. Causes additional output corresponding to a certain timestamp to be generated."

        def close(self) -> None:
            "Close VIO session and free resources. Also consider using the with statement"

        def getOutput(self) -> VioOutput:
            "Removes the first unread output from an internal queue and returns it"

        def getRgbCameraPose(self, arg0: VioOutput) -> CameraPose:
            "Get the CameraPose corresponding to the OAK RGB camera at a certain VioOutput."

        def hasOutput(self) -> bool:
            "Check if there is new output available"

        def waitForOutput(self) -> VioOutput:
            "Waits until there is new output available and returns it"

    class Frame:
        cameraPose: CameraPose
        depthScale: Optional[float]
        image: Any

    class FrameSet:
        depthFrame: Frame
        primaryFrame: Frame
        rgbFrame: Optional[Frame]
        secondaryFrame: Frame
    
    class KeyFrame:
        frameSet: FrameSet
        id: int
        pointCloud: Any
    
    class Map:
        keyFrames: Dict[int, KeyFrame]
    
    class MapperOutput:
        finalMap: bool
        map: Map
        updatedKeyFrames: List[int]