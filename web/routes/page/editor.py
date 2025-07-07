from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import subqueryload

from app.templates import templates
from auth.users import ActiveUserDep
from crud.design import get_design
from crud.procedure import CurrentProcedureIdDep, step_number
from database.connection import DBSessionDep
from models.designs import Design, DesignDocument
from models.hoq import HoqATV, HoqAHP, HoqECHC, HoqHOQ
from models.procedures import Step, Task, OutputType
from routes.render import BreadcrumbsItem


editor_page_router = APIRouter()


def generate_design_breadcrumb(design: Design, task: Task, closed):
    breadcrubms = [BreadcrumbsItem('Design', '/designs'),
                   BreadcrumbsItem(design.name, f'/designs/{design.design_id}/summary')]

    if not closed:
        breadcrubms.append(
            BreadcrumbsItem(f'{step_number(task.step)}. {task.step.title}', f'/designs/{design.design_id}/steps/{task.step_id}'))

    if task:
        breadcrubms.append(BreadcrumbsItem(f'[{task.output_code}] {task.output_name}'))

    return breadcrubms


async def get_task(task_id: str, output_type: OutputType, session: AsyncSession):
    stmt = (select(Task).where(Task.task_id == task_id).where(Task.output_type == output_type)
            .options(subqueryload(Task.step).subqueryload(Step.category)))
    task = await session.scalar(stmt)

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return task


@editor_page_router.get("/designs/{design_id}/tasks/{task_id}/markdown", response_class=HTMLResponse)
async def markdown_document(design_id: int, task_id: str, request: Request,
                  session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.MD, session)

    stmt = (select(DesignDocument)
            .where(DesignDocument.design_id == design_id).where(DesignDocument.task_id == task_id)
            .order_by(DesignDocument.created_at.desc()).limit(1))
    document = await session.scalar(stmt)

    closed = design.procedure_id != procedure_id

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, task, closed),
        'design': design,
        'task': task,
        'document': document.document if document else task.template_markdown,
        'closed': closed
    }

    return templates.TemplateResponse('editor/markdown.html', context)


@editor_page_router.get("/tasks/{task_id}/markdown_example", response_class=HTMLResponse)
async def markdown_example(task_id: str, request: Request, session: DBSessionDep):
    task = await get_task(task_id, OutputType.MD, session)

    context = {
        'request': request,
        'task': task,
    }

    return templates.TemplateResponse('editor/markdown_example.html', context)


@editor_page_router.get("/tasks/{task_id}/markdown_template", response_class=HTMLResponse)
async def markdown_example(task_id: str, request: Request, session: DBSessionDep):
    task = await get_task(task_id, OutputType.MD, session)

    context = {
        'request': request,
        'task': task,
    }

    return templates.TemplateResponse('editor/markdown_template.html', context)


@editor_page_router.get("/designs/{design_id}/tasks/{task_id}/atv", response_class=HTMLResponse)
async def atv_edit(design_id: int, task_id: str, request: Request,
                  session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.ATV, session)

    stmt = select(HoqATV).where(HoqATV.design_id == design_id).order_by(HoqATV.atv_order)
    data = await session.scalars(stmt)

    closed = design.procedure_id != procedure_id

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, task, closed),
        'design': design,
        'task': task,
        'atv_data': data.all(),
        'closed': closed
    }

    return templates.TemplateResponse('editor/atv.html', context)


@editor_page_router.get("/designs/{design_id}/tasks/{task_id}/ahp", response_class=HTMLResponse)
async def ahp_edit(design_id: int, task_id: str, request: Request,
                  session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.AHP, session)

    stmt = (select(HoqATV).where(HoqATV.design_id == design_id).order_by(HoqATV.atv_order)
            .options(subqueryload(HoqATV.ahp_values).subqueryload(HoqAHP.consequent)))
    data = await session.scalars(stmt)
    ahp_data = data.all()

    closed = design.procedure_id != procedure_id

    if not ahp_data:
        context = {
            'request': request,
            'breadcrumbs': generate_design_breadcrumb(design, task, closed),
            'design': design,
            'step_id': task.step_id,
            'title': 'Cannot Edit AHP',
            'message': 'You need to fill out ATV first.'
        }

        return templates.TemplateResponse('editor/error.html', context)

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, task, closed),
        'design': design,
        'task': task,
        'ahp_data': ahp_data,
        'closed': closed
    }

    return templates.TemplateResponse('editor/ahp.html', context)


@editor_page_router.get("/designs/{design_id}/tasks/{task_id}/echc", response_class=HTMLResponse)
async def echc_edit(design_id: int, task_id: str, request: Request,
                   session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.ECHC, session)

    stmt = select(HoqECHC).where(HoqECHC.design_id == design_id).order_by(HoqECHC.echc_order)
    data = await session.scalars(stmt)

    closed = design.procedure_id != procedure_id

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, task, closed),
        'design': design,
        'task': task,
        'echc_data': data.all(),
        'closed': closed
    }

    return templates.TemplateResponse('editor/echc.html', context)


@editor_page_router.get("/designs/{design_id}/tasks/{task_id}/hoq", response_class=HTMLResponse)
async def hoq_edit(design_id: int, task_id: str, request: Request,
                  session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = await get_design(design_id, session, user)
    task = await get_task(task_id, OutputType.HOQ, session)

    stmt = (select(HoqATV).where(HoqATV.design_id == design_id).order_by(HoqATV.atv_order)
            .options(subqueryload(HoqATV.ahp_values).subqueryload(HoqAHP.consequent))
            .options(subqueryload(HoqATV.hoq_values).subqueryload(HoqHOQ.echc)))
    data = await session.scalars(stmt)
    atv_data = data.all()

    stmt = select(HoqECHC).where(HoqECHC.design_id == design_id).order_by(HoqECHC.echc_order)
    data = await session.scalars(stmt)
    echc_data = data.all()

    totals = {atv.atv_id: 1 for atv in atv_data}
    ahp_values = {prcedent.atv_id : {consequent.atv_id: 1 if prcedent.atv_id == consequent.atv_id else 0
                                     for consequent in atv_data}
                  for prcedent in atv_data}

    ahp_updated = False
    for precedent in atv_data:
        if precedent.ahp_values:
            ahp_updated = True
            for value in precedent.ahp_values:
                v = float(value.value)
                s = 1 / v

                totals[value.consequent_atv_id] += v
                totals[value.precedent_atv_id] +=  s

                ahp_values[value.precedent_atv_id][value.consequent_atv_id] = v
                ahp_values[value.consequent_atv_id][value.precedent_atv_id] = s

    ahp_data = [(precedent, sum(ahp_values[precedent.atv_id][consequent.atv_id] / totals[consequent.atv_id]
                                for consequent in atv_data))
                for precedent in atv_data]

    closed = design.procedure_id != procedure_id

    if not ahp_updated or not echc_data:
        context = {
            'request': request,
            'breadcrumbs': generate_design_breadcrumb(design, task, closed),
            'design': design,
            'step_id': task.step_id,
            'title': 'Cannot Edit HOQ',
            'message': 'You need to fill out AHP and ECHC first.'
        }

        return templates.TemplateResponse('editor/error.html', context)

    context = {
        'request': request,
        'breadcrumbs': generate_design_breadcrumb(design, task, closed),
        'design': design,
        'task': task,
        'hoq_data': atv_data,
        'ahp_data': ahp_data,
        'echc_data': echc_data,
        'closed': closed
    }

    return templates.TemplateResponse('editor/hoq.html', context)


@editor_page_router.get("/editor/markdown/{design_id}", response_class=HTMLResponse)
async def hoq_hoq(design_id: int, request: Request,
                  session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = await get_design(design_id, session, user)
    closed = design.procedure_id != procedure_id

    context = {
        'request': request,
        'design': design,
        'closed': closed
    }

    return templates.TemplateResponse('editor/markdown.html', context)
