#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import ForeignKeyConstraint, ForeignKey
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class ProcedureStatus(Enum):
    Published = auto()
    Editing = auto()
    Deleted = auto()


class OutputType(Enum):
    File = 'File'
    MD = 'Markdown'
    ATV = 'ATV'
    AHP = 'AHP'
    ECHC = 'ECHC'
    HOQ = 'HOQ'


class Procedure(Base):
    __tablename__ = 'procedures'

    procedure_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    note: Mapped[str]
    status: Mapped[ProcedureStatus] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    categories: Mapped[List['Category']] = relationship(order_by='Category.phase, Category.category_order')


class Category(Base):
    __tablename__ = 'categories'

    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                   primary_key=True, server_default=sa.text("gen_random_uuid()"))
    procedure_id: Mapped[int]
    title: Mapped[str]
    category_order: Mapped[int]
    is_step: Mapped[bool] = mapped_column(default=False)
    phase: Mapped[int]

    steps: Mapped[List['Step']] = relationship(order_by='Step.step_order', back_populates='category')

    __table_args__ = (
        ForeignKeyConstraint(['procedure_id'], ['procedures.procedure_id']),
    )


class Step(Base):
    __tablename__ = 'steps'

    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                               primary_key=True, server_default=sa.text("gen_random_uuid()"))
    title: Mapped[str]
    step_order: Mapped[int]
    guide: Mapped[Optional[str]] = mapped_column(default='')
    category_id: Mapped[uuid.UUID]

    category: Mapped['Category'] = relationship(back_populates='steps')
    tasks: Mapped[List['Task']] = relationship(order_by='Task.task_order', back_populates='step')

    __table_args__ = (
        ForeignKeyConstraint(['category_id'], ['categories.category_id']),
    )


class Task(Base):
    __tablename__ = 'tasks'

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                               primary_key=True, server_default=sa.text("gen_random_uuid()"))
    title: Mapped[str]
    task_order: Mapped[int]
    description: Mapped[str] = mapped_column(default='')
    output_code: Mapped[str] = mapped_column(default='')
    output_name: Mapped[str] = mapped_column(default='')
    output_type: Mapped[Optional[OutputType]]
    template_file: Mapped[Optional[str]]
    template_uploaded_at: Mapped[Optional[datetime]]
    example_file: Mapped[Optional[str]]
    example_uploaded_at: Mapped[Optional[datetime]]
    template_markdown: Mapped[str] = mapped_column(default='')
    example_markdown:  Mapped[str] = mapped_column(default='')
    step_id: Mapped[uuid.UUID] = mapped_column()

    leaders: Mapped[List['Task']] = relationship(secondary='prerequisites',
                                                 primaryjoin='Task.task_id == Prerequisite.trailing_task_id ',
                                                 secondaryjoin='Task.task_id == Prerequisite.leading_task_id',
                                                 back_populates='trailers')
    trailers: Mapped[List['Task']] = relationship(secondary='prerequisites',
                                                  primaryjoin='Task.task_id == Prerequisite.leading_task_id ',
                                                  secondaryjoin='Task.task_id == Prerequisite.trailing_task_id',
                                                  back_populates='leaders')

    step: Mapped['Step'] = relationship(back_populates='tasks')

    __table_args__ = (
        ForeignKeyConstraint(['step_id'], ['steps.step_id']),
    )


class Prerequisite(Base):
    __tablename__ = 'prerequisites'

    leading_task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tasks.task_id'), primary_key=True)
    trailing_task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tasks.task_id'), primary_key=True)
