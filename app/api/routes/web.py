from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.config import STATIC_DIR


router = APIRouter(
    tags=['web'],
)

@router.get('/', include_in_schema=False)
def index():
    return FileResponse(
        STATIC_DIR / 'index.html',
    )