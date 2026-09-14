from fastapi import FastAPI

from app.api.router import api_router
from app.core.lifespan import lifespan


app = FastAPI(
    title="Meeting AI",
    lifespan=lifespan,
)

app.include_router(api_router)
