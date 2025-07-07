import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from auth.users import User
from database.connection import Base
from .procedures import Procedure


class OwnerType(Enum):
    User = auto()
    Group = auto()


class Design(Base):
    __tablename__ = 'designs'

    design_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    project: Mapped[str]
    system: Mapped[str]
    description: Mapped[str]
    procedure_id: Mapped[int]
    owner_type: Mapped[OwnerType]
    owner_id: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_deleted: Mapped[bool] = mapped_column(default=False)

    members: Mapped[List['User']] = relationship(secondary="design_members")
    procedure: Mapped[Procedure] = relationship()

    __table_args__ = (
        ForeignKeyConstraint(['procedure_id'], ['procedures.procedure_id']),
    )


class DesignFile(Base):
    __tablename__ = 'design_files'

    design_file_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    design_id: Mapped[int]
    task_id: Mapped[uuid.UUID]
    file_name: Mapped[Optional[str]]
    user_id: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_deleted: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.id']),
        ForeignKeyConstraint(['design_id'], ['designs.design_id']),
        ForeignKeyConstraint(['task_id'], ['tasks.task_id'])
    )


class DesignTask(Base):
    __tablename__ = 'design_tasks'

    design_id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    is_completed: Mapped[bool] = mapped_column(default=False)
    output_edited_at: Mapped[Optional[datetime]]

    __table_args__ = (
        ForeignKeyConstraint(['design_id'], ['designs.design_id']),
        ForeignKeyConstraint(['task_id'], ['tasks.task_id'])
    )


class DesignDocument(Base):
    __tablename__ = 'design_documents'

    document_id: Mapped[int] = mapped_column(primary_key=True)
    design_id: Mapped[int]
    task_id: Mapped[uuid.UUID]
    document: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(['design_id'], ['designs.design_id']),
        ForeignKeyConstraint(['task_id'], ['tasks.task_id'])
    )


class DesignMember(Base):
    __tablename__ = 'design_members'

    design_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    user: Mapped['User'] = relationship()

    __table_args__ = (
        ForeignKeyConstraint(['design_id'], ['designs.design_id']),
        ForeignKeyConstraint(['user_id'], ['users.id']),
    )


class Comment(Base):
    __tablename__ = 'comments'

    comment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content: Mapped[str]
    title: Mapped[str]
    writer_id: Mapped[uuid.UUID]
    to_admin: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    edited_at: Mapped[datetime] = mapped_column(nullable=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    parent_id: Mapped[int] = mapped_column(nullable=True)
    design_id: Mapped[int]
    step_id: Mapped[uuid.UUID]

    writer: Mapped['User'] = relationship()
    replies: Mapped[List['Comment']] = relationship(order_by='Comment.created_at')
    parent: Mapped['Comment'] = relationship(remote_side=[comment_id])
    design: Mapped['Design'] = relationship()

    __table_args__ = (
        ForeignKeyConstraint(['parent_id'], ['comments.comment_id']),
        ForeignKeyConstraint(['writer_id'], ['users.id']),
        ForeignKeyConstraint(['design_id'], ['designs.design_id']),
        ForeignKeyConstraint(['step_id'], ['steps.step_id']),
    )
