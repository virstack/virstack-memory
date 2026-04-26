"""Custom exception hierarchy for the Virstack Graphiti SDK.

All SDK-specific errors inherit from :class:`GraphitiError` so callers
can catch the base class for blanket handling.
"""

from __future__ import annotations


class GraphitiError(Exception):
    """Base exception for all Virstack Graphiti SDK errors."""


class GraphitiConnectionError(GraphitiError):
    """Raised when the HTTP connection to the Graphiti server fails.

    This typically wraps ``httpx.ConnectError`` or ``httpx.TimeoutException``.
    """

    def __init__(self, message: str = "Failed to connect to the Graphiti server") -> None:
        super().__init__(message)


class GraphitiAPIError(GraphitiError):
    """Raised when the Graphiti server returns a non-success HTTP status.

    Attributes:
        status_code: The HTTP status code from the response.
        detail: The response body or error detail string.
    """

    def __init__(self, status_code: int, detail: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Graphiti API error {status_code}: {detail}")


class GraphitiValidationError(GraphitiError):
    """Raised when the server returns a 422 Validation Error.

    This is a specialisation of :class:`GraphitiAPIError` for the common
    case where a Pydantic validation error is returned by the FastAPI backend.
    """

    def __init__(self, detail: str = "") -> None:
        self.status_code = 422
        self.detail = detail
        super().__init__(f"Graphiti validation error: {detail}")
