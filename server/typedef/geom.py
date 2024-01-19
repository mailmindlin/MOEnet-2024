from pydantic import BaseModel, Field
from wpimath import geometry

class Vector3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_wpi(self):
        return geometry.Translation3d(self.x, self.y, self.z)

class Quaternion(BaseModel):
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def as_wpi(self):
        return geometry.Quaternion(w=self.w, x=self.x, y=self.y, z=self.z)

class Pose(BaseModel):
    translation: Vector3 = Field(default_factory=Vector3)
    rotation: Quaternion = Field(default_factory=Quaternion)

    @staticmethod
    def from_wpi(pose: geometry.Pose3d) -> 'Pose':
        rot = pose.rotation().getQuaternion()
        return Pose(
            translation=Vector3(x=pose.x, y=pose.y, z=pose.z),
            rotation=Quaternion(w=rot.W(), x=rot.X(), y=rot.Y(), z=rot.Z())
        )

    def as_pose(self):
        return geometry.Pose3d(
            self.translation.as_wpi(),
            geometry.Rotation3d(self.rotation.as_wpi())
        )
    def as_transform(self):
        return geometry.Transform3d(
            self.translation.as_wpi(),
            geometry.Rotation3d(self.rotation.as_wpi())
        )

class Twist(BaseModel):
    velocity: Vector3 = Field(default_factory=Vector3)
    rotation: Vector3 = Field(default_factory=Vector3)
    