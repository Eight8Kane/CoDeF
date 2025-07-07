from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import joinedload

from app.templates import templates
from database.connection import DBSessionDep
from models.designs import Comment
from routes.render import BreadcrumbsItem


comment_router = APIRouter()


def generate_breadcrumbs(*args):
    return [BreadcrumbsItem('Admin'), *args]


@comment_router.get("/admin/comments", response_class=HTMLResponse)
async def comment_list(request: Request):
    context = {
        'breadcrumbs': generate_breadcrumbs(BreadcrumbsItem('Q&A')),
        'request': request,
    }

    return templates.TemplateResponse('admin/comment_list.html', context)


@comment_router.get("/api/comments")
async def get_comments(request: Request, session: DBSessionDep):
    base_filter = and_(Comment.is_deleted == False,
                       Comment.design.has(is_deleted=False),
                       or_(Comment.to_admin == True, Comment.parent.has(Comment.to_admin == True)))

    params = dict(request.query_params)
    search_value = f"%{params['search[value]']}%"

    stmt = select(func.count()).select_from(Comment).where(base_filter)
    total_records = await session.scalar(stmt)

    stmt = select(func.count()).select_from(Comment).where(base_filter).where(Comment.content.like(search_value))
    filtered_records = await session.scalar(stmt)

    stmt = (select(Comment).where(base_filter).where(Comment.content.like(search_value))
            .options(joinedload(Comment.writer)).order_by(desc(Comment.created_at))
            .offset(params['start']).limit(params['length']))
    comments = await session.scalars(stmt)

    return {
        'draw': params['draw'],
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': comments.all()
    }
