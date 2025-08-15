from __future__ import annotations
import time
from typing import Dict, Tuple
from ..core.config import settings

# Simple in-memory rate limiter (per-process). Replace with Redis for production.
# Stores: key -> (first_attempt_epoch, count)
_attempts: Dict[str, Tuple[float, int]] = {}


def check_and_increment(key: str) -> None:
    now = time.time()
    window = settings.rate_limit_auth_window_seconds
    max_attempts = settings.rate_limit_auth_attempts

    first, count = _attempts.get(key, (now, 0))
    if now - first > window:
        # reset window
        first, count = now, 0
    if count >= max_attempts:
        raise RateLimitExceeded(f"Too many attempts. Try again in {int(window - (now - first))}s")
    _attempts[key] = (first, count + 1)


class RateLimitExceeded(Exception):
    pass


def reset(key: str) -> None:
    _attempts.pop(key, None)
