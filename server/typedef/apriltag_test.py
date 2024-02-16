from typing import TypeVar
from unittest import TestCase
from . import apriltag
from pathlib import Path
from tempfile import TemporaryDirectory

T = TypeVar('T')

class TestNamedField(TestCase):
    def test_2024(self):
        field = apriltag.AprilTagFieldNamedWpilib.FRC_2024
        # Convert to local data
        field.load()