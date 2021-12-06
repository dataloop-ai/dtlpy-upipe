import pydantic
from pydantic import typing
from pydantic.class_validators import Optional
from pydantic.fields import List

from .messages import UPipeMessage


class APIResponse(pydantic.BaseModel):
    success: bool
    code: Optional[str]
    messages: List[UPipeMessage] = list()
    data: Optional[typing.Any]
    text: Optional[str]
