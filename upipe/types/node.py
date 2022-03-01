from typing import List

from .base import UPipeEntity


class ResourceType:
    NODE = 'node'
    CPU = 'cpu'
    GPU = 'gpu'
    TPU = 'tpu'
    MEMORY = 'memory'
    NETWORK_IO = 'network_io'
    DISK_IO = 'disk_io'
    STANDARD_STORAGE = 'standard_storage'
    SSD_STORAGE = 'ssd_storage'


class APINodeResource(UPipeEntity):
    type: str  # ResourceType
    id: str
    name: str
    size: float = -1


class APINode(UPipeEntity):
    controller: bool
    controller_host: str = None
    controller_port: int = None
    resources: List[APINodeResource] = []
