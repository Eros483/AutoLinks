# ----- FastAPI application entry point @ backend/main.py -----
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.routes import router
from backend.utils.config import config
from backend.utils.logger import logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(f"Starting {config.app_name}")
    from backend.utils.qdrant import ensure_collection

    ensure_collection()

    if config.debug:
        logger.info("Debug mode enabled")
    if config.dry_run:
        logger.warning("DRY_RUN enabled - using fixture data")

    yield

    logger.info("Shutting down")


app = FastAPI(
    title=config.app_name,
    debug=config.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
