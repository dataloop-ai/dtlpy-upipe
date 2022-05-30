from enum import IntEnum

from pydantic import BaseModel

class UPipeEntityType(IntEnum):
    PROCESSOR = 1
    PROCESSOR_INSTANCE = 2
    PROCESS = 3
    PIPELINE = 4
    PIPELINE_CONTROLLER = 5
    SERVER = 6
    NODE = 7
    QUEUE = 8


class UPipeEntity(BaseModel):
    id: str
    name: str
    type: UPipeEntityType
    settings: dict = {}
    config: dict = {}

    class Config:
        arbitrary_types_allowed = True
