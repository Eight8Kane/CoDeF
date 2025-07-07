from pathlib import Path

from settings import settings


DOCUMENTS_PATH = Path(settings.DATA_PATH) / 'documents'
TEMPLATES_PATH = Path(settings.DATA_PATH) / 'templates'

IMAGES_PATH = Path(settings.DATA_PATH) / 'images'