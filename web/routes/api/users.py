from fastapi import APIRouter, Request
from sqlalchemy import select, func, or_, desc

from auth.schemas import UserUpdate
from auth.users import User
from database.connection import DBSessionDep

user_router = APIRouter()


@user_router.get("/users")
async def get_users(request: Request, session: DBSessionDep):
    params = dict(request.query_params)
    search_value = f"%{params['search[value]'].strip()}%"
    filter = or_(User.email.ilike(search_value), User.name.like(search_value))

    stmt = select(func.count()).select_from(User)
    total_records = await session.scalar(stmt)

    stmt = stmt.where(filter)
    filtered_records = await session.scalar(stmt)

    stmt = select(User).where(filter).offset(params['start']).limit(params['length'])
    column_name = params.get('order[0][name]')
    if column_name:
        column = getattr(User, column_name)
        stmt = stmt.order_by(desc(column) if params['order[0][dir]'] == 'desc' else column)
    users = await session.scalars(stmt)

    return {
        'draw': params['draw'],
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': users.all()
    }


@user_router.put("/users/{id_}")
async def update_users(id_: str, data: UserUpdate, session: DBSessionDep):
    stmt = select(User).where(User.id == id_)
    user = await session.scalar(stmt)

    user.name = data.name
    user.level = data.level
    await session.commit()
