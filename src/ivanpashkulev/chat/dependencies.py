from functools import lru_cache
from ivanpashkulev.chat.service import ChatService


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService()
