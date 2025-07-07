import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Request, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth.users import ActiveUserDep
from crud.design import get_design
from database.connection import DBSessionDep
from models.designs import DesignTask, DesignDocument
from models.hoq import HoqATV, HoqAHP, HoqECHC, HoqHOQ
from models.procedures import Task, OutputType
from schemas.designs import DesignDocumentUpdate
from schemas.hoq import ATVUpdate, ECHCUpdate


editor_router = APIRouter()


async def get_task(task_id: str, output_type: OutputType, session: AsyncSession):
    stmt = select(Task).where(Task.task_id == task_id).where(Task.output_type == output_type)
    task = await session.scalar(stmt)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return task


async def update_task(design_id: int, task_id: uuid.UUID, session: AsyncSession):
    stmt = select(DesignTask).where(DesignTask.design_id == design_id).where(DesignTask.task_id == task_id)
    task = await session.scalar(stmt)

    if task:
        task.output_edited_at = datetime.now()
    else:
        task = DesignTask(design_id=design_id, task_id=task_id, output_edited_at=datetime.now())
        session.add(task)


@editor_router.put("/designs/{design_id}/tasks/{task_id}/markdown")
async def update_document(design_id: int, task_id: str, data: DesignDocumentUpdate,
                          session: DBSessionDep, user: ActiveUserDep):
    await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.MD, session)

    document = DesignDocument(design_id=design_id, task_id=task_id, document=data.document)
    session.add(document)

    await update_task(design_id, task.task_id, session)

    await session.commit()


@editor_router.put("/designs/{design_id}/tasks/{task_id}/atv")
async def update_atv(design_id: int, task_id: str, table: List[ATVUpdate], session: DBSessionDep, user: ActiveUserDep):
    await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.ATV, session)

    stmt = select(HoqATV.atv_id).where(HoqATV.design_id == design_id)
    result = await session.scalars(stmt)
    old_ids = set(result.all())

    current_ids = set()
    for data in table:
        if data.atv_id:
            stmt = select(HoqATV).where(HoqATV.atv_id == data.atv_id)
            atv = await session.scalar(stmt)
            atv.requirement = data.requirement
            atv.note = data.note
            atv.atv_order = data.atv_order

            current_ids.add(data.atv_id)
        else:
            atv = HoqATV(requirement=data.requirement, note=data.note, atv_order=data.atv_order, design_id=design_id)
            session.add(atv)

    stmt = delete(HoqATV).where(HoqATV.atv_id.in_(old_ids - current_ids))
    await session.execute(stmt)

    await update_task(design_id, task.task_id, session)

    await session.commit()


@editor_router.put("/designs/{design_id}/tasks/{task_id}/ahp")
async def update_ahp(design_id: int, task_id: str, info: List[List], session: DBSessionDep, user: ActiveUserDep):
    await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.AHP, session)

    for row in info:
        atv_id = row[0]
        stmt = delete(HoqAHP).where(HoqAHP.precedent_atv_id == atv_id)
        await session.execute(stmt)

        for i in range(1, len(row)):
            session.add(HoqAHP(precedent_atv_id=atv_id, consequent_atv_id=info[i -1][0], value=row[i]))

    await update_task(design_id, task.task_id, session)

    await session.commit()


@editor_router.put("/designs/{design_id}/tasks/{task_id}/echc")
async def update_echc(design_id: int, task_id: str, info: List[ECHCUpdate], session: DBSessionDep, user: ActiveUserDep):
    await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.ECHC, session)

    stmt = select(HoqECHC.echc_id).where(HoqECHC.design_id == design_id)
    result = await session.scalars(stmt)
    old_ids = set(result.all())

    current_ids = set()
    for data in info:
        if data.echc_order == 0:
            stmt = delete(HoqECHC).where(HoqECHC.echc_id == data.echc_id)
            await session.execute(stmt)
        elif data.echc_id:
            stmt = select(HoqECHC).where(HoqECHC.echc_id == data.echc_id)
            echc = await session.scalar(stmt)
            echc.direction = data.direction
            echc.characteristic = data.characteristic
            echc.note = data.note
            echc.echc_order = data.echc_order

            current_ids.add(data.echc_id)
        else:
            echc = HoqECHC(direction=data.direction,
                          characteristic=data.characteristic,
                          note=data.note,
                          echc_order=data.echc_order,
                          design_id=design_id)
            session.add(echc)

    stmt = delete(HoqECHC).where(HoqECHC.echc_id.in_(old_ids - current_ids))
    await session.execute(stmt)

    await update_task(design_id, task.task_id, session)

    await session.commit()


@editor_router.put("/designs/{design_id}/tasks/{task_id}/hoq")
async def update_hoq(design_id: int, task_id: str, info: List[List], request: Request, session: DBSessionDep, user: ActiveUserDep):
    await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.HOQ, session)

    atv_points = info[0]
    echc_values = info[1]

    for row in atv_points:
        atv_id = row[0]
        stmt = delete(HoqHOQ).where(HoqHOQ.atv_id == atv_id)
        await session.execute(stmt)

        for i in range(1, len(row)):
            hoq = HoqHOQ(atv_id=atv_id, echc_id=echc_values[i - 1][0], value=row[i])
            session.add(hoq)

    for row in echc_values:
        stmt = select(HoqECHC).where(HoqECHC.echc_id==row[0])
        echc = await session.scalar(stmt)

        echc.market_value = row[1]
        echc.target_value = row[2]

    await update_task(design_id, task.task_id, session)

    await session.commit()
