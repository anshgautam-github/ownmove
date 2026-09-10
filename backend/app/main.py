"""FastAPI application entry point.

Run locally:
    cd backend
    uvicorn app.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.middleware.error_handler import register_exception_handlers
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks.

    Long-lived resources (DB pools, vector index handles, LLM clients) get
    created here once rather than per-request.
    """
    configure_logging()
    logger.info(
        "Starting %s v%s (env=%s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )

    # Warm up the recommendation embedding model (sentence-transformers/
    # all-MiniLM-L6-v2) so the first /recommendations/for-you request
    # doesn't pay for loading it off disk. Gated behind
    # EMBEDDING_WARM_UP_ON_STARTUP (default False, see app/core/config.py)
    # because loading it — and the torch runtime under it — is what pushed
    # a 512MB instance (Render's free tier) over its memory limit during
    # boot. With the flag off, nothing is loaded here: EmbeddingGenerator
    # (app/ai/embeddings/generator.py) still lazy-loads the model itself,
    # on the first request that actually needs it, via `_load_model()`'s
    # `@lru_cache` — recommendations/embeddings keep working either way,
    # this only controls whether that cost is paid at boot or on demand.
    # Best-effort and non-fatal when enabled: an environment that hasn't
    # installed the optional `sentence-transformers` dependency yet (see
    # requirements.txt) should still boot and serve every other route —
    # EmbeddingGenerator raises a clear 503 on first actual use in that
    # case instead.
    if settings.EMBEDDING_WARM_UP_ON_STARTUP:
        try:
            from app.ai.embeddings.generator import _load_model

            await asyncio.to_thread(_load_model)
        except Exception:  # noqa: BLE001 - startup warm-up must never block boot
            logger.warning(
                "Embedding model warm-up skipped (will load lazily on first use).",
                exc_info=True,
            )
    else:
        logger.info(
            "Embedding model warm-up skipped (EMBEDDING_WARM_UP_ON_STARTUP=False); "
            "will load lazily on first use.",
        )

    yield

    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    """App factory — keeps construction testable and import-side-effect free."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        # Hide interactive docs in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    # Correlation id first so every downstream log line can carry it.
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.add_middleware(SecurityHeadersMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
