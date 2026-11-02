from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import engine
from app.routers import auth, health, images, media, verification

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de provenance et d'authenticité des images du prototype Prisme.",
    debug=settings.debug,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(media.router, prefix=settings.api_v1_prefix)
app.include_router(images.router, prefix=settings.api_v1_prefix)
app.include_router(verification.router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs", "health": "/health/ready"}
