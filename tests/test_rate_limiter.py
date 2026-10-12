"""test_rate_limiter.py - Unit tests for TokenBucketLimiter and retry_with_backoff."""

import time
import unittest
from unittest.mock import MagicMock, patch

import requests

from src.rate_limiter import (
    TokenBucketLimiter,
    is_transient_error,
    retry_with_backoff,
)


class TestTokenBucketLimiter(unittest.TestCase):
    """Test TokenBucketLimiter rate limiting behavior."""

    def test_unlimited_when_zero_or_negative(self):
        limiter = TokenBucketLimiter(rate_per_minute=0)
        self.assertTrue(limiter.acquire(1.0, timeout=1.0))
        self.assertTrue(limiter.acquire(10.0, timeout=1.0))

    def test_burst_and_refill(self):
        # 120 RPM = 2 tokens per second, capacity = 4 tokens
        limiter = TokenBucketLimiter(rate_per_minute=120.0, capacity=4.0)

        # Acquire all initial capacity
        self.assertTrue(limiter.acquire(4.0, timeout=0.1))

        # Immediate acquire should fail or wait if timeout is too short
        start_t = time.monotonic()
        acquired = limiter.acquire(1.0, timeout=0.1)
        # Should timeout because 1 token requires 0.5s refill
        self.assertFalse(acquired)

        # Acquire with enough timeout (0.7s) to get 1 refilled token (0.5s needed)
        start_t = time.monotonic()
        acquired = limiter.acquire(1.0, timeout=1.5)
        elapsed = time.monotonic() - start_t
        self.assertTrue(acquired)
        self.assertGreaterEqual(elapsed, 0.3)


class TestTransientErrorDetection(unittest.TestCase):
    """Test is_transient_error logic across different exception types."""

    def test_requests_timeout_and_connection_error(self):
        exc_timeout = requests.exceptions.Timeout("Connection timed out")
        is_trans, retry_after = is_transient_error(exc_timeout)
        self.assertTrue(is_trans)
        self.assertIsNone(retry_after)

        exc_conn = requests.exceptions.ConnectionError("Connection reset by peer")
        is_trans, _ = is_transient_error(exc_conn)
        self.assertTrue(is_trans)

    def test_requests_http_status_codes(self):
        # 429 Too Many Requests with Retry-After
        resp_429 = requests.Response()
        resp_429.status_code = 429
        resp_429.headers["Retry-After"] = "5"
        exc_429 = requests.exceptions.HTTPError("429 Client Error", response=resp_429)

        is_trans, retry_after = is_transient_error(exc_429)
        self.assertTrue(is_trans)
        self.assertEqual(retry_after, 5.0)

        # 503 Service Unavailable
        resp_503 = requests.Response()
        resp_503.status_code = 503
        exc_503 = requests.exceptions.HTTPError("503 Server Error", response=resp_503)
        is_trans, _ = is_transient_error(exc_503)
        self.assertTrue(is_trans)

        # 401 Unauthorized (Non-transient, should NOT retry)
        resp_401 = requests.Response()
        resp_401.status_code = 401
        exc_401 = requests.exceptions.HTTPError("401 Unauthorized", response=resp_401)
        is_trans, _ = is_transient_error(exc_401)
        self.assertFalse(is_trans)


class TestRetryWithBackoff(unittest.TestCase):
    """Test retry_with_backoff execution flow."""

    def test_successful_execution_without_retry(self):
        mock_func = MagicMock(return_value="success")
        result = retry_with_backoff(mock_func, max_retries=3, initial_delay=0.01)
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)

    def test_transient_error_retry_and_eventual_success(self):
        calls = [0]

        def flaky_api():
            calls[0] += 1
            if calls[0] < 3:
                raise requests.exceptions.Timeout("Flaky network")
            return "recovered"

        result = retry_with_backoff(
            flaky_api,
            max_retries=3,
            initial_delay=0.02,
            backoff_factor=1.5,
            jitter=False,
            service_name="TestAPI"
        )
        self.assertEqual(result, "recovered")
        self.assertEqual(calls[0], 3)

    def test_non_transient_error_fails_immediately(self):
        calls = [0]

        def fatal_api():
            calls[0] += 1
            resp_400 = requests.Response()
            resp_400.status_code = 400
            raise requests.exceptions.HTTPError("Bad Request", response=resp_400)

        with self.assertRaises(requests.exceptions.HTTPError):
            retry_with_backoff(
                fatal_api,
                max_retries=3,
                initial_delay=0.01,
                service_name="TestAPI"
            )

        # Must not retry on 400 Bad Request
        self.assertEqual(calls[0], 1)

    def test_exhausted_retries_raises_last_exception(self):
        calls = [0]

        def always_failing():
            calls[0] += 1
            raise requests.exceptions.Timeout("Permanent timeout")

        with self.assertRaises(requests.exceptions.Timeout):
            retry_with_backoff(
                always_failing,
                max_retries=3,
                initial_delay=0.01,
                backoff_factor=1.5,
                jitter=False,
                service_name="TestAPI"
            )

        self.assertEqual(calls[0], 3)


if __name__ == "__main__":
    unittest.main()
