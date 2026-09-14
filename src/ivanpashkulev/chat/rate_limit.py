from redis.asyncio import Redis


class ChatRateLimiter:
    WINDOW_SECONDS = 24 * 60 * 60

    def __init__(self, redis: Redis, limit: int) -> None:
        self._redis = redis
        self._limit = limit

    async def retry_after_seconds(self, client_ip: str) -> int | None:
        key = f"chat-rate-limit:{client_ip}"

        # Establish the 24-hour window before incrementing. This prevents a
        # process failure between commands from leaving a permanent key.
        await self._redis.set(key, 0, ex=self.WINDOW_SECONDS, nx=True)
        request_count = await self._redis.incr(key)

        if request_count <= self._limit:
            return None

        return max(
            await self._redis.ttl(key),
            1,
        )
