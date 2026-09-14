import pytest
from fakeredis.aioredis import FakeRedis

from ivanpashkulev.chat.rate_limit import ChatRateLimiter


@pytest.mark.asyncio
async def test_allows_requests_until_the_daily_limit_is_reached() -> None:
    redis = FakeRedis(decode_responses=True)
    limiter = ChatRateLimiter(redis, limit=2)

    assert await limiter.retry_after_seconds("203.0.113.10") is None
    assert await limiter.retry_after_seconds("203.0.113.10") is None

    retry_after_seconds = await limiter.retry_after_seconds("203.0.113.10")

    assert retry_after_seconds is not None
    assert 1 <= retry_after_seconds <= ChatRateLimiter.WINDOW_SECONDS
