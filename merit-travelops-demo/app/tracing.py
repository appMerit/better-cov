"""OpenTelemetry tracing utilities for TravelOps Assistant."""

from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

# Get tracer
tracer = trace.get_tracer("travelops", "0.1.0")


@contextmanager
def trace_operation(name: str, attributes: dict[str, Any] | None = None):
    """Context manager for tracing operations."""
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(key, value)
                elif isinstance(value, list):
                    span.set_attribute(key, str(value))
                else:
                    span.set_attribute(key, str(value))
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def set_span_attributes(span: Span, attributes: dict[str, Any]) -> None:
    """Set multiple attributes on a span."""
    for key, value in attributes.items():
        if isinstance(value, (str, int, float, bool)):
            span.set_attribute(key, value)
        elif isinstance(value, list):
            span.set_attribute(key, str(value))
        else:
            span.set_attribute(key, str(value))
