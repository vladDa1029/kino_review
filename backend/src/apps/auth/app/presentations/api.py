from dataclasses import asdict
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import UUID4


from app.presentations.dependens import UserUoWDep
from app.presentations.schemas import CreateUsers, ResponseUsers


router = APIRouter(tags=["auth"])


@router.post("/users")
async def create(user: CreateUsers, uow: UserUoWDep):
    try:
        entity = user.from_entities()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    async with uow as uow:
        await uow.users.add(entity)
        await uow.commit()
    return {"msg": "succesfull"}


@router.get("/users", response_model=List[ResponseUsers])
async def list(uow: UserUoWDep):
    async with uow as uow:
        entities = await uow.users.list()
        users_data = [asdict(entity) for entity in entities]
        response = [ResponseUsers.model_validate(user) for user in users_data]
    return response


@router.get("/users/{oid}")
async def get(oid: UUID4, uow: UserUoWDep):
    async with uow as uow:
        entities = await uow.users.get(oid)
        if not entities:
            raise HTTPException(status_code=404, detail="Page not found!")
        users_data = asdict(entities)
        response = ResponseUsers.model_validate(users_data)
    return response
