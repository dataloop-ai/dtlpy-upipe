from typing import List

from pydantic import BaseModel
from pydantic.class_validators import Optional
from .base import PipeEntityType, APIPipeEntity

from .pipe import APIPipe
from .node import APINode
from .processor import APIProcess, APIProcessor, APIProcessorInstance


# this is a mock object, for nested type conversion
class UpipeEntities(BaseModel):
    node: APINode
    pipe: APIPipe
    processors: List[APIProcessor]
    processors_instances: List[APIProcessorInstance]
    processes: List[APIProcess]
