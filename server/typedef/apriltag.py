from typing import Literal, Annotated, Union, TYPE_CHECKING
from pydantic import RootModel, BaseModel, Field, Discriminator, Tag
from pathlib import Path
# Import for conversions
import numpy as np
from scipy.spatial.transform import Rotation
try:
    from . import geom
except ImportError:
    import geom
if TYPE_CHECKING:
    import robotpy_apriltag

FLIP_SAI = True
"We're supposed to flip SAI coordinates, but idk"

Vec4 = RootModel[tuple[float, float, float, float]]
Mat44 = RootModel[tuple[Vec4, Vec4, Vec4, Vec4]]

AprilTagFamily = Literal['tag16h5', 'tag25h9', 'tag36h11']

class SaiAprilTag(BaseModel):
    id: int = Field(description="AprilTag id", ge=0)
    size: float = Field(description="Tag size (meters)")
    family: AprilTagFamily = Field(description="Tag family")
    tagToWorld: Mat44
    def to_wpi(self) -> 'WpiFieldTag':
        matrix = np.asarray(self.tagToWorld, dtype=float)

        r_matrix = matrix[:3, :3]
        [x,y,z] = matrix[:3,3]

        r = Rotation.from_matrix(r_matrix)
        [i, j, k, w] = r.as_quat()

        position = geom.Translation3d(x, y, z)
        rotation = geom.Rotation3d(geom.Quaternion(w, i, j, k))#TODO: we might be able to the matrix constructor

        tagToField = geom.Transform3d(position, rotation)
        fieldToTag = tagToField.inverse() if FLIP_SAI else fieldToTag
        return WpiFieldTag(
            ID=self.id,
            pose=geom.Pose3d(fieldToTag.translation(), fieldToTag.rotation())
        )

    def to_sai(self, tagFamily: AprilTagFamily, tagSize: float) -> 'SaiAprilTag':
        return self

SaiAprilTagList = RootModel[list[SaiAprilTag]]

class FieldLayout(BaseModel):
    length: float = Field(description="Field length (meters)")
    width: float = Field(description="Field width (meters)")

class WpiFieldTag(BaseModel):
    ID: int = Field(description="AprilTag id", ge=0)
    pose: geom.Pose3d = Field(description="AprilTag pose, in field-space (field->tag)")
    def to_wpilib(self) -> 'robotpy_apriltag.AprilTag':
        import robotpy_apriltag
        res = robotpy_apriltag.AprilTag()
        res.ID = self.ID
        res.pose = self.pose
        return res
    
    def to_wpi(self) -> 'WpiFieldTag':
        return self
    def to_sai(self, tagFamily: AprilTagFamily, tagSize: float) -> SaiAprilTag:
        fieldToTag = geom.Transform3d(self.pose.translation(), self.pose.rotation())
        tagToField = fieldToTag.inverse() if FLIP_SAI else fieldToTag
        position = tagToField.translation()
        orientation = tagToField.rotation().getQuaternion()
        x, y, z = position.x, position.y, position.z
        i, j, k, w = orientation.X(), orientation.Y(), orientation.Z(), orientation.W()

        # create rotation matrix
        r = Rotation.from_quat([i, j, k, w])
        r_matrix = r.as_matrix()

        # create homogenous matrix
        matrix = np.eye(4) # 4x4 identity matrix
        matrix[:3, :3] = r_matrix # first 3 in rows and columns
        matrix[:3, 3] = [x, y, z] # first 3 in rows, last in columns
        return SaiAprilTag(
            id=self.ID,
            size=tagSize,
            family=tagFamily,
            tagToWorld=matrix
        )

class WpiAprilTagField(BaseModel):
    "Format of WPIlib AprilTag JSON files"
    field: FieldLayout
    tags: list[WpiFieldTag]

class AprilTagFieldBase(BaseModel):
    format: Literal["wpi", "sai"]

    def load(self, base: Path | None = None) -> 'InlineAprilTagField':
        raise NotImplementedError()

class InlineAprilTagFieldBase(AprilTagFieldBase):
    field: FieldLayout = Field(description="Field size")
    def load(self, base: Path | None = None) -> 'InlineAprilTagField':
        return self

class WpiInlineAprilTagField(InlineAprilTagFieldBase):
    "Inline AprilTag config (WPI format)"
    format: Literal["wpi"]
    tags: list[WpiFieldTag] = Field(description="AprilTags (WPI format)")
    tagFamily: AprilTagFamily = Field(description="AprilTag family")
    tagSize: float = Field(description="AprilTag side length, in meters")
    def to_sai_inline(self) -> 'SaiInlineAprilTagField':
        return SaiInlineAprilTagField(
            format='sai',
            field=self.field,
            tags=[
                tag.to_sai(self.tagFamily, self.tagSize)
                for tag in self.tags
            ]
        )
    def to_wpi_inline(self) -> 'WpiInlineAprilTagField':
        return self
    
    def store(self, base: Path) -> 'WpiAprilTagFieldRef':
        pass

    def to_wpilib(self) -> 'robotpy_apriltag.AprilTagFieldLayout':
        from robotpy_apriltag import AprilTag, AprilTagFieldLayout
        return AprilTagFieldLayout(
            [
                tag.to_wpilib()
                for tag in self.tags
            ],
            self.field.length,
            self.field.width,
        )


class SaiInlineAprilTagField(InlineAprilTagFieldBase):
    "Inline AprilTag config (SAI format)"
    format: Literal["sai"]
    tags: SaiAprilTagList = Field(description="AprilTags (SAI format)")
    def to_sai_inline(self):
        return self

    def to_wpi_inline(self) -> 'WpiInlineAprilTagField':
        return self
    
    def store(self, base: Path) -> 'SaiAprilTagFieldRef':
        pass

InlineAprilTagField = Annotated[
    Union[
        Annotated[WpiInlineAprilTagField, Tag("wpi")],
        Annotated[SaiInlineAprilTagField, Tag("sai")],
    ],
    Discriminator("format")
]

class AprilTagFieldRefBase(AprilTagFieldBase):
    "Reference to an AprilTag JSON file"
    path: Path = Field(description="Path to AprilTag configuration")
    def load_raw(self, base: Path | None = None) -> str:
        res_path = self.path if (base is None) else (base / self.path)
        res_path = res_path.resolve()
        with open(res_path, 'r') as f:
            return f.read()
    

class WpiAprilTagFieldRef(AprilTagFieldRefBase):
    "Reference to an AprilTag JSON file (in WPIlib format)"
    format: Literal["wpi"]
    tagFamily: AprilTagFamily = Field(description="AprilTag family")
    tagSize: float = Field(description="AprilTag side length, in meters")
    def load(self, base: Path | None = None) -> InlineAprilTagField:
        text = self.load_raw(base)
        data = WpiAprilTagField.model_validate_json(text)
        return WpiInlineAprilTagField(
            format='wpi',
            field=data.field,
            tags=data.tags,
            tagFamily=self.tagFamily,
            tagSize=self.tagSize,
        )

class SaiAprilTagFieldRef(AprilTagFieldRefBase):
    "Reference to an AprilTag JSON file (in SpectacularAI format)"
    format: Literal["sai"]
    field: FieldLayout

    def load(self, base: Path | None = None) -> InlineAprilTagField:
        text = self.load_raw(base)
        data = SaiAprilTagList.model_validate_json(text)
        return SaiInlineAprilTagField(
            format='sai',
            field=self.field,
            tags=data
        )


AprilTagFieldRef = Annotated[
    Union[
        Annotated[WpiAprilTagFieldRef, Tag("frc")],
        Annotated[SaiAprilTagFieldRef, Tag("sai")],
    ],
    Discriminator("format")
]