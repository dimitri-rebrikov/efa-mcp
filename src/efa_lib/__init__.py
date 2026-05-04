"""EFA transit API library - core library for querying EFA transit APIs."""

from efa_lib.client import EFAClient, set_default_provider, get_default_provider
from efa_lib.models import (
    Stop,
    Departure,
    TripLeg,
    TripConnection,
    Provider,
)
from efa_lib.exceptions import (
    EFAError,
    EFAConnectionError,
    EFAAPIError,
    EFAStopNotFoundError,
)

__all__ = [
    "EFAClient",
    "set_default_provider",
    "get_default_provider",
    "Stop",
    "Departure",
    "TripLeg",
    "TripConnection",
    "Provider",
    "EFAError",
    "EFAConnectionError",
    "EFAAPIError",
    "EFAStopNotFoundError",
]
