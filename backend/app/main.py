from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler

from . import storage, vector
from .config import get_settings
from .db import engine
from .logging_conf import configure_logging, get_logger
from .models import Base
from .routers import events, search

configure_logging()
log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    storage.ensure_bucket()
    vector.ensure_collection()
    log.info("startup_complete")
    yield


app = FastAPI(title="GrabPic API", version="0.1.0", lifespan=lifespan)

app.state.limiter = search.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(search.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
