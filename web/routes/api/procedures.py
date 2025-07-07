import json
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, UploadFile, Form, HTTPException, status
from sqlalchemy import func, select, delete
from sqlalchemy.orm import subqueryload, joinedload
from starlette.responses import FileResponse

from app.file_system import TEMPLATES_PATH
from crud.design import get_design_counts
from crud.procedure import get_task_file_name, task_number, current_procedure_id, get_procedure_for_copy, copy_procedure
from crud.procedure import EditingProcedureIdDep, CurrentProcedureIdDep
from database.connection import DBSessionDep
from models.procedures import Category, Step, Task, Prerequisite, ProcedureStatus, OutputType
from schemas.procedures import ProcedureCreate, CategoryCreate, StepCreate, TaskCreate, TaskOrder
from schemas.procedures import CategoryUpdate, StepUpdate, TaskUpdate, CategoryOrder, StepOrder


procedure_router = APIRouter()


@procedure_router.post("/procedures")
async def create_procedure(data: ProcedureCreate, session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    def validate_dependency(leader, trailer):
        if leader.step.category.phase > trailer.step.category.phase:
            return False
        elif leader.step.category.phase == trailer.step.category.phase:
            if leader.step.category.category_order > trailer.step.category.category_order:
                return False
            elif leader.step.category.category_order == trailer.step.category.category_order:
                if leader.step.step_order > trailer.step.step_order:
                    return False
                elif leader.step.step_order == trailer.step.step_order and leader.task_order > trailer.task_order:
                    return False

        return True

    procedure = await get_procedure_for_copy(session, procedure_id)

    dependency_errors = []
    for category in procedure.categories:
        for step in category.steps:
            for task in step.tasks:
                for leader in task.leaders:
                    if not validate_dependency(leader, task):
                        dependency_errors.append(f'{task_number(task)} {task.title}')
                        break

    tool_errors = []
    hoq_tools = [OutputType.ATV, OutputType.AHP, OutputType.ECHC, OutputType.HOQ]
    prev_tool = None
    leader = None
    for tool in hoq_tools:
        stmt = (select(Task).options(joinedload(Task.step).joinedload(Step.category))
                .join(Step).join(Category)
                .where(Task.output_type == tool, Category.procedure_id == procedure_id))
        # stmt = (select(Task)
        #         .options(subqueryload(Task.step).subqueryload(Step.category), with_loader_criteria(Category, Category.procedure_id == procedure_id))
        #         .where(Task.editor_name == tool))
        result = await session.scalars(stmt)
        tasks = result.all()
        counts = len(tasks)

        if counts == 0:
            leader = None
            prev_tool = tool
        elif counts == 1:
            task = tasks[0]
            if prev_tool:
                if leader is None:
                    tool_errors.append(('DEP', tool, f'{task_number(task)} {task.title}', prev_tool, None))
                elif not validate_dependency(leader, task):
                    tool_errors.append(('DEP', tool, f'{task_number(task)} {task.title}',
                                        prev_tool, f'{task_number(leader)} {leader.title}'))
            leader = task
            prev_tool = tool
        else:
            tool_errors.append(('DUP', tool, [f'{task_number(t)} {t.title}' for t in tasks]))
            leader = None
            prev_tool = None

    if dependency_errors or tool_errors:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={'dependency_errors': dependency_errors, 'tool_errors': tool_errors})

    copy_procedure(session, procedure, data, ProcedureStatus.Published)
    await session.commit()


@procedure_router.delete("/procedures/{id_}")
async def delete_procedure(id_: int, session: DBSessionDep, procedure_id: CurrentProcedureIdDep):
    if id_ != procedure_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Cannot delete procedure that is not the current procedure.')

    if await get_design_counts(procedure_id, session) > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Cannot delete procedure on which designs are based.')

    procedure = await get_procedure_for_copy(session, procedure_id)
    procedure.status = ProcedureStatus.Deleted
    await session.flush()

    copy_procedure(session,
                   await get_procedure_for_copy(session, await current_procedure_id(session)),
                   ProcedureCreate(name="Editing", note=f'Delete v{procedure_id}'), ProcedureStatus.Editing)
    await session.commit()


@procedure_router.post("/categories")
async def create_category(data: CategoryCreate, session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    order = (select(func.count(Category.category_order) + 1)
             .where(Category.procedure_id == procedure_id).where(Category.phase == data.phase))

    category = Category(procedure_id=procedure_id,
                        title='' if data.is_step else data.title,
                        category_order=order,
                        phase=data.phase,
                        is_step=data.is_step)

    if data.is_step:
        category.steps.append(Step(title=data.title, step_order=1))

    session.add(category)
    await session.commit()
    await session.refresh(category, ['steps'])

    return category


@procedure_router.put("/categories/{id_}")
async def update_category(id_: str, data: CategoryUpdate, session: DBSessionDep):
    stmt = select(Category).where(Category.category_id == id_)
    category = await session.scalar(stmt)

    category.title = data.title

    await session.commit()
    await session.refresh(category)

    return category


@procedure_router.delete("/categories/{id_}")
async def delete_category(id_: str, session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    stmt = select(Category).where(Category.category_id == id_).options(subqueryload(Category.steps))
    result = await session.execute(stmt)
    category = result.scalar_one()

    if category.is_step and len(category.steps) == 1:
        await session.delete(category.steps[0])
    elif category.steps:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Cannot delete category which has steps')

    stmt = select(Category).where(Category.phase == category.phase).where(Category.procedure_id == procedure_id)
    categories = await session.scalars(stmt)

    await session.delete(category)
    for c in categories.all():
        if c.category_order > category.category_order:
            c.category_order = c.category_order - 1

    await session.commit()


@procedure_router.put("/categories/{id_}/order")
async def update_category_order(id_: str, data: CategoryOrder,
                                session: DBSessionDep, procedure_id: EditingProcedureIdDep):
    stmt = select(Category).where(Category.category_id == id_)
    category = await session.scalar(stmt)

    stmt = select(Category).where(Category.phase == category.phase).where(Category.procedure_id == procedure_id)
    if category.phase == data.phase and category.category_order > data.category_order:
        stmt = (stmt
                .where(Category.category_order < category.category_order)
                .where(Category.category_order >= data.category_order))
        categories = await session.scalars(stmt)

        for c in categories.all():
            c.category_order += 1
    else:
        stmt = stmt.where(Category.category_order >= category.category_order)
        if category.phase == data.phase:
            stmt = stmt.where(Category.category_order <= data.category_order)
        categories = await session.scalars(stmt)

        for c in categories.all():
            c.category_order -= 1

    if category.phase != data.phase:
        stmt = (select(Category)
                .where(Category.phase == data.phase)
                .where(Category.procedure_id == procedure_id)
                .where(Category.category_order >= data.category_order))
        categories = await session.scalars(stmt)

        for c in categories.all():
            c.category_order += 1

    category.phase = data.phase
    category.category_order = data.category_order

    await session.commit()


@procedure_router.post("/steps")
async def create_step(data: StepCreate, session: DBSessionDep):
    order = (select(func.count(Step.step_order) + 1).where(Step.category_id == data.category_id))

    step = Step(title=data.title, step_order=order, category_id=data.category_id)

    session.add(step)
    await session.commit()
    await session.refresh(step)

    return step


@procedure_router.put("/steps/{id_}")
async def update_step(id_: str, data: StepUpdate, session: DBSessionDep):
    stmt = select(Step).where(Step.step_id == id_)
    result = await session.execute(stmt)
    step = result.scalar_one()

    step.title = data.title
    step.guide = data.guide

    await session.commit()
    await session.refresh(step)

    return step


@procedure_router.delete("/steps/{id_}")
async def delete_step(id_: str, session: DBSessionDep):
    stmt = select(Step).where(Step.step_id == id_)
    result = await session.execute(stmt)
    step = result.scalar_one()
    await session.delete(step)

    stmt = select(Step).where(Step.category_id == step.category_id)
    steps = await session.scalars(stmt)
    for s in steps.all():
        if s.step_order > step.step_order:
            s.step_order = s.step_order - 1

    await session.commit()


@procedure_router.put("/steps/{id_}/order")
async def update_step_order(id_: str, data: StepOrder, session: DBSessionDep):
    stmt = select(Step).where(Step.step_id == id_)
    step = await session.scalar(stmt)

    stmt = select(Step).where(Step.category_id == step.category_id)
    if step.category_id == data.category_id and step.step_order > data.step_order:
        stmt = stmt.where(Step.step_order < step.step_order).where(Step.step_order >= data.step_order)
        steps = await session.scalars(stmt)

        for s in steps.all():
            s.step_order += 1
    else:
        stmt = stmt.where(Step.step_order >= step.step_order)
        if step.category_id == data.category_id:
            stmt = stmt.where(Step.step_order <= data.step_order)
        steps = await session.scalars(stmt)

        for s in steps.all():
            s.step_order -= 1

    if step.category_id != data.category_id:
        stmt = select(Step).where(Step.category_id == data.category_id).where(Step.step_order >= data.step_order)
        steps = await session.scalars(stmt)

        for s in steps.all():
            s.step_order += 1

    step.category_id = data.category_id
    step.step_order = data.step_order

    await session.commit()


@procedure_router.post("/tasks")
async def create_task(data: TaskCreate, session: DBSessionDep):
    order = (select(func.count(Task.task_order) + 1).where(Task.step_id == data.step_id))
    task = Task(title=data.title,
                task_order=order,
                step_id=data.step_id)

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return task


@procedure_router.put("/tasks/{id_}")
async def update_task(id_: str, info: Annotated[str, Form()], *, template: UploadFile = None, example: UploadFile = None,
                        session: DBSessionDep):
    stmt = select(Task).where(Task.task_id == id_)
    task = await session.scalar(stmt)

    data = TaskUpdate(**json.loads(info))

    task.title = data.title
    task.description = data.description.strip()
    task.output_code = data.output_code
    task.output_name = data.output_name
    task.output_type = None if data.output_type is None else OutputType[data.output_type]
    task.template_markdown = data.template_markdown
    task.example_markdown = data.example_markdown

    if data.output_code:
        now = datetime.now()
        if template:
            content = await template.read()
            task.template_file = f"{str(uuid4())}{Path(template.filename).suffix}"
            task.template_uploaded_at = now
            with open(TEMPLATES_PATH / task.template_file, 'wb') as f:
                f.write(content)

        if example:
            content = await example.read()
            task.example_file = f"{str(uuid4())}{Path(example.filename).suffix}"
            task.example_uploaded_at = now
            with open(TEMPLATES_PATH / task.example_file, 'wb') as f:
                f.write(content)
    else:
        task.template_file = None
        task.template_uploaded_at = None
        task.example_file = None
        task.example_uploaded_at = None

    stmt = delete(Prerequisite).where(Prerequisite.trailing_task_id == task.task_id)
    await session.execute(stmt)

    for leader_id in data.leading_task_ids:
        session.add(Prerequisite(leading_task_id=leader_id, trailing_task_id=task.task_id))

    await session.commit()
    await session.refresh(task)

    return task


@procedure_router.delete("/tasks/{id_}")
async def delete_task(id_: str, session: DBSessionDep):
    stmt = select(Task).where(Task.task_id == id_)
    result = await session.execute(stmt)
    task = result.scalar_one()
    await session.delete(task)

    stmt = select(Task).where(Task.step_id == task.step_id)
    tasks = await session.scalars(stmt)
    for t in tasks.all():
        if t.task_order > task.task_order:
            t.task_order = t.task_order - 1

    await session.commit()


@procedure_router.put("/tasks/{id_}/order")
async def update_task_order(id_: str, data: TaskOrder, session: DBSessionDep):
    stmt = select(Task).where(Task.task_id == id_)
    task = await session.scalar(stmt)

    stmt = select(Task).where(Task.step_id == task.step_id)
    if task.step_id == data.step_id and task.task_order > data.task_order:
        stmt = stmt.where(Task.task_order < task.task_order).where(Task.task_order >= data.task_order)
        tasks = await session.scalars(stmt)

        for t in tasks.all():
            t.task_order += 1
    else:
        stmt = stmt.where(Task.task_order >= task.task_order)
        if task.step_id == data.step_id:
            stmt = stmt.where(Task.task_order <= data.task_order)
        tasks = await session.scalars(stmt)

        for t in tasks.all():
            t.task_order -= 1

    if task.step_id != data.step_id:
        stmt = select(Task).where(Task.step_id == data.step_id).where(Task.task_order >= data.task_order)
        tasks = await session.scalars(stmt)

        for t in tasks.all():
            t.task_order += 1

    task.step_id = data.step_id
    task.task_order = data.task_order

    await session.commit()


@procedure_router.get("/tasks/{id_}/template_file")
async def download_template(id_: str, session: DBSessionDep):
    stmt = select(Task).where(Task.task_id == id_).options(subqueryload(Task.step).subqueryload(Step.category))
    task = await session.scalar(stmt)

    file = TEMPLATES_PATH / task.template_file

    return FileResponse(file, filename='[TEMPLATE] ' + get_task_file_name(task, file.suffix))


@procedure_router.get("/tasks/{id_}/example_file")
async def download_example(id_: str, session: DBSessionDep):
    stmt = select(Task).where(Task.task_id == id_).options(subqueryload(Task.step).subqueryload(Step.category))
    task = await session.scalar(stmt)

    file = TEMPLATES_PATH / task.example_file

    return FileResponse(file, filename='[EXAMPLE] ' + get_task_file_name(task, file.suffix))
