#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from enum import Enum, auto

from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base, DBSessionDep


class UserLevel(Enum):
    User        = 'User'
    Admin       = 'Admin'


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = 'users'

    name: Mapped[str] = mapped_column()
    level: Mapped[UserLevel] = mapped_column(default=UserLevel.User)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


async def get_user_db(session: DBSessionDep):
    yield SQLAlchemyUserDatabase(session, User)
