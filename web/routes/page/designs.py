from datetime import datetime
from dataclasses import dataclass

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func, desc
from sqlalchemy.orm import subqueryload, aliased

from app.templates import templates
from auth.users import ActiveUserDep
from crud.design import get_design
from crud.procedure import get_procedure, get_task_counts, CurrentProcedureIdDep, step_number
from database.connection import DBSessionDep
from models.designs import Design, DesignTask, DesignFile, Comment, DesignMember
from models.procedures import Category, Task, Step
from routes.render import BreadcrumbsItem


design_page_router = APIRouter()


def generate_breadcrumbs(*args):
    return [BreadcrumbsItem('Design', '/designs'), *args]


def generate_design_breadcrumb(design: Design, *args):
    return generate_breadcrumbs(BreadcrumbsItem(design.name, f'/designs/{design.design_id}/summary'), *args)


@dataclass
class TaskData:
    is_completed: bool
    output_edited_at: datetime
    latest_file: DesignFile


@design_page_router.get("/", response_class=HTMLResponse)
async def main():
    return RedirectResponse(f'/designs', status_code=status.HTTP_303_SEE_OTHER)


@design_page_router.get("/designs", response_class=HTMLResponse)
async def design_list(request: Request, procedure_id: CurrentProcedureIdDep):
    context = {
        'request': request,
        'breadcrumbs': generate_breadcrumbs(BreadcrumbsItem('My Designs')),
        'procedure_id': procedure_id
    }

    return templates.TemplateResponse('designs/design_list.html', context)


@design_page_router.get("/designs/new", response_class=HTMLResponse)
async def design_new(request: Request):
    context = {
        'breadcrumbs': generate_breadcrumbs(BreadcrumbsItem('New')),
        'request': request,
    }

    return templates.TemplateResponse('designs/design_new.html', context)


@design_page_router.get("/designs/{id_}/summary", response_class=HTMLResponse)
async def design_summary(id_: int, request: Request,
                         session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = await get_design(id_, session, user)
    procedure = await get_procedure(session, design.procedure_id)

    design_file_query = (
        select(
            DesignFile,
            func.rank().over(partition_by=DesignFile.task_id, order_by=desc(DesignFile.created_at)).label("order"))
        .where(DesignFile.design_id == design.design_id, DesignFile.is_deleted == False)).subquery()
    design_file = aliased(design_file_query)

    stmt = (select(Task, DesignTask.is_completed, DesignTask.output_edited_at, DesignFile)
            .join(DesignTask, (DesignTask.task_id == Task.task_id) & (DesignTask.design_id == design.design_id), isouter=True)
            .join(design_file, (design_file.c.task_id == Task.task_id) & (design_file.c.order == 1), isouter=True)
            .join(DesignFile, DesignFile.design_file_id == design_file.c.design_file_id, isouter=True)
            .join(Step, Step.step_id == Task.step_id)
            .join(Category, Category.category_id == Step.category_id)
            .where(Category.procedure_id == design.procedure_id)
            .options(subqueryload(Task.leaders)))
    tasks = await session.execute(stmt)

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, BreadcrumbsItem('Summary')),
        'design': design,
        'procedure': procedure,
        'task_counts': get_task_counts(procedure),
        'tasks': {task.task_id: TaskData(is_completed, output_edited_at, design_file)
                  for task, is_completed, output_edited_at, design_file in tasks.all()},
        'closed': design.procedure_id != procedure_id
    }

    return templates.TemplateResponse('designs/design_summary.html', context)


@design_page_router.get("/designs/{id_}/steps/{step_id}", response_class=HTMLResponse)
async def design_step(id_: int, step_id: str, request: Request, session: DBSessionDep, user: ActiveUserDep):
    design = await get_design(id_, session, user)

    stmt = select(Step).where(Step.step_id == step_id).options(subqueryload(Step.category))
    step = await session.scalar(stmt)

    design_file_query = (
        select(
            DesignFile,
            func.rank().over(partition_by=DesignFile.task_id, order_by=desc(DesignFile.created_at)).label("order"))
        .where(DesignFile.design_id == design.design_id, DesignFile.is_deleted == False)).subquery()
    design_file = aliased(design_file_query)

    stmt = (select(Task, DesignTask, DesignFile)
            .join(DesignTask, (DesignTask.design_id == id_) & (DesignTask.task_id == Task.task_id), isouter=True)
            .join(design_file, (design_file.c.task_id == Task.task_id) & (design_file.c.order == 1), isouter=True)
            .join(DesignFile, (DesignFile.design_file_id == design_file.c.design_file_id), isouter=True)
            .where(Task.step_id == step_id)
            .options(subqueryload(Task.leaders).options(subqueryload(Task.step).subqueryload(Step.category)))
            .options(subqueryload(Task.step)))
    tasks = await session.execute(stmt)

    stmt = (select(Comment)
            .where(Comment.design_id == id_).where(Comment.step_id == step_id).where(Comment.parent_id == None)
            .order_by(Comment.created_at)
            .options(subqueryload(Comment.replies).options(subqueryload(Comment.writer)))
            .options(subqueryload(Comment.writer)))
    comments = await session.scalars(stmt)

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, BreadcrumbsItem(f'{step_number(step)}. {step.title}')),
        'design': design,
        'procedure': await get_procedure(session, design.procedure_id),
        'step': step,
        'tasks': tasks.all(),
        'comments': comments.all(),
        'files': {},
        'schemas': {'comment': Comment(), 'reply': Comment(parent_id=0)}
    }

    return templates.TemplateResponse('designs/design_step.html', context)


@design_page_router.get("/designs/{id_}/members", response_class=HTMLResponse)
async def members_list(id_: int, request: Request, session: DBSessionDep, user: ActiveUserDep):
    design = await get_design(id_, session, user)

    stmt = select(DesignMember).where(DesignMember.design_id == id_).options(subqueryload(DesignMember.user))
    members = await session.scalars(stmt)

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, BreadcrumbsItem('Members')),
        'design': design,
        'members': members.all()
    }

    return templates.TemplateResponse('designs/design_members.html', context)


@design_page_router.get("/designs/{id_}/comments", response_class=HTMLResponse)
async def comments_list(id_: int, request: Request, session: DBSessionDep, user: ActiveUserDep):
    design = await get_design(id_, session, user)

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, BreadcrumbsItem('Comments')),
        'design': design,
    }

    return templates.TemplateResponse('designs/design_comments.html', context)
