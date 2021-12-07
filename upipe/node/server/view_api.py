from fastapi import APIRouter

from upipe import types
from upipe.node.server.node_controller import node

router = APIRouter(
    prefix="/view",
    tags=["pipe view"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/nodes")
async def read_nodes():
    return types.APIResponse(success=True, data=[node.api_def.dict()])


@router.get("/pipes")
async def read_pipes():
    return types.APIResponse(success=True, data=[node.pipe_controllers[controller].pipe for controller in node.pipe_controllers])