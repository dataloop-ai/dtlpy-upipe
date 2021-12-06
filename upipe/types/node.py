from .base import UPipeEntity


class APINode(UPipeEntity):
    controller: bool
    controller_host: str = None
    controller_port: int = None
