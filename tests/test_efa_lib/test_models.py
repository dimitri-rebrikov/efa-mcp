"""Tests for Pydantic model validation."""

import pytest
from efa_lib.models import Stop, Departure, TripLeg, TripConnection, Provider


class TestStop:
    def test_valid_stop(self):
        stop = Stop(name="Stuttgart Hauptbahnhof", id="de:08111:1")
        assert stop.name == "Stuttgart Hauptbahnhof"
        assert stop.id == "de:08111:1"

    def test_stop_serialization(self):
        stop = Stop(name="Test", id="123")
        data = stop.model_dump()
        assert data == {"name": "Test", "id": "123"}

    def test_stop_empty_name_allowed(self):
        """Pydantic allows empty strings by default (no min_length constraint)."""
        stop = Stop(name="", id="123")
        assert stop.name == ""
        assert stop.id == "123"


class TestDeparture:
    def test_valid_departure(self):
        dep = Departure(
            planned_time="2026-05-01T19:43:00Z",
            estimated_time="2026-05-01T19:45:00Z",
            type="0",
            number="S1",
            direction="Stuttgart",
        )
        assert dep.planned_time == "2026-05-01T19:43:00Z"
        assert dep.estimated_time == "2026-05-01T19:45:00Z"

    def test_departure_without_estimated(self):
        dep = Departure(
            planned_time="2026-05-01T19:43:00Z",
            type="0",
            number="S1",
            direction="Stuttgart",
        )
        assert dep.estimated_time is None

    def test_departure_serialization(self):
        dep = Departure(
            planned_time="2026-05-01T19:43:00Z",
            type="0",
            number="S1",
            direction="Stuttgart",
        )
        data = dep.model_dump()
        assert data["planned_time"] == "2026-05-01T19:43:00Z"
        assert data["estimated_time"] is None
        assert data["type"] == "0"
        assert data["number"] == "S1"
        assert data["direction"] == "Stuttgart"


class TestTripLeg:
    def test_valid_leg(self):
        leg = TripLeg(
            type="0",
            number="S1",
            direction="Stuttgart",
            departure_station="Stuttgart Hbf",
            planned_departure_time="2026-05-01T19:43:00Z",
            arrival_station="Stuttgart Flughafen",
            planned_arrival_time="2026-05-01T19:55:00Z",
        )
        assert leg.type == "0"
        assert leg.estimated_departure_time is None
        assert leg.estimated_arrival_time is None

    def test_leg_with_estimates(self):
        leg = TripLeg(
            type="0",
            number="S1",
            direction="Stuttgart",
            departure_station="Stuttgart Hbf",
            planned_departure_time="2026-05-01T19:43:00Z",
            estimated_departure_time="2026-05-01T19:45:00Z",
            arrival_station="Stuttgart Flughafen",
            planned_arrival_time="2026-05-01T19:55:00Z",
            estimated_arrival_time="2026-05-01T19:57:00Z",
        )
        assert leg.estimated_departure_time == "2026-05-01T19:45:00Z"
        assert leg.estimated_arrival_time == "2026-05-01T19:57:00Z"

    def test_leg_serialization(self):
        leg = TripLeg(
            type="0",
            number="S1",
            direction="Stuttgart",
            departure_station="Stuttgart Hbf",
            planned_departure_time="2026-05-01T19:43:00Z",
            arrival_station="Stuttgart Flughafen",
            planned_arrival_time="2026-05-01T19:55:00Z",
        )
        data = leg.model_dump()
        assert data["departure_station"] == "Stuttgart Hbf"
        assert data["estimated_departure_time"] is None


class TestTripConnection:
    def test_valid_connection(self):
        leg = TripLeg(
            type="0",
            number="S1",
            direction="Stuttgart",
            departure_station="Stuttgart Hbf",
            planned_departure_time="2026-05-01T19:43:00Z",
            arrival_station="Stuttgart Flughafen",
            planned_arrival_time="2026-05-01T19:55:00Z",
        )
        conn = TripConnection(legs=[leg])
        assert len(conn.legs) == 1
        assert conn.legs[0].number == "S1"

    def test_connection_serialization(self):
        leg = TripLeg(
            type="0",
            number="S1",
            direction="Stuttgart",
            departure_station="Stuttgart Hbf",
            planned_departure_time="2026-05-01T19:43:00Z",
            arrival_station="Stuttgart Flughafen",
            planned_arrival_time="2026-05-01T19:55:00Z",
        )
        conn = TripConnection(legs=[leg])
        data = conn.model_dump()
        assert len(data["legs"]) == 1
        assert data["legs"][0]["number"] == "S1"


class TestProvider:
    def test_valid_provider(self):
        provider = Provider(
            name="VVS",
            url="https://www3.vvs.de/mngvvs/",
            country="Germany",
            info={"source": "test"},
        )
        assert provider.name == "VVS"
        assert provider.country == "Germany"

    def test_provider_serialization(self):
        provider = Provider(
            name="Test",
            url="https://example.com/",
            country="DE",
            info={"key": "value"},
        )
        data = provider.model_dump()
        assert data["name"] == "Test"
        assert data["info"] == {"key": "value"}
