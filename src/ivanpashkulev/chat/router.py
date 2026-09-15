from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ivanpashkulev.chat.dependencies import (
    ChatRateLimiterDep,
    enforce_chat_rate_limit,
    enforce_chat_request_limits,
    get_chat_service,
)
from ivanpashkulev.chat.schemas import ChatRequest
from ivanpashkulev.chat.service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.post("")
async def chat(
    http_request: Request,
    request: ChatRequest,
    service: ChatServiceDep,
    rate_limiter: ChatRateLimiterDep,
) -> StreamingResponse:
    enforce_chat_request_limits(request)
    await enforce_chat_rate_limit(http_request, rate_limiter)

    async def generate():
        async for chunk in service.stream(request.message, request.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
