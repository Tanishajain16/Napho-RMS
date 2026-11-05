from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Startup / shutdown lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run init_db() and optionally seed on first startup."""
    from app.database import init_db

    logger.info("Starting Napho RMS API…")
    init_db()
    logger.info("Database tables verified / created.")

    # Auto-seed if the database looks empty (no organisations exist)
    try:
        from app.database import SessionLocal
        from app.models.organization import Organization

        with SessionLocal() as db:
            count = db.query(Organization).count()

        if count == 0:
            logger.info("Database appears empty — running seed script…")
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import importlib
            seed_module = importlib.import_module("seed")
            seed_module.main()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Auto-seed failed (non-fatal): %s", exc)

    yield

    logger.info("Shutting down Napho RMS API.")


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Napho RMS API",
    version="1.0.0",
    description=(
        "Reimbursement Management System — FastAPI backend.\n\n"
        "**Authenticating in Swagger:** click **Authorize**, enter an email as *username* "
        "(e.g. `admin@napho.com`) and the password (`password123`), leave client fields blank. "
        "The bearer token is then sent with every request.\n\n"
        "- Swagger UI: `/docs`\n- ReDoc: `/redoc`\n- OpenAPI JSON: `/openapi.json`"
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,   # keep token across page reloads
        "displayRequestDuration": True,
        "filter": True,                 # search box for endpoints
        "tryItOutEnabled": True,
    },
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> Response:
    """Add X-Process-Time header and log slow requests."""
    start = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"
    if elapsed_ms > 500:
        logger.warning(
            "Slow request: %s %s took %.2fms",
            request.method, request.url.path, elapsed_ms,
        )
    return response


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Static file serving for uploads
# ---------------------------------------------------------------------------

# Ensure the upload directory exists before mounting
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ---------------------------------------------------------------------------
# API router
# ---------------------------------------------------------------------------

from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Quick liveness probe."""
    return {"status": "ok", "version": app.version}
