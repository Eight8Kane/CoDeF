import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, HTTPException, status, Request
from fastapi.responses import FileResponse
from markdown_it import MarkdownIt
from mdit_plain.renderer import RendererPlain
from sqlalchemy import select, func, desc, and_, or_, update
from sqlalchemy.orm import subqueryload, joinedload

from app.file_system import DOCUMENTS_PATH
from auth.db import UserLevel
from auth.users import ActiveUserDep, User
from crud.design import get_design
from crud.procedure import get_task_file_name, CurrentProcedureIdDep
from database.connection import DBSessionDep
from models.designs import Design, OwnerType, DesignTask, DesignFile, Comment, DesignMember
from models.procedures import Step, Task, Prerequisite
from schemas.designs import DesignCreate, DesignTaskUpdate, CommentCreate, CommentUpdate, DesignMemberCreate

design_router = APIRouter()


def get_comment_title(content: str):
    parser = MarkdownIt(renderer_cls=RendererPlain)
    first = content.strip().splitlines()[0]

    return parser.render(re.sub(r'!\[.*?]\(.*?\)', '[image attached]', first))


@design_router.post("/designs")
async def create_design(data: DesignCreate,
                        session: DBSessionDep, user: ActiveUserDep, procedure_id: CurrentProcedureIdDep):
    design = Design(name=data.name,
                    project=data.project,
                    system=data.system,
                    description=data.description,
                    procedure_id=procedure_id,
                    owner_type=OwnerType.User,
                    owner_id=user.id,
                    members=[user])

    session.add(design)
    await session.commit()
    await session.refresh(design)

    return design.design_id


@design_router.get("/designs")
async def get_designs(request: Request, session: DBSessionDep, user: ActiveUserDep):
    params = dict(request.query_params)
    tag_keyword = params['search[value]'].strip()
    name_keyword = f'%{tag_keyword}%'
    filter = or_(Design.name.ilike(name_keyword), Design.project.ilike(tag_keyword), Design.system.ilike(tag_keyword))

    if user.level == UserLevel.Admin:
        count_stmt = select(func.count()).select_from(Design)
        list_stmt = select(Design).options(subqueryload(Design.procedure))
    else:
        count_stmt = select(func.count()).select_from(Design).join(DesignMember).where(DesignMember.user_id == user.id)
        list_stmt = select(Design).join(DesignMember).where(DesignMember.user_id == user.id)

    count_stmt = count_stmt.where(Design.is_deleted == False)
    list_stmt = list_stmt.where(Design.is_deleted == False)

    total_records = await session.scalar(count_stmt)

    stmt = count_stmt.where(filter)
    filtered_records = await session.scalar(stmt)

    stmt = list_stmt.where(filter).offset(params['start']).limit(params['length'])
    if param := params.get('order[0][name]'):
        column = getattr(Design, param)
        stmt = stmt.order_by(desc(column) if params['order[0][dir]'] == 'desc' else column)

    designs = await session.scalars(stmt)

    return {
        'draw': params['draw'],
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': designs.all()
    }


@design_router.delete("/designs/{id_}")
async def delete_design(id_: int, session: DBSessionDep, user: ActiveUserDep):
    if user.level != UserLevel.Admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    design = await get_design(id_, session, user)
    design.is_deleted =True

    await session.commit()


@design_router.put("/designs/{id_}/tasks/{task_id}")
async def update_task(id_: int, task_id: str, data: DesignTaskUpdate, session: DBSessionDep, user: ActiveUserDep):
    await get_design(id_, session, user)
    task = DesignTask(design_id=id_, task_id=task_id, is_completed=data.is_completed)

    await session.merge(task)
    await session.commit()

    return task.is_completed


@design_router.post("/designs/{id_}/tasks/{task_id}/files")
async def upload_file(id_: int, task_id: str, file: UploadFile, session: DBSessionDep, user: ActiveUserDep):
    content = await file.read()
    document_file = f"{str(uuid4())}{Path(file.filename).suffix}"
    with open(DOCUMENTS_PATH / document_file, 'wb') as f:
        f.write(content)

    design_file = DesignFile(design_id=id_, task_id=task_id, file_name=document_file, user_id=user.id)

    session.add(design_file)
    await session.commit()

    return design_file


@design_router.delete("/designs/{id_}/tasks/{task_id}/files")
async def delete_files(id_: int, task_id: str, session: DBSessionDep, user: ActiveUserDep):
    await get_design(id_, session, user)

    stmt = update(DesignFile).where(DesignFile.task_id == task_id).values(is_deleted=True)
    await session.execute(stmt)

    await session.commit()


@design_router.get("/designs/{id_}/tasks/{task_id}/file")
async def download_file(id_: int, task_id: str, session: DBSessionDep, user: ActiveUserDep):
    design = await get_design(id_, session, user)

    stmt = (select(DesignFile)
            .where(DesignFile.design_id == id_, DesignFile.task_id == task_id, DesignFile.is_deleted == False)
            .order_by(desc(DesignFile.created_at)).limit(1))
    design_file = await session.scalar(stmt)

    if design_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    stmt = (select(Task).where(Task.task_id == design_file.task_id)
            .options(subqueryload(Task.step).subqueryload(Step.category)))
    task = await session.scalar(stmt)

    file = DOCUMENTS_PATH / design_file.file_name

    return FileResponse(file,
                        filename=f'{design.project}-{design.system}-{get_task_file_name(task, file.suffix)}')


@design_router.get("/designs/{id_}/tasks/{task_id}/dependency_statuses")
async def get_dependency_statuses(id_: int, task_id: str, session: DBSessionDep):
    stmt = (select(Task, DesignTask)
            .join(Prerequisite, Prerequisite.leading_task_id == Task.task_id)
            .join(DesignTask, (DesignTask.design_id == id_) & (DesignTask.task_id == Task.task_id), isouter=True)
            .where(Prerequisite.trailing_task_id == task_id)
            .options(subqueryload(Task.step).subqueryload(Step.category)))
    tasks = await session.execute(stmt)

    return {task.task_id: False if designTask is None else designTask.is_completed for task, designTask in tasks}


@design_router.post("/designs/{id_}/members")
async def create_member(id_: int, data: DesignMemberCreate, session: DBSessionDep, user: ActiveUserDep):

    design = await get_design(id_, session, user)

    stmt = select(User).where(User.email == data.email)
    user = await session.scalar(stmt)

    member = DesignMember(design_id=design.design_id, user_id=user.id)
    session.add(member)

    await session.commit()


@design_router.post("/designs/{id_}/steps/{step_id}/comments")
async def create_comment(id_: int, step_id: str, data: CommentCreate, session: DBSessionDep, user: ActiveUserDep):
    await get_design(id_, session, user)

    comment = Comment(content=data.content,
                      title=get_comment_title(data.content),
                      writer_id=user.id,
                      to_admin=data.to_admin,
                      parent_id=data.parent_id,
                      design_id=id_,
                      step_id=step_id)
    session.add(comment)

    await session.commit()
    await session.refresh(comment)

    return comment


@design_router.delete("/comments/{id_}")
async def delete_comment(id_: int, session: DBSessionDep, user: ActiveUserDep):
    stmt = (select(Comment)
            .options(subqueryload(Comment.replies))
            .where(Comment.comment_id == id_, Comment.writer_id == user.id))
    comment = await session.scalar(stmt)

    if comment:
        if comment.replies:
            comment.is_deleted = True
        else:
            await session.delete(comment)

        await session.commit()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@design_router.get("/comments/{id_}")
async def get_comment(id_: int, session: DBSessionDep, user: ActiveUserDep):
    stmt = (select(Comment)
            .where(Comment.comment_id == id_, Comment.writer_id == user.id))
    comment = await session.scalar(stmt)

    if comment:
        return comment
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@design_router.put("/comments/{id_}")
async def update_comment(id_: int, data: CommentUpdate, session: DBSessionDep, user: ActiveUserDep):
    stmt = (select(Comment)
            .where(Comment.comment_id == id_, Comment.writer_id == user.id))
    comment = await session.scalar(stmt)

    if comment:
        comment.content = data.content
        comment.title = get_comment_title(data.content)
        comment.to_admin = data.to_admin
        comment.edited_at = func.now()

        await session.commit()

        return comment
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@design_router.get("/designs/{id_}/comments")
async def get_comments(id_: int, request: Request, session: DBSessionDep, user: ActiveUserDep):
    await get_design(id_, session, user)

    base_filter = and_(Comment.design_id == id_, Comment.is_deleted == False)

    params = dict(request.query_params)
    search_value = f"%{params['search[value]']}%"

    stmt = select(func.count()).select_from(Comment).where(base_filter)
    total_records = await session.scalar(stmt)

    stmt = select(func.count()).select_from(Comment).where(base_filter).where(Comment.content.like(search_value))
    filtered_records = await session.scalar(stmt)

    stmt = (select(Comment).where(base_filter).where(Comment.content.like(search_value))
            .options(joinedload(Comment.writer)).order_by(desc(Comment.created_at))
            .offset(params['start']).limit(params['length']))
    comments = await session.scalars(stmt)

    return {
        'draw': params['draw'],
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': comments.all()
    }


@design_router.get("/user_name")
async def get_user_name(email: str, session: DBSessionDep):
    stmt = select(User).where(User.email == email)
    user = await session.scalar(stmt)

    if user:
        return user.name
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
