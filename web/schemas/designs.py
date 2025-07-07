from pydantic import BaseModel


class DesignCreate(BaseModel):
    name: str
    description: str
    project: str
    system: str


class DesignTaskUpdate(BaseModel):
    is_completed: bool


class DesignDocumentUpdate(BaseModel):
    document: str


class DesignMemberCreate(BaseModel):
    email: str


class CommentCreate(BaseModel):
    content: str
    to_admin: bool = False
    parent_id: int = None


class CommentUpdate(BaseModel):
    content: str
    to_admin: bool = False
