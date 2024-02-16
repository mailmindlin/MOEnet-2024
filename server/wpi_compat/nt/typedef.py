"""
Useful protocols for dealing with NetworkTables types in a generic way
"""
from typing import Protocol, TypeVar, Any, overload
from ntcore import PubSubOptions

P = TypeVar("P", bool, int, float, str, list[bool], list[int], list[float], list[str])

class GenericPublisher(Protocol[P]):
	"Interface for NetworkTables' XXXPublisher"
	def close(self) -> None: ...
	# def getTopic(self) -> 'ProtoTopic[P]': ...
	def set(self, value: P, time: int = 0) -> None: ...
	def setDefault(self, value: P) -> None: ...

class GenericTsValue(Protocol[P]):
	"Interface for NetworkTables' TimeStampedXXX"
	@overload
	def __init__(self) -> None: ...
	@overload
	def __init__(self, time: int, serverTime: int, value: P) -> None: ...
	def __repr__(self) -> str: ...
	@property
	def serverTime(self) -> int: ...
	@serverTime.setter
	def serverTime(self, arg0: int) -> None: ...
	@property
	def time(self) -> int: ...
	@time.setter
	def time(self, arg0: int) -> None: ...
	@property
	def value(self) -> P: ...
	@value.setter
	def value(self, arg0: P) -> None: ...

class GenericSubscriber(Protocol[P]):
	"Interface for NetworkTables' XXXSubscriber"
	def __enter__(self) -> 'GenericSubscriber[P]': ...
	def __exit__(self, *args) -> None: ...
	def close(self) -> None: ...
	@overload
	def get(self) -> P: ...
	@overload
	def get(self, defaultValue: P) -> P: ...
	@overload
	def getAtomic(self) -> GenericTsValue[P]: ...
	@overload
	def getAtomic(self, defaultValue: P) -> GenericTsValue[P]: ...
	# def getTopic(self) -> 'ProtoTopic[P]': ...
	def readQueue(self) -> list[Any]: ...

class GenericEntry(GenericSubscriber[P], GenericPublisher[P], Protocol[P]):
	# def __enter__(self) -> 'ProtoEntry[P]': ...
	# def __exit__(self, *args) -> None: ...
	# def close(self) -> None: ...
	# def getTopic(self) -> 'ProtoTopic[P]': ... 
	# def unpublish(self) -> None: ...
	...

class GenericTopic(Protocol[P]):
	def close(self) -> None:
		...
	def getEntry(self, defaultValue: P, options: PubSubOptions = ...) -> GenericEntry[P]: 
		...
	def getEntryEx(self, typeString: str, defaultValue: P, options: PubSubOptions = ...) -> GenericEntry[P]: 
		...
	def publish(self, options: PubSubOptions = ...) -> GenericPublisher[P]: 
		...
	# def publishEx(self, typeString: str, properties: json, options: PubSubOptions = ...) -> ProtoPublisher[P]: 
	# 	...
	def subscribe(self, defaultValue: P, options: PubSubOptions = ...) -> GenericSubscriber[P]: 
		...
	def subscribeEx(self, typeString: str, defaultValue: P, options: PubSubOptions = ...) -> GenericSubscriber[P]: 
		...
	
	def getName(self) -> str: ...