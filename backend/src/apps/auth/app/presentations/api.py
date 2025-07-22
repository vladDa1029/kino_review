from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import UUID4

from app.adapters.repository import SqlAlchemyRepository
from app.infrastructure.database import SesDep
from app.presentations.schemas import CreateUsers, ResponseUsers


router = APIRouter(tags=["auth"])


@router.post("/users")
async def create(user: CreateUsers, session: SesDep):
    try:
        entity = user.from_entities()
        print(entity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await SqlAlchemyRepository(session).add(entity)
    return {"msg": "succesfull"}


@router.get("/users", response_model=List[ResponseUsers])
async def list(session: SesDep):
    entities = await SqlAlchemyRepository(session).list()
    return entities


@router.get("/users/{oid}", response_model=ResponseUsers)
async def get(oid: UUID4, session: SesDep):
    entities = await SqlAlchemyRepository(session).get(oid)
    if not entities:
        return HTTPException(status_code=404, detail="Page not found!")
    return entities
