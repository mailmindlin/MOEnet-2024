from typedef.geom import Pose3d, Transform3d

def lerp_pose3d(a: Pose3d, b: Pose3d, t: float) -> Pose3d:
	"Interpolate between `Pose3d`s"
	if t <= 0:
		return a
	if t >= 1:
		return b
	twist = a.log(b)
	return a.exp(twist * t)

def as_transform(a: Pose3d) -> Transform3d:
	return Transform3d(Pose3d(), a)
def as_pose(a: Transform3d) -> Pose3d:
	return Pose3d().transformBy(a)

def lerp_transform3d(a: Transform3d, b: Transform3d, t: float) -> Transform3d:
	"Interpolate between `Transform3d`s"
	if t <= 0:
		return a
	if t >= 1:
		return b
	aP = as_pose(a)
	bP = as_pose(b)
	twist = aP.log(bP)
	return as_transform(aP.exp(twist * t))
