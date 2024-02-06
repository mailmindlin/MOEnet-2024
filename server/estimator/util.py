from typedef.geom import Pose3d

def interpolate_pose3d(a: Pose3d, b: Pose3d, t: float) -> Pose3d:
	"Interpolate between `Pose3d`s"
	if t <= 0:
		return a
	if t >= 1:
		return b
	twist = a.log(b)
	return a.exp(twist * t)