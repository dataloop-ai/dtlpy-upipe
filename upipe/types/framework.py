from typing import List

from pydantic import BaseModel
from pydantic.class_validators import Optional
from .base import UPipeEntityType, UPipeEntity

from .pipe import APIPipe, APIPipeControlMessage, APIPipeStatusMessage
from .node import APINode
from .processor import APIProcess, APIProcessor, APIProcessorInstance
from .http_api import APIResponse


# this is a mock object, for nested type conversion
class UpipeEntities(BaseModel):
    node: APINode
    pipe: APIPipe
    processors: List[APIProcessor]
    processors_instances: List[APIProcessorInstance]
    processes: List[APIProcess]
    response: APIResponse
    entity_type: UPipeEntityType
    control_message: APIPipeControlMessage
    status_message: APIPipeStatusMessage
