from .base import APIPipeEntity


class APINode(APIPipeEntity):
    controller: bool
    controller_host: str = None
    controller_port: int = None
    id: str
