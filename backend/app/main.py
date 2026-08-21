from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, jobs, videos
from app.config import get_settings
from app.utils.errors import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("autocut")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    settings.ensure_dirs()
    logger.info("%s API ready", settings.app_name)
    yield
    # Shutdown (add cleanup here if needed later)
    logger.info("%s API shutting down", settings.app_name)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(videos.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "details": exc.details or None},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Something went wrong. Please try again.",
            "code": "internal_error",
            "details": None,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)