from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth.db import UserLevel
from auth.users import User
from models.designs import Design


async def get_design(id_: int, session: AsyncSession, user: User):
    if user.level == UserLevel.Admin:
        stmt = select(Design)
    else:
        stmt = select(Design).join(Design.members).where(User.id == user.id)

    design = await session.scalar(stmt.where(Design.design_id == id_,Design.is_deleted == False))

    if design:
        return design
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


async def get_design_counts(procedure_id: int, session: AsyncSession):
    stmt = select(func.count(Design.design_id)).where(Design.procedure_id == procedure_id)
    count = await session.scalar(stmt)

    return count
