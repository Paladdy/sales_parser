import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.dependencies import build_container

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = build_container(use_memory=False)
    try:
        container.startup()
        logger.info("Application started")
    except Exception as exc:
        logger.error("Startup failed: %s", exc)
        raise
    app.state.container = container
    yield
    container.shutdown()
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    app = FastAPI(title="Lead Enricher", version="1.0.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
