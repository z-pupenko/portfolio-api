import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field_name in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
        ):
            if hasattr(record, field_name):
                log_data[field_name] = getattr(record, field_name)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    application_logger = logging.getLogger("portfolio_api")
    application_logger.handlers.clear()
    application_logger.addHandler(handler)
    application_logger.setLevel(log_level)
    application_logger.propagate = False
