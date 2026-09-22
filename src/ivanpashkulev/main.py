from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ivanpashkulev.chat.dependencies import get_chat_service
from ivanpashkulev.chat.router import router as chat_router
from ivanpashkulev.core.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_chat_service()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
