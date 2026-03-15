"""Simple test functions for exercising the API without external dependencies."""

import time
import uuid
from typing import Any, Dict, List, Optional


def echo(text: str, prefix: str = "") -> Dict[str, Any]:
    """Return the given text back to the caller."""
    return {"echo": f"{prefix}{text}"}


def add_numbers(numbers: List[float]) -> Dict[str, Any]:
    """Return the sum and count of the provided list of numbers."""
    return {"sum": sum(numbers), "count": len(numbers)}


def wait(seconds: float = 1.0) -> Dict[str, Any]:
    """Sleep for the requested number of seconds, then return a confirmation."""
    time.sleep(seconds)
    return {"slept_seconds": seconds}


def get_status() -> Dict[str, Any]:
    """Return a small status payload useful for health checks."""
    return {"status": "ok", "timestamp": time.time(), "request_id": str(uuid.uuid4())}
