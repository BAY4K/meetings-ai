from fastapi import APIRouter

from app.api.routes.web import router as web_router
from app.api.routes.downloads import router as downloads_router
from app.api.routes.processing import router as processing_router


api_router = APIRouter()

api_router.include_router(web_router)
api_router.include_router(downloads_router)
api_router.include_router(processing_router)