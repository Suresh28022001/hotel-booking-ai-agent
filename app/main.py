from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.database import create_tables
from app.api.middleware import error_handler_middleware, validation_exception_handler
from app.api.routes import auth, hotels, bookings, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting Hotel Booking AI Agent", env=settings.app_env)
    await create_tables()
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-powered hotel booking API using LangGraph + OpenRouter",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.middleware("http")(error_handler_middleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(hotels.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}
