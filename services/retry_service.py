import asyncio
from typing import Any, Awaitable, Callable


class RetryService:
    def __init__(self, max_attempts: int = 2, base_delay: float = 0.15, timeout_s: float = 1.0) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.timeout_s = timeout_s

    async def run(self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await asyncio.wait_for(fn(*args, **kwargs), timeout=self.timeout_s)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_attempts:
                    await asyncio.sleep(self.base_delay * attempt)
        if last_error:
            raise last_error
        raise RuntimeError("Retry failed without exception")
