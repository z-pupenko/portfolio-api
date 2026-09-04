import json
import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter
from app.middleware import _log_level_for_response, _log_level_for_status


def test_json_formatter_includes_request_fields():
    record = logging.LogRecord(
        name="portfolio_api.requests",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="HTTP request completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.method = "GET"
    record.path = "/health/live"
    record.status_code = 200
    record.duration_ms = 12.5

    log_data = json.loads(JsonFormatter().format(record))

    assert log_data["level"] == "INFO"
    assert log_data["message"] == "HTTP request completed"
    assert log_data["request_id"] == "request-123"
    assert log_data["method"] == "GET"
    assert log_data["path"] == "/health/live"
    assert log_data["status_code"] == 200
    assert log_data["duration_ms"] == 12.5


def test_request_logging_adds_request_id_and_records_metadata(
    client: TestClient,
):
    with patch("app.middleware.request_logger") as request_logger:
        response = client.get("/")

    request_logger.log.assert_called_once()
    level, message = request_logger.log.call_args.args
    fields = request_logger.log.call_args.kwargs["extra"]

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == fields["request_id"]
    assert level == logging.INFO
    assert message == "HTTP request completed"
    assert fields["method"] == "GET"
    assert fields["path"] == "/"
    assert fields["status_code"] == 200
    assert fields["duration_ms"] >= 0
    assert set(fields) == {
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
    }


def test_request_logging_records_client_errors(client: TestClient):
    with patch("app.middleware.request_logger") as request_logger:
        response = client.get("/route-that-does-not-exist")

    level, message = request_logger.log.call_args.args
    fields = request_logger.log.call_args.kwargs["extra"]

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == fields["request_id"]
    assert level == logging.WARNING
    assert message == "HTTP request completed"
    assert fields["status_code"] == 404


def test_successful_health_checks_use_debug_level(client: TestClient):
    with patch("app.middleware.request_logger") as request_logger:
        response = client.get("/health/live")

    level, _message = request_logger.log.call_args.args

    assert response.status_code == 200
    assert level == logging.DEBUG


def test_failed_health_checks_keep_error_level():
    assert _log_level_for_response("/health/ready", 503) == logging.ERROR


@pytest.mark.parametrize(
    ("status_code", "expected_level"),
    [
        (200, logging.INFO),
        (404, logging.WARNING),
        (503, logging.ERROR),
    ],
)
def test_log_level_matches_response_status(
    status_code: int,
    expected_level: int,
):
    assert _log_level_for_status(status_code) == expected_level
