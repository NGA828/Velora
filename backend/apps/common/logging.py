import logging


class RequestIDFallbackFilter(logging.Filter):
    """Ensure formatters can safely render records created outside request handling."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True
