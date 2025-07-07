import uuid

from fastapi_users import schemas

from auth.db import UserLevel


class UserRead(schemas.BaseUser[uuid.UUID]):
    name: str
    level: UserLevel


class UserCreate(schemas.BaseUserCreate):
    name: str
    level: UserLevel = UserLevel.User


class UserUpdate(schemas.BaseUserUpdate):
    name: str
    level: UserLevel
