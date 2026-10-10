"""FastAPI app: wiring for settings, database pool, middleware, errors and routes.

Run with:  uvicorn app.main:create_app --factory
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, load_settings
from .db import create_pool
from .errors import internal_error_response, register_error_handlers
from .routers import applications, auth
from .schemas import HealthOut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("jobtracker")

DOCS_PATHS = ("/docs", "/openapi.json", "/redoc")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pool.open(wait=False)
        yield
        app.state.pool.close()

    # Interactive docs only outside production. docs/openapi.yaml is the contract.
    docs_on = not settings.is_production
    app = FastAPI(
        title="Job Application Tracker API",
        lifespan=lifespan,
        docs_url="/docs" if docs_on else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_on else None,
    )
    app.state.settings = settings
    app.state.pool = create_pool(settings.database_url)

    register_error_handlers(app)

    @app.middleware("http")
    async def security_headers_and_errors(request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            # Full details go to the server log only; the client gets a generic message.
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            response = internal_error_response()

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if not request.url.path.startswith(DOCS_PATHS):
            # A JSON API never needs to load scripts or be framed.
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    # Added last, so it wraps everything: even error responses get CORS headers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # Tokens go in the Authorization header, not cookies.
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", response_model=HealthOut, tags=["health"])
    def health():
        return HealthOut()

    app.include_router(auth.router)
    app.include_router(applications.router)
    return app

