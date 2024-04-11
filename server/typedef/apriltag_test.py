from unittest import TestCase
from . import apriltag
from pathlib import Path

class TestNamedField(TestCase):
    def test_2024(self):
        field = apriltag.AprilTagFieldNamedWpilib.FRC_2024
        # Convert to local data
        field.load()
    
    def test_load_vs_ref(self):
        file_wpi = apriltag.AprilTagFieldRefWpi(
            path=Path('apriltag/2024-crescendo.json'),
            tagFamily=apriltag.AprilTagFamily.TAG_36H11,
            tagSize=0.1651,
        )
        field_wpi = file_wpi.load(Path(__file__).parent / '../config')
        ref_wpi = apriltag.AprilTagFieldNamedWpilib.FRC_2024.load()
        self.assertAlmostEqual(field_wpi.field.width, ref_wpi.field.width)
        self.assertAlmostEqual(field_wpi.field.length, ref_wpi.field.length)
        self.assertEqual(field_wpi.field, ref_wpi.field)
        self.assertAlmostEqual(field_wpi.tagSize, ref_wpi.tagSize)
        self.assertEqual(field_wpi.tagFamily, ref_wpi.tagFamily)

        tags1 = sorted(field_wpi.tags, key=lambda tag: tag.ID)
        tags2 = sorted(ref_wpi.tags, key=lambda tag: tag.ID)
        for i, (t1, t2) in enumerate(zip(tags1, tags2)):
            self.assertEqual(t1, t2, f"Tag {i}")
        
        self.assertEqual(field_wpi, ref_wpi)
    def test_conversion_roundtrip(self):
        file_wpi = apriltag.AprilTagFieldRefWpi(
            path=Path('apriltag/2024-crescendo.json'),
            tagFamily=apriltag.AprilTagFamily.TAG_36H11,
            tagSize=0.1651,
        )
        wpi = file_wpi.load(Path(__file__).parent / '../config')
        wpi1 = file_wpi.load(Path(__file__).parent / '../config')

        self.assertEqual(wpi, wpi1)

        sai = wpi1.as_inline_sai()
        wpi2 = sai.as_inline_wpi()
        self.assertEqual(wpi, wpi2)

    def test_conversion(self):
        file_wpi = apriltag.AprilTagFieldRefWpi(
            path=Path('apriltag/2024-crescendo.json'),
            tagFamily=apriltag.AprilTagFamily.TAG_36H11,
            tagSize=0.1651,
        )
        wpi = file_wpi.load(Path(__file__).parent / '../config')

        file_sai = apriltag.AprilTagFieldRefSai(
            path=Path('apriltag/2024-crescendo-sai.json'),
            field=wpi.field,
        )
        sai = file_sai.load(Path(__file__).parent / '../config')
        cvt_wpi = sai.as_inline_wpi()
        
        self.assertAlmostEqual(wpi.field.width, cvt_wpi.field.width)
        self.assertAlmostEqual(wpi.field.length, cvt_wpi.field.length)
        self.assertEqual(wpi.field, cvt_wpi.field)
        self.assertAlmostEqual(wpi.tagSize, cvt_wpi.tagSize)
        self.assertEqual(wpi.tagFamily, cvt_wpi.tagFamily)

        tags1 = sorted(wpi.tags, key=lambda tag: tag.ID)
        tags2 = sorted(cvt_wpi.tags, key=lambda tag: tag.ID)
        for i, (t1, t2) in enumerate(zip(tags1, tags2)):
            self.assertEqual(t1.ID, t2.ID, f"Tag {i}")
            self.assertEqual(t1.pose.translation(), t2.pose.translation(), f"Tag {i}")
            self.assertEqual(t1.pose.rotation(), t2.pose.rotation(), f"Tag {i}")
            self.assertEqual(t1.pose, t2.pose, f"Tag {i}")
            self.assertEqual(t1, t2, f"Tag {i}")
        
        self.assertEqual(wpi, cvt_wpi)