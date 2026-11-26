"""Errors from the FHIR access layer.

Messages carry resource types, ids and HTTP status codes only, never response bodies or
clinical values (no clinical content in logs or errors).
"""


class FhirError(Exception):
    """Base class for FHIR access errors."""


class ResourceNotFoundError(FhirError):
    """The requested resource does not exist: missing data, not a failed request."""


class FhirRequestError(FhirError):
    """A request failed. ``transient`` is true when retries were exhausted on a
    temporary failure (timeout, 429, 5xx)."""

    def __init__(self, message: str, *, status: int | None = None, transient: bool) -> None:
        super().__init__(message)
        self.status = status
        self.transient = transient
