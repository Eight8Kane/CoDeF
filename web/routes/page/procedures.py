from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import subqueryload

from app.templates import templates
from crud.design import get_design_counts
from crud.procedure import get_procedure, get_task_counts, get_procedure_info
from crud.procedure import EditingProcedureIdDep, CurrentProcedureIdDep
from database.connection import DBSessionDep
from models.procedures import Procedure, Category, Step, Task, ProcedureStatus
from routes.render import BreadcrumbsItem

procedures_page_router = APIRouter()


def edit_page_breadcrumbs():
    return [BreadcrumbsItem('Admin'), BreadcrumbsItem('Design Procedure')]


def generate_breadcrumbs(*args):
    return [BreadcrumbsItem('Admin'), BreadcrumbsItem('Design Procedure', '/admin/procedures/0'), *args]


@procedures_page_router.get("/procedures", response_class=HTMLResponse)
async def procedure_list(request: Request, session: DBSessionDep, procedure_id: CurrentProcedureIdDep):
    stmt = (select(Procedure)
            .where(~Procedure.status.in_([ProcedureStatus.Editing, ProcedureStatus.Deleted]))
            .order_by(Procedure.created_at.desc()))
    procedures = await session.scalars(stmt)

    current_version_designs = await get_design_counts(procedure_id, session)

    context = {
        'request': request,
        'breadcrumbs': generate_breadcrumbs(BreadcrumbsItem('History')),
        'procedures': procedures.all(),
        'deletable': current_version_designs == 0
    }

    return templates.TemplateResponse('procedures/procedure_list.html', context)


@procedures_page_router.get("/procedures/{id_}", response_class=HTMLResponse)
async def procedure_edit(id_: int, request: Request,
                         session: DBSessionDep, current_procedure_id: EditingProcedureIdDep):
    procedure_id = current_procedure_id if id_ == 0 else id_

    context = {
        'request': request,
        'breadcrumbs': edit_page_breadcrumbs(),
        'procedure_info': await get_procedure_info(session, procedure_id),
        'procedure': await get_procedure(session, procedure_id),
        'editable': procedure_id == current_procedure_id,
    }

    return templates.TemplateResponse('procedures/procedure_edit.html', context)


@procedures_page_router.get("/category_edit/{id_}", response_class=HTMLResponse)
async def category_edit(id_: str, request: Request, session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    stmt = select(Category).where(Category.category_id == id_)
    category = await session.scalar(stmt)

    context = {
        'request': request,
        'breadcrumbs': edit_page_breadcrumbs(),
        'procedure_info': await get_procedure_info(session, procedure_id),
        'procedure': await get_procedure(session, category.procedure_id),
        'current_category': category,
        'editable': category.procedure_id == procedure_id
    }

    return templates.TemplateResponse('procedures/procedure_edit.html', context)


@procedures_page_router.get("/step_edit/{id_}", response_class=HTMLResponse)
async def step_edit(id_: str, request: Request, session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    stmt = (select(Step).where(Step.step_id == id_)
            .options(subqueryload(Step.tasks)).options(subqueryload(Step.category)))
    step = await session.scalar(stmt)

    context = {
        'request': request,
        'breadcrumbs': edit_page_breadcrumbs(),
        'procedure_info': await get_procedure_info(session, procedure_id),
        'procedure': await get_procedure(session, step.category.procedure_id),
        'current_step': step,
        'editable': step.category.procedure_id == procedure_id
    }

    return templates.TemplateResponse('procedures/procedure_edit.html', context)


@procedures_page_router.get("/task_edit/{id_}", response_class=HTMLResponse)
async def task_edit(id_: str, request: Request, session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    stmt = (select(Task).where(Task.task_id == id_)
            .options(subqueryload(Task.leaders).subqueryload(Task.step).subqueryload(Step.category))
            .options(subqueryload(Task.step).subqueryload(Step.category)))
    task = await session.scalar(stmt)

    context = {
        'request': request,
        'breadcrumbs': edit_page_breadcrumbs(),
        'procedure_info': await get_procedure_info(session, task.step.category.procedure_id),
        'procedure': await get_procedure(session, task.step.category.procedure_id),
        'current_task': task,
        'editable': task.step.category.procedure_id == procedure_id
    }

    return templates.TemplateResponse('procedures/procedure_edit.html', context)


@procedures_page_router.get("/dependency_selector", response_class=HTMLResponse)
async def dependency_selector(trailing_task_id: str, request: Request,
                              session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    stmt = select(Task).where(Task.task_id == trailing_task_id)
    task = await session.scalar(stmt)

    procedure = await get_procedure(session, procedure_id)

    context = {
        'request': request,
        'procedure': procedure,
        'task_counts': get_task_counts(procedure),
        'task_id': trailing_task_id,
        'trailing_task': task
    }

    return templates.TemplateResponse('procedures/dependency_modal.html', context)
