"""Custom exceptions for the EFA library."""


class EFAError(Exception):
    """Base exception for all EFA library errors."""


class EFAConnectionError(EFAError):
    """Raised when the EFA API is unreachable or returns a connection error."""


class EFAAPIError(EFAError):
    """Raised when the EFA API returns an error message."""


class EFAStopNotFoundError(EFAError):
    """Raised when no stop is found for the given search term."""
