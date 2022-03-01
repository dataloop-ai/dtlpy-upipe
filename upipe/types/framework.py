from typing import List

from pydantic import BaseModel

from . import NodePerformanceStats, APINodeUsageMessage
from .base import UPipeEntityType
from .performance import QueuePerformanceStats

from .pipe import APIPipe, APIPipeControlMessage, APIPipeStatusMessage
from .node import APINode
from .processor import APIProcessor
from .processor_instance import APIProcessorInstance, APIProcess
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
    node_stats: NodePerformanceStats
    node_stats_message: APINodeUsageMessage
    queue_stats: QueuePerformanceStats

