from fastapi.templating import Jinja2Templates

from auth.db import UserLevel
from crud.procedure import get_task_file_name
from models.procedures import OutputType


def get_file_extension(filename: str):
    return filename.split('.')[-1] if '.' in filename else ''


templates = Jinja2Templates(directory="templates", context_processors=[])
templates.env.filters['get_file_extension'] = get_file_extension
templates.env.globals['UserLevel'] = UserLevel
templates.env.globals['OutputType'] = OutputType
templates.env.globals['edit_pages'] = {
    OutputType.MD:      'markdown',
    OutputType.ATV:     'atv',
    OutputType.AHP:     'ahp',
    OutputType.ECHC:    'echc',
    OutputType.HOQ:     'hoq'
}
templates.env.globals['get_task_file_name'] = get_task_file_name
