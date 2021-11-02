from typing import List

from pydantic import BaseModel
from pydantic.class_validators import Optional
from .base import PipeEntityType, API_Pipe_Entity

from .pipe import API_Pipe
from .node import API_Node
from .processor import API_Process, API_Processor, API_Processor_Instance


# this is a mock object, for nested type conversion
class UpipeEntities(BaseModel):
    node: API_Node
    pipe: API_Pipe
    processors: List[API_Processor]
    processors_instances: List[API_Processor_Instance]
    processes: List[API_Process]
