#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles

from auth.schemas import UserCreate, UserRead, UserUpdate
from auth.users import ActiveUserDep, auth_backend, current_active_user, fastapi_users, current_active_admin
from routes.admin.comments import comment_router
from routes.api.designs import design_router
from routes.api.editor import editor_router
from routes.api.file_data import data_router
from routes.api.procedures import procedure_router
from routes.api.users import user_router
from routes.page.auth import auth_router
from routes.page.designs import design_page_router
from routes.page.editor import editor_page_router
from routes.page.procedures import procedures_page_router
from routes.page.users import user_page_router


logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Not needed if you setup a migration system like Alembic
    # await create_db_and_tables()

    yield

    # Clean up here
    pass


app = FastAPI(lifespan=lifespan)

app.include_router(fastapi_users.get_auth_router(auth_backend, requires_verification=True), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"],)
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"],)
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"],)

# app.include_router(auth_page_router, prefix="/auth")
app.include_router(auth_router, prefix="/auth")

app.include_router(user_router, prefix="/api", dependencies=[Depends(current_active_admin)])
app.include_router(user_page_router, prefix="/admin", dependencies=[Depends(current_active_admin)])

app.include_router(procedure_router, prefix="/api", dependencies=[Depends(current_active_admin)])
app.include_router(procedures_page_router, prefix="/admin", dependencies=[Depends(current_active_admin)])

app.include_router(design_router, prefix="/api", dependencies=[Depends(current_active_user)])
app.include_router(design_page_router, prefix="", dependencies=[Depends(current_active_user)])

app.include_router(editor_router, prefix="/api", dependencies=[Depends(current_active_user)])
app.include_router(editor_page_router, prefix="", dependencies=[Depends(current_active_user)])

app.include_router(comment_router, prefix="", dependencies=[Depends(current_active_admin)])

app.include_router(data_router, prefix="/api", dependencies=[Depends(current_active_admin)])

app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/data', StaticFiles(directory='data'), name='data')

@app.get("/authenticated-route")
async def authenticated_route(user: ActiveUserDep):
    return {"message": f"Hello {user.email}!"}


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8001, reload=True)
