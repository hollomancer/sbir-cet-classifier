"""Performance monitoring utilities."""

import functools
import time
import logging
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@contextmanager
def timer(operation_name: str):
    """Context manager for timing operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("⏱️  %s: %.3fs", operation_name, elapsed)


def profile_memory(func: F) -> F:
    """Decorator to profile memory usage of a function."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024 / 1024  # MB

            result = func(*args, **kwargs)

            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            mem_diff = mem_after - mem_before

            if mem_diff > 10:  # Only log if significant change
                logger.info("🧠 %s: %+0.1fMB memory change", func.__name__, mem_diff)

            return result
        except ImportError:
            # psutil not available, just run the function
            return func(*args, **kwargs)

    return wrapper


def time_function(func: F) -> F:
    """Decorator to time function execution."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        if elapsed > 0.1:  # Only log if > 100ms
            logger.info("⏱️  %s: %.3fs", func.__name__, elapsed)

        return result

    return wrapper
