"""Pydantic models for EFA API data structures."""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class Stop(BaseModel):
    """A transit stop returned by the EFA stop finder."""

    name: str
    id: str


class Departure(BaseModel):
    """A single departure event from a stop."""

    planned_time: str
    estimated_time: Optional[str] = None
    type: str
    number: str
    direction: str


class TripLeg(BaseModel):
    """A single leg of a trip connection."""

    type: str
    number: str
    direction: str
    departure_station: str
    planned_departure_time: str
    estimated_departure_time: Optional[str] = None
    arrival_station: str
    planned_arrival_time: str
    estimated_arrival_time: Optional[str] = None


class TripConnection(BaseModel):
    """A complete trip connection consisting of one or more legs."""

    legs: list[TripLeg]


class Provider(BaseModel):
    """An EFA API provider from the public-transport/transport-apis repository."""

    name: str
    url: str
    country: str
    info: Dict[str, Any]
