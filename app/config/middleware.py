"""
Production request logging middleware.

WHAT THIS DOES (the framework-agnostic concept):
-------------------------------------------------
Every HTTP request enters your application through a single door (the socket).
Middleware wraps that door — it runs BEFORE your route handler and AFTER.

This middleware does 3 things that EVERY production backend needs:

1. CORRELATION ID (request_id):
   Generates a UUID and binds it to the current async task's contextvars.
   Every log line downstream — in routes, services, DB calls — automatically
   includes this ID. When a user says "my request failed", you search by
   this single ID and see the ENTIRE request timeline.

   Framework-agnostic equivalent:
   - Go: set value in context.Context, pass via r.Context()
   - Node: set in AsyncLocalStorage, available in all callbacks
   - Java: set in MDC (Mapped Diagnostic Context)

2. LATENCY MEASUREMENT:
   Uses time.perf_counter() (monotonic clock — never jumps backward due to
   NTP sync, unlike time.time()). Measures wall-clock processing time in ms.

3. ACCESS LOG:
   One structured JSON line per request with method, path, status, duration.
   This is equivalent to nginx access logs but with your correlation ID attached.

WHY BaseHTTPMiddleware?
------------------------
It's Starlette's (the ASGI toolkit under FastAPI) convenience wrapper.
Under the hood, it's just: receive bytes → run your code → send bytes.
The same concept as Express's (req, res, next) => {} or Go's http.Handler wrapper.
"""

import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # ── 1. Clear any leftover context from previous request on this task ──
        structlog.contextvars.clear_contextvars()

        # ── 2. Create or inherit correlation ID ──
        # If an upstream load balancer/gateway already set X-Request-ID, reuse it.
        # Otherwise generate a new one. This is how distributed tracing works.
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # ── 3. Bind context for ALL downstream log calls ──
        # After this line, every logger.info(), logger.error(), etc. in ANY file
        # will automatically include request_id, path, method, client_ip.
        # No argument passing needed — contextvars handles it.
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        # ── 4. Measure latency with monotonic clock ──
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            # ── 5. Emit structured access log ──
            logger.info(
                "http_request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # ── 6. Return request_id to client ──
            # Users can quote this in bug reports: "My request X-Request-ID: abc-123 failed"
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000

            # logger.exception() automatically captures the FULL traceback
            # into the structured JSON — file, line number, call stack, everything.
            logger.exception(
                "http_request_unhandled_exception",
                duration_ms=round(duration_ms, 2),
                error_type=exc.__class__.__name__,
            )

            response = Response("Internal Server Error", status_code=500)
            response.headers["X-Request-ID"] = request_id
            return response
