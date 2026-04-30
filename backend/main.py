# ----- FastAPI application entry point @ backend/main.py -----
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.v1.routes import router
from backend.utils.config import config
from backend.utils.logger import logger

app = FastAPI(
    title=config.app_name,
    debug=config.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {config.app_name}")
    if config.debug:
        logger.info("Debug mode enabled")
    if config.dry_run:
        logger.warning("DRY_RUN enabled - using fixture data")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
