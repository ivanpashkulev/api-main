from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ivanpashkulev.chat.rate_limit import ChatRateLimiter
from ivanpashkulev.chat.schemas import ChatRequest
from ivanpashkulev.chat.service import ChatService
from ivanpashkulev.core.config import settings


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService()


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_chat_rate_limiter() -> ChatRateLimiter:
    return ChatRateLimiter(get_redis(), settings.chat_rate_limit_per_day)


ChatRateLimiterDep = Annotated[
    ChatRateLimiter,
    Depends(get_chat_rate_limiter),
]


def enforce_chat_request_limits(chat_request: ChatRequest) -> None:
    if len(chat_request.message) > settings.chat_max_message_characters:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={"code": "chat_message_limit_exceeded"},
        )

    history_characters = sum(len(message.content) for message in chat_request.history)
    if history_characters > settings.chat_max_history_characters:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={"code": "conversation_history_limit_exceeded"},
        )


async def enforce_chat_rate_limit(
    request: Request,
    rate_limiter: ChatRateLimiterDep,
) -> None:
    client_ip = request.headers.get("X-Real-IP")
    if client_ip is None:
        client_ip = request.client.host if request.client else "unknown"

    try:
        retry_after_seconds = await rate_limiter.retry_after_seconds(client_ip)
    except RedisError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat is temporarily unavailable.",
        ) from error

    if retry_after_seconds is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat request limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after_seconds)},
        )
