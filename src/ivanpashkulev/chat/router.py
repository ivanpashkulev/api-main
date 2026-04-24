from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from ivanpashkulev.chat.schemas import ChatRequest
from ivanpashkulev.chat.service import ChatService
from ivanpashkulev.chat.dependencies import get_chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.post("")
async def chat(
    request: ChatRequest,
    service: ChatServiceDep,
) -> StreamingResponse:
    async def generate():
        async for chunk in service.stream(request.message, request.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
