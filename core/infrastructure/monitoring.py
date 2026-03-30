"""Monitoring and observability setup."""

import logging
import time
from typing import Callable
from functools import wraps
import json
from datetime import datetime

from fastapi import Request, Response
from fastapi.responses import JSONResponse


class StructuredLogger:
    """Structured logging with JSON output."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _format_log(self, level: str, message: str, **extras) -> dict:
        """Format log entry with structured data."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "logger": self.logger.name,
            **extras,
        }

    def debug(self, message: str, **extras):
        """Log debug message."""
        log_entry = self._format_log("DEBUG", message, **extras)
        self.logger.debug(json.dumps(log_entry))

    def info(self, message: str, **extras):
        """Log info message."""
        log_entry = self._format_log("INFO", message, **extras)
        self.logger.info(json.dumps(log_entry))

    def warning(self, message: str, **extras):
        """Log warning message."""
        log_entry = self._format_log("WARNING", message, **extras)
        self.logger.warning(json.dumps(log_entry))

    def error(self, message: str, **extras):
        """Log error message."""
        log_entry = self._format_log("ERROR", message, **extras)
        self.logger.error(json.dumps(log_entry))

    def critical(self, message: str, **extras):
        """Log critical message."""
        log_entry = self._format_log("CRITICAL", message, **extras)
        self.logger.critical(json.dumps(log_entry))


class PerformanceMonitor:
    """Monitor and record performance metrics."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.metrics = {}

    def record_metric(self, name: str, value: float, unit: str = ""):
        """Record a performance metric."""
        self.metrics[name] = {"value": value, "unit": unit}
        self.logger.info(
            f"Metric recorded: {name}",
            metric_name=name,
            metric_value=value,
            metric_unit=unit,
        )

    def timing(self, operation_name: str) -> Callable:
        """Decorator to measure operation timing."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    self.record_metric(f"{operation_name}_duration", elapsed, "seconds")
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    self.logger.error(
                        f"Operation failed: {operation_name}",
                        operation=operation_name,
                        duration=elapsed,
                        error=str(e),
                    )
                    raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    self.record_metric(f"{operation_name}_duration", elapsed, "seconds")
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    self.logger.error(
                        f"Operation failed: {operation_name}",
                        operation=operation_name,
                        duration=elapsed,
                        error=str(e),
                    )
                    raise

            return async_wrapper if callable(getattr(func, "__await__", None)) else sync_wrapper

        return decorator


class RequestLoggingMiddleware:
    """Middleware for request/response logging."""

    def __init__(self, app):
        self.app = app
        self.logger = StructuredLogger(__name__)

    async def __call__(self, request: Request, call_next) -> Response:
        """Log request and response."""
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", str(time.time()))

        # Log request
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.url.query),
            client=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            self.logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=process_time,
            )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            process_time = time.time() - start_time
            self.logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration=process_time,
                error=str(e),
            )
            raise


class MetricsCollector:
    """Collect application metrics."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.request_count = 0
        self.request_errors = 0
        self.total_request_time = 0

    def record_request(self, duration: float, status_code: int):
        """Record request metrics."""
        self.request_count += 1
        self.total_request_time += duration

        if status_code >= 400:
            self.request_errors += 1

    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_time = (
            self.total_request_time / self.request_count
            if self.request_count > 0
            else 0
        )

        return {
            "total_requests": self.request_count,
            "total_errors": self.request_errors,
            "error_rate": (
                self.request_errors / self.request_count
                if self.request_count > 0
                else 0
            ),
            "average_response_time": avg_time,
        }


# Global instances
logger = StructuredLogger("app")
monitor = PerformanceMonitor()
metrics = MetricsCollector()
