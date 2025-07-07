#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
from typing import Annotated, Optional

from fastapi import Depends, Request, HTTPException, status
from fastapi_mail import ConnectionConfig, MessageSchema, FastMail, MessageType
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, JWTStrategy, CookieTransport
from fastapi_users.db import SQLAlchemyUserDatabase

from auth.db import User, get_user_db, UserLevel
from settings import settings


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")
        await self.request_verify(user, request)

    async def on_after_forgot_password(
            self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
            self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME
        )

        message = MessageSchema(
            subject="Email Verification",
            recipients=[user.email],
            body=f"Please verify your email by clicking on the following link: http://{settings.DOMAIN}/auth/verify/{token}",
            subtype=MessageType.html
        )
        fm = FastMail(conf)

        await fm.send_message(message)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


# bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
cookie_transport = CookieTransport(cookie_max_age=3600, cookie_secure=False)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_user = fastapi_users.current_user(active=True, optional=True)


async def current_active_user(request: Request, user: User = Depends(current_user)):
    request.state.user = user

    if user is None:
        if str(request.url.path).startswith('/api'):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        else:
            raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={'Location': '/auth/login'})

    return user

ActiveUserDep = Annotated[User, Depends(current_active_user)]
#
# async def current_active_lecturer(user: ActiveUserDep):
#     if user.level == UserLevel.User:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
#
#     return user


async def current_active_admin(user: ActiveUserDep):
    if user.level != UserLevel.Admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return user
