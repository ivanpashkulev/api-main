from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ivanpashkulev.chat.dependencies import (
    ChatRateLimiterDep,
    TurnstileServiceDep,
    enforce_chat_rate_limit,
    enforce_chat_request_limits,
    get_chat_service,
    get_client_ip,
)
from ivanpashkulev.chat.schemas import ChatRequest
from ivanpashkulev.chat.service import ChatService
from ivanpashkulev.chat.turnstile import (
    SESSION_COOKIE_NAME,
    TurnstileSessionStoreError,
    TurnstileUnavailableError,
    TurnstileVerificationError,
)
from ivanpashkulev.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


@router.get("/session")
async def get_chat_session(
    http_request: Request,
    turnstile: TurnstileServiceDep,
) -> dict[str, bool]:
    try:
        verified = await turnstile.has_valid_session(
            http_request.cookies.get(SESSION_COOKIE_NAME)
        )
    except TurnstileSessionStoreError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "chat_verification_unavailable"},
        ) from error

    return {"verified": verified}


@router.post("")
async def chat(
    http_request: Request,
    request: ChatRequest,
    service: ChatServiceDep,
    rate_limiter: ChatRateLimiterDep,
    turnstile: TurnstileServiceDep,
) -> StreamingResponse:
    enforce_chat_request_limits(request)

    try:
        session_verified = await turnstile.has_valid_session(
            http_request.cookies.get(SESSION_COOKIE_NAME)
        )
        if not session_verified:
            await turnstile.verify_token(
                request.turnstile_token,
                get_client_ip(http_request),
            )
    except TurnstileVerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "turnstile_verification_required"},
        ) from error
    except (TurnstileUnavailableError, TurnstileSessionStoreError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "chat_verification_unavailable"},
        ) from error

    await enforce_chat_rate_limit(http_request, rate_limiter)

    new_session_id: str | None = None
    if not session_verified:
        try:
            new_session_id = await turnstile.create_session()
        except TurnstileSessionStoreError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "chat_verification_unavailable"},
            ) from error

    async def generate():
        async for chunk in service.stream(request.message, request.history):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    response = StreamingResponse(generate(), media_type="text/event-stream")

    if new_session_id:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=new_session_id,
            max_age=settings.turnstile_session_ttl_seconds,
            httponly=True,
            secure=settings.turnstile_cookie_secure,
            samesite="lax",
            path="/",
        )

    return response
