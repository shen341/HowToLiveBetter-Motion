"""rate_limiter.py - Token Bucket rate limiting and exponential backoff retry mechanisms.

Designed for high-throughput batch generation pipelines in HowToLiveBetter-Motion.
Protects against API rate limits (HTTP 429), gateway timeouts (HTTP 504), and temporary outages (HTTP 502/503).
"""

import math
import random
import threading
import time
from typing import Any, Callable, Optional, Sequence, Tuple, Type, Union

import requests

try:
    import openai
    from openai import (
        APIConnectionError,
        APIError,
        APIStatusError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def _safe_print(text: str):
    """Safely print text without raising UnicodeEncodeError on Windows CP932/CP936 consoles."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        try:
            clean_text = text.encode("gbk", errors="replace").decode("gbk", errors="replace")
            print(clean_text, flush=True)
        except Exception:
            try:
                clean_text = text.encode("ascii", errors="replace").decode("ascii")
                print(clean_text, flush=True)
            except Exception:
                pass


class TokenBucketLimiter:
    """Thread-safe Token Bucket rate limiter.
    
    Ensures that outgoing requests to external services (Muse AI, Cloudflare Edge-TTS)
    do not exceed the configured Requests Per Minute (RPM).
    """

    def __init__(self, rate_per_minute: float = 30.0, capacity: Optional[float] = None):
        """Initialize Token Bucket.
        
        Args:
            rate_per_minute: Maximum allowed requests per minute. <= 0 means unlimited.
            capacity: Maximum burst capacity of the bucket. Defaults to max(1.0, 2 * refill_rate).
        """
        self.rate_per_minute = float(rate_per_minute)
        self.rate_per_second = self.rate_per_minute / 60.0 if self.rate_per_minute > 0 else 0.0
        if capacity is not None:
            self.capacity = float(capacity)
        else:
            self.capacity = max(1.0, self.rate_per_second * 2.0) if self.rate_per_second > 0 else 1.0

        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, tokens: float = 1.0, timeout: float = 60.0) -> bool:
        """Acquire specified number of tokens. Blocks until available or timeout is reached.
        
        Args:
            tokens: Number of tokens needed (default 1.0).
            timeout: Maximum seconds to wait before giving up (default 60s).
            
        Returns:
            True if tokens were acquired, False if timeout expired.
        """
        if self.rate_per_minute <= 0:
            return True

        deadline = time.monotonic() + timeout

        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_second)
                self.last_refill = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                missing = tokens - self.tokens
                wait_time = missing / self.rate_per_second

            if time.monotonic() + wait_time > deadline:
                return False

            # Sleep in small chunks to avoid oversleeping
            sleep_slice = min(wait_time, 0.5)
            time.sleep(sleep_slice)

    def set_rate(self, rate_per_minute: float):
        """Update rate dynamically."""
        with self.lock:
            self.rate_per_minute = float(rate_per_minute)
            self.rate_per_second = self.rate_per_minute / 60.0 if self.rate_per_minute > 0 else 0.0
            self.capacity = max(1.0, self.rate_per_second * 2.0) if self.rate_per_second > 0 else 1.0
            self.tokens = min(self.tokens, self.capacity)


def is_transient_error(exc: Exception) -> Tuple[bool, Optional[float]]:
    """Determine if an exception is transient (retryable) and extract Retry-After header if present.
    
    Retryable conditions:
    - HTTP 429: Too Many Requests (Rate limit)
    - HTTP 500, 502, 503, 504: Server/Gateway errors
    - Connection timeouts, connection drops, socket errors
    """
    retry_after: Optional[float] = None

    # 1. Check Requests exceptions
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True, None

    if isinstance(exc, requests.exceptions.HTTPError):
        status = getattr(exc.response, "status_code", None)
        if status in (429, 500, 502, 503, 504):
            if exc.response is not None and "Retry-After" in exc.response.headers:
                try:
                    retry_after = float(exc.response.headers["Retry-After"])
                except (ValueError, TypeError):
                    pass
            return True, retry_after
        return False, None

    # 2. Check OpenAI exceptions if installed
    if HAS_OPENAI:
        if isinstance(exc, (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)):
            return True, None
        if isinstance(exc, APIStatusError):
            status = getattr(exc, "status_code", None)
            if status in (429, 500, 502, 503, 504):
                if hasattr(exc, "response") and exc.response is not None:
                    header_val = exc.response.headers.get("retry-after") if hasattr(exc.response, "headers") else None
                    if header_val:
                        try:
                            retry_after = float(header_val)
                        except (ValueError, TypeError):
                            pass
                return True, retry_after
            return False, None

    # 3. Standard timeout and connection errors
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True, None

    # 4. Check error message string for common rate-limit or gateway keywords
    msg = str(exc).lower()
    if any(k in msg for k in ("429", "rate limit", "too many requests", "502 bad gateway", "503 service unavailable", "504 gateway timeout", "timed out", "connection reset")):
        return True, None

    return False, None


def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    service_name: str = "API",
    limiter: Optional[TokenBucketLimiter] = None,
    **kwargs,
) -> Any:
    """Execute a callable with exponential backoff retry on transient errors.
    
    Retry intervals (with backoff_factor=2.0, initial_delay=2.0s):
    - Attempt 1: 2.0s + jitter
    - Attempt 2: 4.0s + jitter
    - Attempt 3: 8.0s + jitter
    
    Args:
        func: The function to execute.
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial wait seconds before first retry.
        backoff_factor: Multiplier for subsequent retry delays.
        jitter: Whether to add a small random jitter to avoid thundering herd.
        service_name: Name of the service being called (for logs).
        limiter: Optional TokenBucketLimiter to acquire tokens from before each attempt.
    """
    delay = initial_delay

    for attempt in range(1, max_retries + 1):
        if limiter is not None:
            acquired = limiter.acquire(tokens=1.0, timeout=45.0)
            if not acquired:
                _safe_print(f"⚠️ [{service_name}] 令牌桶等待超时 (45s)，仍尝试发起请求...")

        try:
            return func(*args, **kwargs)
        except Exception as e:
            is_transient, retry_after = is_transient_error(e)

            if not is_transient or attempt >= max_retries:
                # Fatal error or max retries exhausted
                raise e

            # Compute wait time
            sleep_time = retry_after if retry_after is not None else delay
            if jitter:
                sleep_time += random.uniform(0.1, 0.6)

            _safe_print(
                f"   ⚠️ [{service_name}] 遇到瞬时异常或限流 (第 {attempt}/{max_retries} 次): {e!s:.90}..."
            )
            _safe_print(f"      ⏳ 正在启动指数退避重试，休眠 {sleep_time:.2f}s 后自动重试...")
            time.sleep(sleep_time)

            delay *= backoff_factor
