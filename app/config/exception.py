"""
Global exception handler.

WHY THIS EXISTS (framework-agnostic concept):
----------------------------------------------
Every production backend needs a "last resort" error boundary.
If an exception escapes your route handler AND your middleware's try/except,
this catches it and returns a clean JSON error instead of leaking a raw
stack trace to the client (which is both ugly and a security risk).

The key difference from your original:
- logger.error(str(exc)) → loses the traceback (file, line, call stack)
- logger.exception(msg)  → automatically captures the FULL traceback

This one-word change is the difference between debugging in 30 seconds vs 3 hours.
"""

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


async def global_exception_handler(request: Request, exc: Exception):
    # logger.exception() does TWO things:
    # 1. Logs at ERROR level
    # 2. Automatically attaches exc_info (the full traceback) to the log entry
    #
    # Because middleware already bound request_id via contextvars,
    # this log line will AUTOMATICALLY include the request_id.
    # You don't need to pass it or look it up.
    logger.exception(
        "unhandled_server_error",
        error_type=exc.__class__.__name__,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )
