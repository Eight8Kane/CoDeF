from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.templates import templates
from auth.users import User
from database.connection import DBSessionDep
from routes.render import BreadcrumbsItem


user_page_router = APIRouter()


def generate_breadcrumbs(*args):
    return [BreadcrumbsItem('Admin'), *args]


@user_page_router.get("/users", response_class=HTMLResponse)
async def user_list(request: Request):
    context = {
        'breadcrumbs': generate_breadcrumbs(BreadcrumbsItem('Users')),
        'request': request,
    }

    return templates.TemplateResponse('users/user_list.html', context)


@user_page_router.get("/users/{id_}", response_class=HTMLResponse)
async def user_edit(id_: str, request: Request, session: DBSessionDep):
    stmt = select(User).where(User.id == id_)
    user = await session.scalar(stmt)

    context = {
        'request': request,
        'breadcrumbs': generate_breadcrumbs(BreadcrumbsItem('Users', '/admin/users'), BreadcrumbsItem('Edit')),
        'user': user
    }

    return templates.TemplateResponse('users/user_edit.html', context)
