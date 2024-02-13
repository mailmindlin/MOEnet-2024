from typing import TYPE_CHECKING, Any, Optional
if TYPE_CHECKING:
	import numpy as np
	from depthai.node import MonoCamera, StereoDepth, ColorCamera
	from depthai import Device

	class Configuration:
		accFrequencyHz: int
		aprilTagPath: str
		"Path to .json file with AprilTag information. AprilTag detection is enabled when not empty. For the file format see: https://github.com/SpectacularAI/docs/blob/main/pdf/april_tag_instructions.pdf. Note: sets useSlam=true"
		def asDict(self) -> dict:
			"Dictionary representation of this configuration."
			pass
		def update(self, **kwargs):
			"Update the contents of this object with kwargs corresponding to a subset of the member names"
			pass

		depthQueueSize: int

		disableCameras: bool
		"Disables cameras + VIO, only useful for recording."

		ensureSufficientUsbSpeed: bool
		extendedDisparity: bool
		"Use DepthAI extended disparity mode"

		fastImu: bool
		fastVio: bool
		"Use more light-weight VIO settings"

		forceRectified: bool
		forceUnrectified: bool
		gyroFrequencyHz: int

		imuQueueSize: int
		imuToGnss: int
		inputResolution: str
		internalParameters: dict[str, str]
		"Internal SDK parameters (key-value pairs converted to string-string). Not safe for unsanitized user input"

		keyframeCandidateEveryNthFrame: int
		"When useSlam = True, useFeatureTracker = True and keyframeCandidateEveryNthFrame > 0, a mono gray image is captured every N frames for SLAM."

		mapLoadPath: Optional[str]
		"Load existing SLAM map (.bin format required)"

		mapSavePath: Optional[str]
		"Output filename. Supported outputs types: .ply, .csv and .pcd (point cloud), and .bin (Spectacular AI SLAM map)."

		monoQueueSize: int
		recordingFolder: Optional[str]
		recordingOnly: bool
		"Disables VIO and only records session when recordingFolder is set."

		silenceUsbWarnings: bool

		useColor: bool
		"Use DepthAI color camera for tracking. Only supported for OAK-D series 2."

		useColorStereoCameras: bool
		"When device has stereo color cameras"

		useEncodedVideo: bool
		"Encode stereo camera video on the OAK-D device, cannot be used for live tracking"

		useFeatureTracker: bool
		"Use Movidius VPU-accelelerated feature tracking"

		useGrayDepth: bool
		"Use one gray frame and depth for tracking"

		useSlam: bool
		"Enable the SLAM module"

		useStereo: bool
		"Use stereo vision. Set to false for monocular mode (i.e., using one camera only)."

		useVioAutoExposure: bool
		"Enable SpectacularAI auto exposure which optimizes exposure parameters for VIO performance (BETA)"

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
		def asMatrix(self) -> np.ndarray: ...
	
	class Camera:
		def getIntrinsicMatrix(self) -> np.ndarray: ...
	
	class CameraPose:
		pose: Pose
		camera: Camera
		def getCameraToWorldMatrix(self) -> np.ndarray: ...
		def getPosition(self) -> Vector3d: ...
		def getWorldToCameraMatrix(self) -> np.ndarray: ...
	
	class VioOutput:
		angularVelocity: Vector3d
		pose: Pose
		poseTrail: list[Pose]
		positionCovariance: np.ndarray
		tag: int
		velocity: Vector3d
		velocityCovariance: np.ndarray

		def getCameraPose(self, id: int) -> CameraPose: ...
	
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
		def addAbsolutePose(self, /, arg0: Pose, arg1: list[list[float[3]][3]], arg2: float) -> None:
			"Add external pose information.VIO will correct its estimates to match the pose."
		def addGnss(self, /, arg0: float, arg1: WgsCoordinates, arg2: list[list[float[3]][3]]) -> None:
			"Add GNSS input (for GNSS-VIO fusion)"

		def addTrigger(self, /, arg0: float, arg1: int) -> None:
			"Add an external trigger input. Causes additional output corresponding to a certain timestamp to be generated."

		def close(self) -> None:
			"Close VIO session and free resources. Also consider using the with statement"

		def getOutput(self) -> VioOutput:
			"Removes the first unread output from an internal queue and returns it"

		def getRgbCameraPose(self, /, arg0: VioOutput) -> CameraPose:
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
		keyFrames: dict[int, KeyFrame]
	
	class MapperOutput:
		finalMap: bool
		map: Map
		updatedKeyFrames: list[int]
	
	class Pipeline:
		monoLeft: MonoCamera
		monoRight: MonoCamera
		stereo: StereoDepth
		color: ColorCamera

		def startSession(self, /, arg0: Device) -> VioSession: ...