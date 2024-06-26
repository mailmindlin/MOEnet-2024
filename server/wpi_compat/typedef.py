from typing import Protocol, Union
from typing_extensions import Buffer

class SchemaRegistry(Protocol):
    "A schema registry (in practice, either NetworkTables or DataLog)"
    def hasSchema(self, typeString: str) -> bool: ...
    def addSchema(self, name: str, type: str, schema: Union[str, Buffer], timestamp: int = 0): ...