from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1.router import v1_router
from app.config.database import Base, engine
from app.models.user import Users
from alembic.config import Config
from alembic import command
from app.config.middleware import RequestLoggingMiddleware
from app.config.exception import global_exception_handler
from app.config.logging_config import setup_logging

# Configure logging at startup — before anything else
setup_logging()


# Handel db migration at startup
@asynccontextmanager
async def lifespan(app):
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield


app = FastAPI(title="fastapi_apply", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.add_exception_handler(Exception, global_exception_handler)
app.include_router(v1_router)
