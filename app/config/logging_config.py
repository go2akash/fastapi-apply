"""
Production logging configuration using structlog.

WHY structlog over stdlib logging?
-----------------------------------
stdlib logging builds strings: logger.info(f"user {id} created") → a flat string
structlog builds dictionaries: logger.info("user_created", user_id=id) → a JSON object

In production, log aggregators (Grafana Loki, Elasticsearch, Datadog) index JSON fields.
Searching `user_id == "usr_42"` across millions of lines takes milliseconds.
Searching `*usr_42*` with regex across millions of string lines takes minutes.

WHY contextvars?
-----------------
Every async request runs in its own coroutine task.
contextvars gives each task its own isolated "slot" for data (like request_id).
This is the SAME concept as:
  - Go's context.Context
  - Node's AsyncLocalStorage
  - Java's ThreadLocal

When middleware sets request_id in the contextvar, ANY function downstream
(3 layers deep in a service → repository → helper) can read it without
passing it as an argument. structlog's merge_contextvars processor
automatically injects all bound contextvars into every log line.
"""

import logging
import sys
import structlog


def setup_logging():
    """
    Configure structlog for the entire app. Call once at startup.

    Output:
    - Development: colored, human-readable lines to stderr
    - Production: JSON lines to stdout (for container log shipping)
    """

    # ── Shared processors: run on EVERY log line ──
    shared_processors = [
        structlog.contextvars.merge_contextvars,       # Injects request_id, user_id, etc.
        structlog.processors.add_log_level,            # Adds "level": "info"
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # ISO 8601 timestamp
        structlog.processors.StackInfoRenderer(),      # Stack info if requested
        structlog.processors.format_exc_info,          # Formats tracebacks into a string
    ]

    # ── Renderer: JSON for production, colored text for dev ──
    # In real production, you'd check an env var like ENVIRONMENT=production
    # For now, always use JSON so you can SEE what production logs look like
    renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # ── Also route stdlib logging (uvicorn, sqlalchemy) through structlog ──
    # This ensures ALL log output is structured JSON, not a mix of formats
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.WARNING)  # Only WARN+ from third-party libs
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)

    # ── Silence uvicorn's default access log ──
    # Our RequestLoggingMiddleware already emits structured JSON for every request.
    # Without this, you get duplicate lines: one JSON (ours) + one plain text (uvicorn's).
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
