from typing import Annotated

from fastapi import Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import subqueryload, make_transient

from database.connection import DBSessionDep
from models.procedures import Category, Step, Procedure, Task, ProcedureStatus
from schemas.procedures import ProcedureCreate

PHASE_SYMBOLS = ['', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
STEP_SYMBOLS = ['', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']


async def editing_procedure_id(session: DBSessionDep):
    stmt = (select(Procedure.procedure_id).where(Procedure.status == ProcedureStatus.Editing)
            .order_by(desc(Procedure.created_at)).limit(1))

    return await session.scalar(stmt)


async def current_procedure_id(session: DBSessionDep):
    stmt = (select(Procedure.procedure_id).where(Procedure.status == ProcedureStatus.Published)
            .order_by(desc(Procedure.created_at)).limit(1))

    return await session.scalar(stmt)


async def get_procedure_for_copy(session: DBSessionDep, procedure_id: int):
    stmt = (select(Procedure).
            where(Procedure.procedure_id == procedure_id).
            options(subqueryload(Procedure.categories).
                    subqueryload(Category.steps).
                    subqueryload(Step.tasks).
                    subqueryload(Task.leaders)))

    return await session.scalar(stmt)


async def get_procedure_info(session: AsyncSession, procedure_id: int):
    stmt = select(Procedure).where(Procedure.procedure_id == procedure_id)
    procedure = await session.scalar(stmt)

    return procedure


async def get_procedure(session: AsyncSession, procedure_id: int):
    procedure = []
    for phase in range(1, 4):
        stmt = (select(Category)
                .where(Category.procedure_id == procedure_id).where(Category.phase == phase)
                .order_by(Category.category_order)
                .options(subqueryload(Category.steps).subqueryload(Step.tasks)))
        categories = await session.scalars(stmt)

        procedure.append(categories.all())

    return procedure


def get_task_counts(procedure):
    counts = {'phase': {}, 'category': {}, 'step': {}}
    for phase in range(1, 4):
        categories = procedure[phase - 1]
        counts['phase'][phase] = 0
        for category in categories:
            if category.steps:
                counts['category'][category.category_id] = 0
                for step in category.steps:
                    counts['step'][step.step_id] = len(step.tasks) if step.tasks else 1
                    counts['category'][category.category_id] += counts['step'][step.step_id]
                    counts['phase'][phase] += counts['step'][step.step_id]
            else:
                counts['category'][category.category_id] = 1
                counts['phase'][phase] += 1

    return counts


def copy_procedure(session: DBSessionDep, procedure: Procedure, data: ProcedureCreate, status: ProcedureStatus):
    session.expunge(procedure)
    make_transient(procedure)
    procedure.procedure_id = None
    procedure.created_at = None
    procedure.name = data.name
    procedure.note = data.note
    procedure.status = status

    for category in procedure.categories:
        make_transient(category)
        category.category_id = None

        for step in category.steps:
            make_transient(step)
            step.step_id = None

            for task in step.tasks:
                make_transient(task)
                task.task_id = None

                leaders = []
                while len(task.leaders) > 0:
                    l = task.leaders.pop()
                    leaders.append(l)
                task.leaders = leaders

    session.add(procedure)


def category_number(category: Category):
    return f'{PHASE_SYMBOLS[category.phase]}-{category.category_order}'


def step_number(step: Step):
    return f'{category_number(step.category)}{"" if step.category.is_step else "-" + STEP_SYMBOLS[step.step_order]}'


def task_number(task: Task):
    return f'{step_number(task.step)}-{task.task_order}'


def get_task_file_name(task: Task, suffix: str):
    return f'{task_number(task)}-{task.output_code}{suffix}'


EditingProcedureIdDep = Annotated[int, Depends(editing_procedure_id)]
CurrentProcedureIdDep = Annotated[int, Depends(current_procedure_id)]