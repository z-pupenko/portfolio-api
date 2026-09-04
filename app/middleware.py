import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

request_logger = logging.getLogger("portfolio_api.requests")
HEALTH_CHECK_PATHS = frozenset(
    {
        "/health/live",
        "/health/ready",
    }
)


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        request_logger.exception(
            "HTTP request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": _elapsed_milliseconds(started_at),
            },
        )
        raise

    response.headers["X-Request-ID"] = request_id
    request_logger.log(
        _log_level_for_response(
            request.url.path,
            response.status_code,
        ),
        "HTTP request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": _elapsed_milliseconds(started_at),
        },
    )
    return response


def _elapsed_milliseconds(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1_000, 2)


def _log_level_for_status(status_code: int) -> int:
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    return logging.INFO


def _log_level_for_response(path: str, status_code: int) -> int:
    if path in HEALTH_CHECK_PATHS and status_code < 400:
        return logging.DEBUG
    return _log_level_for_status(status_code)
