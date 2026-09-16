from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import STATIC_DIR
from app.core.lifespan import lifespan


app = FastAPI(
    title="Meeting AI",
    lifespan=lifespan,
)


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


app.include_router(api_router)