"""FastAPI entry point for the BlindSpot backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import auth, debrief, decisions, sessions


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables on startup. In production, use migrations.
    init_db()
    yield


settings = get_settings()
app = FastAPI(
    title="BlindSpot API",
    description=(
        "Backend for the BlindSpot decision-simulation platform. "
        "Manages user accounts, simulation sessions, scenarios, decisions, "
        "and Bayesian analysis of within-subject patterns."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(decisions.router)
app.include_router(debrief.router)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}
