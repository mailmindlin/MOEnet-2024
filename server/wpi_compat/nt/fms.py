from ntcore import NetworkTableInstance
from wpilib import DriverStation
from enum import IntFlag, Enum, auto, IntEnum
from dataclasses import dataclass

class ControlWord(IntFlag):
	ROBOT_ENABLED = 0x01
	MODE_AUTO = 0x02
	MODE_TEST = 0x04
	ESTOP = 0x08
	FMS_ATTACHED = 0x10
	DS_ATTACHED = 0x20

@dataclass(eq=True, frozen=True)
class MatchInfo:
   eventName: str = ""
   gameSpecificMessage: str = ""
   matchNumber: int = 0
   replayNumber: int = 0
   matchType: DriverStation.MatchType

class RobotMode(Enum):
   AUTO = auto()
   TELEOP = auto()
   TEST = auto()

@dataclass
class RobotState:
   mode: RobotMode

@dataclass
class FMSData:
	match: MatchInfo | None = None
	alliance: DriverStation.Alliance | None = None
	allianceStation: int | None = None

	fmsAttached: bool = False
	dsAttached: bool = False
	estop: bool | None = None
	robotEnabled: bool | None = None
	modeTest: bool | None = None
	modeAuto: bool | None = None


class FMSInfo:
	def __init__(self, nt: NetworkTableInstance):
		path = "/FMSInfo"
		root = nt.getTable(path)
		# Event stuff
		self._sub_gameSpecificMessage = root.getStringTopic("GameSpecificMessage").subscribe("")
		self._sub_eventName = root.getStringTopic("EventName").subscribe("")
		self._sub_matchNumber = root.getIntegerTopic("MatchNumber").subscribe(0)
		self._sub_replayNumber = root.getIntegerTopic("ReplayNumber").subscribe(0)
		self._sub_matchType = root.getIntegerTopic("MatchType").subscribe(0)

		# Alliance stuff
		self._sub_alliance = root.getBooleanTopic("IsRedAlliance").subscribe(False)
		self._sub_station = root.getIntegerTopic("StationNumber").subscribe(0)

		# Robot state
		self._sub_controlWord = root.getIntegerTopic("FMSControlData").subscribe(0)

		self.current = FMSData()
		self.cached = FMSData()

	def fetch(self):
		data = FMSData()

		if self._sub_alliance.exists():
			data.alliance = self.current.alliance
			for m in self._sub_alliance.readQueue():
				# True if red
				if m.value:
					data.alliance = DriverStation.Alliance.kRed
				else:
					data.alliance = DriverStation.Alliance.kBlue
		if self._sub_station.exists():
			data.allianceStation = self.current.allianceStation
			for m in self._sub_station.readQueue():
				data.allianceStation = m.value
		if self._sub_controlWord.exists():
			data.robotEnabled = self.current.robotEnabled
			data.modeAuto = self.current.modeAuto
			data.modeTest = self.current.modeTest
			data.estop = self.current.estop
			data.fmsAttached = self.current.fmsAttached
			data.dsAttached = self.current.dsAttached
			for m in self._sub_controlWord.exists():
				cw = ControlWord(m)
				data.robotEnabled = ControlWord.ROBOT_ENABLED in cw
				data.modeAuto     = ControlWord.MODE_AUTO in cw
				data.modeTest     = ControlWord.MODE_TEST in cw
				data.estop        = ControlWord.ESTOP in cw
				data.fmsAttached  = ControlWord.FMS_ATTACHED in cw
				data.dsAttached   = ControlWord.DS_ATTACHED in cw
		else:
			data.fmsAttached = False
		
		return data