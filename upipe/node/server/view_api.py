from fastapi import APIRouter

router = APIRouter(
    prefix="/view",
    tags=["pipe view"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/nodes")
async def read_nodes():
    return [{"username": "Rick"}, {"username": "Morty"}]
