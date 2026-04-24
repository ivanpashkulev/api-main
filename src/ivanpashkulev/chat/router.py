from typing import Annotated
from fastapi import APIRouter, Depends
from ivanpashkulev.chat.schemas import ChatRequest, ChatResponse
from ivanpashkulev.chat.service import ChatService
from ivanpashkulev.chat.dependencies import get_chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatServiceDep,
) -> ChatResponse:
    response = await service.chat(request.message, request.history)
    return ChatResponse(response=response)
