from typing import TYPE_CHECKING, Literal, Annotated, Union, TypeVar, Callable, Type, cast
from pydantic import RootModel, BaseModel, Field, Discriminator, Tag
from pathlib import Path
import enum, abc
# Import for conversions
import numpy as np
from scipy.spatial.transform import Rotation
import tempfile
try:
    from . import geom, common
except ImportError:
    import geom, common
if TYPE_CHECKING:
    import robotpy_apriltag
    import depthai as dai

FLIP_SAI = False
"We're supposed to flip SAI coordinates, but idk"

class AprilTagFamily(enum.StrEnum):
    TAG_16H5 = 'tag16h5'
    TAG_25H9 = 'tag25h9'
    TAG_36H10 = 'tag36h10'
    TAG_36H11 = 'tag36h11'
    TAG_CIR21H7 = 'tagCircle21h7'
    TAG_STAND41H12 = 'tagStandard41h12'

    def as_dai(self) -> 'dai.AprilTagConfig.Family':
        match self:
            case AprilTagFamily.TAG_16H5:
                return dai.AprilTagConfig.Family.TAG_16H5
            case AprilTagFamily.TAG_25H9:
                return dai.AprilTagConfig.Family.TAG_25H9
            case AprilTagFamily.TAG_36H10:
                return dai.AprilTagConfig.Family.TAG_36H10
            case AprilTagFamily.TAG_36H11:
                return dai.AprilTagConfig.Family.TAG_36H11
            case AprilTagFamily.TAG_CIR21H7:
                return dai.AprilTagConfig.Family.TAG_CIR21H7
            case AprilTagFamily.TAG_STAND41H12:
                return dai.AprilTagConfig.Family.TAG_STAND41H12
            case _:
                raise ValueError(f'Unknown AprilTag family {self}')

class AprilTagBase(abc.ABC):
    id: int

    def to_wpilib(self) -> 'robotpy_apriltag.AprilTag':
        pass
    @abc.abstractmethod
    def to_wpi(self) -> 'AprilTagWpi':
        assert isinstance(self, AprilTagWpi)
        return self
    @abc.abstractmethod
    def to_sai(self, tagFamily: AprilTagFamily, tagSize: float) -> 'AprilTagSai':
        "Convert to SpectacularAI format"
        assert isinstance(self, AprilTagSai)
        return self

class AprilTagSai(BaseModel, AprilTagBase):
    id: int = Field(description="AprilTag id", ge=0)
    size: float = Field(description="Tag size (meters)", ge=0, allow_inf_nan=False)
    family: AprilTagFamily = Field(description="Tag family")
    tagToWorld: common.Mat44
    def get_sai_matrix(self) -> np.ndarray:
        "Get SpectacularAI tag-to-world matrix"
        return np.asarray([
            [
                item
                for item in row.root
            ]
            for row in self.tagToWorld.root
        ])
    def to_wpi(self) -> 'AprilTagWpi':
        matrix = np.asarray(self.tagToWorld, dtype=float)

        r_matrix = matrix[:3, :3]
        [x,y,z] = matrix[:3,3]

        r = Rotation.from_matrix(r_matrix)
        [i, j, k, w] = r.as_quat(False)

        position = geom.Translation3d(x, y, z)
        rotation = geom.Rotation3d(geom.Quaternion(w, i, j, k))#TODO: we might be able to the matrix constructor

        tagToField = geom.Transform3d(position, rotation)
        fieldToTag = tagToField.inverse() if FLIP_SAI else tagToField
        return AprilTagWpi(
            ID=self.id,
            pose=geom.Pose3d(fieldToTag.translation(), fieldToTag.rotation())
        )

    def to_sai(self, tagFamily: AprilTagFamily, tagSize: float) -> 'AprilTagSai':
        return self

AprilTagJsonSai = RootModel[list[AprilTagSai]]

class FieldLayout(BaseModel):
    length: float = Field(description="Field length (meters)")
    width: float = Field(description="Field width (meters)")

class AprilTagWpi(BaseModel):
    "A single AprilTag definition (WPI format)"

    @staticmethod
    def from_wpilib(src: 'robotpy_apriltag.AprilTag') -> 'AprilTagWpi':
        return AprilTagWpi(
            ID=src.ID,
            pose=src.pose,
        )
    
    ID: int = Field(description="AprilTag id", ge=0)
    pose: geom.Pose3d = Field(description="AprilTag pose, in field-space (field->tag)")
    def to_wpilib(self) -> 'robotpy_apriltag.AprilTag':
        import robotpy_apriltag
        res = robotpy_apriltag.AprilTag()
        res.ID = self.ID
        res.pose = self.pose
        return res
    
    def to_wpi(self) -> 'AprilTagWpi':
        return self
    def to_sai(self, tagFamily: AprilTagFamily, tagSize: float) -> AprilTagSai:
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
        return AprilTagSai(
            id=self.ID,
            size=tagSize,
            family=tagFamily,
            tagToWorld=matrix
        )

class AprilTagJsonWpi(BaseModel):
    "Format of WPIlib AprilTag JSON files"
    field: FieldLayout
    tags: list[AprilTagWpi]


class _AprilTagField(BaseModel):
    format: Literal["wpi", "sai"]

    @staticmethod
    def from_wpilib(field: Union['robotpy_apriltag.AprilTagFieldLayout', 'robotpy_apriltag.AprilTagField']) -> '_AprilTagField':
        raise NotImplementedError()

    def _resolve_path(self, base: Path | None, relpart: Path) -> Path:
        from util.path import resolve_path
        return resolve_path(base, relpart)
    
    def resolve(self, base: Path | None = None) -> '_AprilTagField':
        "Resolve path references (if any) relative to a base folder"
        return self
    
    # def as_inline_sai(self, base: Path | None = None) -> 'AprilTagFieldInlineSai':
    #     return self.load(base).as_inline_sai()
    
    # def as_inline_wpi(self, base: Path | None = None) -> 'AprilTagFieldInlineWpi':
    #     return self.load(base).as_inline_wpi()

    def validate(self, base: Path | None):
        "Validate that this has valid field data"
        self.model_validate(self)
    
    def convert(self, target: Type['F'], base: Path, tempdir: Callable[[], Path]) -> 'F':
        "Convert to another AprilTagField type"
        current = self.resolve(base)
        if isinstance(current, target):
            return current
        
        # Which transforms do we need to do?
        need_load = False
        need_store = False
        if issubclass(target, _AprilTagFieldInline):
            need_load = True
        if issubclass(target, _AprilTagFieldRef):
            need_store = True
        
        # Get target format
        if issubclass(target, _AprilTagFieldSai):
            target_format = 'sai'
        elif issubclass(target, _AprilTagFieldWpi):
            target_format = 'wpi'
        else:
            # If not specified, don't convert
            target_format = None
        if need_store and (target_format is not None) and (self.format != target_format):
            need_load = True

        if need_load:
            current = self.load(base)
        else:
            current = cast(AprilTagFieldInline, current)
        
        # Convert type
        if target_format in (current.format, None):
            # No conversion needed
            pass
        elif target_format == 'sai':
            current = current.as_inline_sai()
        elif target_format == 'wpi':
            current = current.as_inline_wpi()
        else:
            raise ValueError()
        
        if need_store:
            current = current.store(tempdir)
        
        current = current.resolve(base)
        
        return current
    
    @abc.abstractmethod
    def store(self, tempdir: Callable[[], Path]) -> 'AprilTagFieldRef':
        "Convert this field into a reference, by storing data in `tempdir`"
        pass

    def load(self, base: Path | None = None) -> 'AprilTagFieldInline':
        raise NotImplementedError()

class _AprilTagFieldWpi(_AprilTagField, abc.ABC):
    "WPI-format AprilTag data"
    format: Literal["wpi"] = Field(default_factory=lambda: 'wpi')

class _AprilTagFieldSai(_AprilTagField, abc.ABC):
    "SpectacularAI-format AprilTag data"
    format: Literal["sai"] = Field(default_factory=lambda: 'sai')

class _AprilTagFieldInline(_AprilTagField, abc.ABC):
    "Inline AprilTag info"
    field: FieldLayout = Field(description="Field size")
    def load(self, base: Path | None = None) -> 'AprilTagFieldInline':
        return self
    
    def to_wpilib(self) -> 'robotpy_apriltag.AprilTagFieldLayout':
        return self.as_inline_wpi().to_wpilib()

class _AprilTagFieldRef(_AprilTagField, abc.ABC):
    "Reference to an AprilTag JSON file"
    path: Path = Field(description="Path to AprilTag configuration")

    def validate(self, base: Path | None):
        super().validate(base)
        self._load_data(base)
    
    def store(self, tempdir: Callable[[], Path]) -> '_AprilTagFieldRef':
        return self
    
    def resolve(self, base: Path | None = None) -> '_AprilTagFieldRef':
        return self.model_copy(
            update=dict(
                path=self._resolve_path(base, self.path)
            )
        )
    
    def _load_raw(self, base: Path | None = None) -> str:
        "Load raw JSON"
        res_path = self._resolve_path(base, self.path)
        with open(res_path, 'r') as f:
            return f.read()
    
    @abc.abstractmethod
    def _load_data(self, base: Path | None = None):
        pass


class AprilTagFieldInlineWpi(_AprilTagFieldInline, _AprilTagFieldWpi):
    "Inline AprilTag config (WPI format)"
    format: Literal["wpi"] = Field(default_factory=lambda: 'wpi')
    tags: list[AprilTagWpi] = Field(description="AprilTags (WPI format)")
    tagFamily: AprilTagFamily = Field(description="AprilTag family")
    tagSize: float = Field(description="AprilTag side length, in meters")

    @staticmethod
    def from_wpilib(field: Union['robotpy_apriltag.AprilTagFieldLayout', 'robotpy_apriltag.AprilTagField']) -> 'AprilTagFieldInlineWpi':
        raise NotImplementedError()
    
    def as_inline_sai(self, path: Path | None = None) -> 'AprilTagFieldInlineSai':
        return AprilTagFieldInlineSai(
            field=self.field,
            tags=[
                tag.to_sai(self.tagFamily, self.tagSize)
                for tag in self.tags
            ]
        )
    def as_inline_wpi(self, path: Path | None = None) -> 'AprilTagFieldInlineWpi':
        return self
    
    def store(self, tempdir: Callable[[], Path]) -> 'AprilTagFieldRefWpi':
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=tempdir(),
            delete=False,
            prefix='apriltag_',
            suffix='.json',
        ) as f:
            data = AprilTagJsonWpi(
                field=self.field,
                tags=self.tags,
            )
            f.write(data.model_dump_json())
            path = Path(f.name)
        return AprilTagFieldRefWpi(
            path=path,
            tagFamily=self.tagFamily,
            tagSize=self.tagSize,
        )

    def to_wpilib(self) -> 'robotpy_apriltag.AprilTagFieldLayout':
        from robotpy_apriltag import AprilTagFieldLayout
        return AprilTagFieldLayout(
            [
                tag.to_wpilib()
                for tag in self.tags
            ],
            self.field.length,
            self.field.width,
        )


class AprilTagFieldInlineSai(_AprilTagFieldInline, _AprilTagFieldSai):
    "Inline AprilTag config (SAI format)"
    format: Literal["sai"] = Field(default_factory=lambda: 'sai')
    tags: list[AprilTagSai] = Field(description="AprilTags (SAI format)")
    def as_inline_sai(self, path: Path | None = None):
        return self

    def as_inline_wpi(self, path: Path | None = None) -> 'AprilTagFieldInlineWpi':
        if len(self.tags) == 0:
            family = AprilTagFamily.TAG_16H5
            size = 1.0
        else:
            family = self.tags[0].family
            size = self.tags[0].size
        tags = list()
        for tag in self.tags:
            assert tag.family == family
            assert (tag.size - size) < 1e-6
            tags.append(tag.to_wpi())
        
        return AprilTagFieldInlineWpi(
            field=self.field,
            tags=tags,
            tagFamily=family,
            tagSize=size,
        )
    
    def store(self, tempdir: Callable[[], Path]) -> 'AprilTagFieldRefSai':
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=tempdir(),
            delete=False,
            prefix='apriltag_',
            suffix='.json',
        ) as f:
            data = AprilTagJsonSai(root=self.tags)
            f.write(data.model_dump_json())
            path = Path(f.name)
        return AprilTagFieldRefSai(
            path=path,
            field=self.field,
        )


class AprilTagFieldRefWpi(_AprilTagFieldRef, _AprilTagFieldWpi):
    "Reference to an AprilTag JSON file (in WPIlib format)"
    format: Literal["wpi"] = Field(default_factory=lambda: 'wpi')
    tagFamily: AprilTagFamily = Field(description="AprilTag family")
    tagSize: float = Field(description="AprilTag side length, in meters")

    def load(self, base: Path | None = None) -> AprilTagFieldInlineWpi:
        data = self._load_data(base)
        return AprilTagFieldInlineWpi(
            format='wpi',
            field=data.field,
            tags=data.tags,
            tagFamily=self.tagFamily,
            tagSize=self.tagSize,
        )
    
    def _load_data(self, base: Path | None = None):
        text = self._load_raw(base)
        data = AprilTagJsonWpi.model_validate_json(text)
        return data

class AprilTagFieldRefSai(_AprilTagFieldRef, _AprilTagFieldSai):
    "Reference to an AprilTag JSON file (in SpectacularAI format)"
    format: Literal["sai"] = Field(default_factory=lambda: 'sai')
    field: FieldLayout

    def load(self, base: Path | None = None) -> 'AprilTagFieldInlineSai':
        data = self._load_data(base)
        return AprilTagFieldInlineSai(
            field=self.field,
            tags=data,
        )
    
    def _load_data(self, base: Path | None = None):
        text = self._load_raw(base)
        data = AprilTagJsonSai.model_validate_json(text)
        return data


class AprilTagFieldNamedWpilib(enum.StrEnum):
    "Named AprilTag field"
    FRC_2022 = "2022RapidReact"
    FRC_2023 = "2023ChargedUp"
    FRC_2024 = "2024Crescendo"
    def as_wpilib(self):
        "Get associated wpilib AprilTagField"
        from robotpy_apriltag import AprilTagField
        match self:
            case AprilTagFieldNamedWpilib.FRC_2022:
                return AprilTagField.k2022RapidReact
            case AprilTagFieldNamedWpilib.FRC_2023:
                return AprilTagField.k2023ChargedUp
            case AprilTagFieldNamedWpilib.FRC_2024:
                return AprilTagField.k2024Crescendo
    def tagFamily(self):
        match self:
            case AprilTagFieldNamedWpilib.FRC_2022:
                return AprilTagFamily.TAG_16H5
            case AprilTagFieldNamedWpilib.FRC_2023:
                return AprilTagFamily.TAG_16H5
            case AprilTagFieldNamedWpilib.FRC_2024:
                return AprilTagFamily.TAG_36H11
    def tagSize(self):
        from wpimath.units import inchesToMeters
        match self:
            case AprilTagFieldNamedWpilib.FRC_2022:
                return inchesToMeters(6)
            case AprilTagFieldNamedWpilib.FRC_2023:
                return inchesToMeters(6)
            case AprilTagFieldNamedWpilib.FRC_2024:
                return inchesToMeters(6.5)
            
    def load_wpilib(self):
        from robotpy_apriltag import loadAprilTagLayoutField
        return loadAprilTagLayoutField(self.as_wpilib())
    
    def load(self, *args) -> AprilTagFieldInlineWpi:
        field_wpilib = self.load_wpilib()
        return AprilTagFieldInlineWpi(
            field=FieldLayout(
                length=field_wpilib.getFieldLength(),
                width=field_wpilib.getFieldWidth(),
            ),
            tags=[
                AprilTagWpi.from_wpilib(tag)
                for tag in field_wpilib.getTags()
            ],
            tagFamily=self.tagFamily(),
            tagSize=self.tagSize(),
        )

# ===== Annotated types =====

AprilTagFieldInline = Annotated[
    Union[
        Annotated[AprilTagFieldInlineWpi, Tag("wpi")],
        Annotated[AprilTagFieldInlineSai, Tag("sai")],
    ],
    Discriminator("format")
]

AprilTagFieldRef = Annotated[
    Union[
        Annotated[AprilTagFieldRefWpi, Tag("frc")],
        Annotated[AprilTagFieldRefSai, Tag("sai")],
    ],
    Discriminator("format")
]

AprilTagField = Union[
    AprilTagFieldRef,
    AprilTagFieldInline,
    AprilTagFieldNamedWpilib,
]
"Any AprilTag field data"

F = TypeVar('F', AprilTagFieldRefWpi, AprilTagFieldInlineWpi, AprilTagFieldInlineWpi, AprilTagFieldInlineSai)