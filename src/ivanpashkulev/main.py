from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ivanpashkulev.chat.router import router as chat_router
from ivanpashkulev.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
