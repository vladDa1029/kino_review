

from fastapi import APIRouter


router = APIRouter(tags =["auth"])


@router.get("/registry")
async def registry():
    pass
