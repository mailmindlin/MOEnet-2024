import spectacularAI
import depthai
import threading
import numpy as np
import time

from spectacularAI.cli.visualization.visualizer import Visualizer, VisualizerArgs

if __name__ == '__main__':
	configInternal = {"useExternalPoseOrientation" : "true"}
	visArgs = VisualizerArgs()
	visArgs.cameraFollow = False
	visArgs.targetFps = 30
	visualizer = Visualizer(visArgs)
	tStart = -1
	firstPose = None

	def onVioOutput(vioOutput, vioSession):
		global tStart
		global firstPose
		visualizer.onVioOutput(vioOutput.getCameraPose(0), status=vioOutput.status)

		if firstPose is None: firstPose = vioOutput.pose.asMatrix()
		if tStart < 0: tStart = time.time()

		# Every once-in-a-while, we will re-calibrate odometry using
		# some external sensors:
		ts = time.time()
		if (ts - tStart) > 5:
			print("Resetting...")
			tStart = ts
		
			# Calibrate the yaw to a known heading:
			# NOTE: this will not work well in practice because the poses aren't using consistent coordinate frame
			# (we always try to reset to first pose) and VIO state will easily explode... 
			# but you can use this approach if the external poses are accurate.
			newPose = spectacularAI.Pose.fromMatrix(vioOutput.pose.time, firstPose) # TODO: replace with a real pose

			covariance = 1e-5 * np.identity(3)
			orientationVariance = 1e-7
			vioSession.addAbsolutePose(newPose, covariance, orientationVariance)

	def captureLoop():
		print("Starting OAK-D device")
		pipeline = depthai.Pipeline()
		config = spectacularAI.depthai.Configuration()
		config.internalParameters = configInternal
		vioPipeline = spectacularAI.depthai.Pipeline(pipeline, config)

		with depthai.Device(pipeline) as device:
			with vioPipeline.startSession(device) as vioSession:
				while not visualizer.shouldQuit:
					onVioOutput(vioSession.waitForOutput(), vioSession)

	thread = threading.Thread(target=captureLoop)
	thread.start()
	visualizer.run()
	thread.join()