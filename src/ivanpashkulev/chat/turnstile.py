import logging
from secrets import token_urlsafe

import httpx
from redis.asyncio import Redis
from redis.exceptions import RedisError

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
SESSION_COOKIE_NAME = "chat_turnstile_session"
SESSION_KEY_PREFIX = "chat-turnstile-session:"

logger = logging.getLogger(__name__)


class TurnstileVerificationError(Exception):
    """The supplied Turnstile token is absent, invalid, expired, or mismatched."""


class TurnstileUnavailableError(Exception):
    """Cloudflare Siteverify cannot be reached or returned an invalid response."""


class TurnstileSessionStoreError(Exception):
    """Redis cannot read or create a verified browser session."""


class TurnstileService:
    def __init__(
        self,
        redis: Redis,
        secret_key: str,
        expected_hostname: str | None,
        session_ttl_seconds: int,
    ) -> None:
        self._redis = redis
        self._secret_key = secret_key
        self._expected_hostname = expected_hostname
        self._session_ttl_seconds = session_ttl_seconds

    async def has_valid_session(self, session_id: str | None) -> bool:
        if not session_id:
            return False

        try:
            return await self._redis.exists(self._session_key(session_id)) == 1
        except RedisError as error:
            raise TurnstileSessionStoreError from error

    async def verify_token(
        self,
        token: str | None,
        client_ip: str,
    ) -> None:
        if not token:
            raise TurnstileVerificationError

        result = await self._validate_token(token, client_ip)
        if result.get("success") is not True:
            logger.warning(
                "Turnstile verification rejected: error_codes=%s hostname=%s",
                result.get("error-codes"),
                result.get("hostname"),
            )
            raise TurnstileVerificationError

        if (
            self._expected_hostname
            and result.get("hostname") != self._expected_hostname
        ):
            logger.warning(
                "Turnstile hostname mismatch: expected=%s actual=%s",
                self._expected_hostname,
                result.get("hostname"),
            )
            raise TurnstileVerificationError

    async def create_session(self) -> str:
        session_id = token_urlsafe(32)
        try:
            await self._redis.set(
                self._session_key(session_id),
                "verified",
                ex=self._session_ttl_seconds,
            )
        except RedisError as error:
            raise TurnstileSessionStoreError from error

        return session_id

    async def _validate_token(self, token: str, client_ip: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    SITEVERIFY_URL,
                    data={
                        "secret": self._secret_key,
                        "response": token,
                        "remoteip": client_ip,
                    },
                )
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise TurnstileUnavailableError from error

        if not isinstance(result, dict):
            raise TurnstileUnavailableError

        return result

    @staticmethod
    def _session_key(session_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}{session_id}"
