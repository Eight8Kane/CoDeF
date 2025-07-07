from uuid import uuid4

from fastapi import APIRouter, UploadFile

from app.file_system import IMAGES_PATH


data_router = APIRouter()


@data_router.post("/images/{target}")
async def upload_image(target: str, file: UploadFile) -> dict:
    filename = IMAGES_PATH / target / f'{uuid4()}.{file.filename.split(".")[-1]}'

    with open(filename, 'wb') as f:
        f.write(await file.read())

    return {
        'uri': '/' + filename.as_posix()
    }
