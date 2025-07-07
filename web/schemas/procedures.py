from typing import List

from pydantic import BaseModel


class ProcedureCreate(BaseModel):
    name: str
    note: str


class CategoryCreate(BaseModel):
    title: str
    phase: int
    is_step: bool = False


class CategoryUpdate(BaseModel):
    title: str


class CategoryOrder(BaseModel):
    phase: int
    category_order: int


class StepCreate(BaseModel):
    title: str
    category_id: str


class StepUpdate(BaseModel):
    title: str
    guide: str


class StepGuide(BaseModel):
    step_id: str
    guide: str


class StepOrder(BaseModel):
    category_id: str
    step_order: int


class TaskCreate(BaseModel):
    title: str
    step_id: str


class TaskUpdate(BaseModel):
    title: str
    description: str
    output_code: str = ''
    output_name: str = ''
    output_type: str = None
    template_markdown: str = ''
    example_markdown: str = ''
    leading_task_ids: List[str] = None


class TaskOrder(BaseModel):
    step_id: str
    task_order: int
