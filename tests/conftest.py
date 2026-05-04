"""Shared test fixtures and configuration."""

import re
import pytest

# Test constants
TEST_PROVIDERS = [
    ("efa", "https://www.efa.de/efa/", "Stuttgart Hauptbahnhof", "Stuttgart Flughafen/Messe"),
    ("vvs", "https://www3.vvs.de/mngvvs/", "Stuttgart Hauptbahnhof", "Stuttgart Flughafen/Messe"),
]

TEST_PROVIDERS_MULTI_LEG = [
    ("efa", "https://www.efa.de/efa/", "Stuttgart Hauptbahnhof", "Stuttgart Ressestrasse"),
    ("vvs", "https://www3.vvs.de/mngvvs/", "Stuttgart Hauptbahnhof", "Stuttgart Ressestrasse"),
]

TEST_PROVIDER_URL = "https://www.efa.de/efa/"
NEW_TEST_PROVIDER_URL = "https://projekte.kvv-efa.de/sl3/"


def validate_time_format(time_str: str, field_name: str):
    """Validate that a time string is in ISO 8601 format as returned by EFA APIs.

    EFA APIs return times in ISO 8601 format like "2026-05-01T19:43:00Z".
    """
    if not time_str or not isinstance(time_str, str):
        pytest.fail(f"{field_name} should be a non-empty string: {time_str}")

    # EFA returns ISO 8601 with optional Z suffix or timezone offset
    patterns = [
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$',  # ISO format with optional Z
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$',  # ISO with timezone offset
    ]

    if not any(re.match(pattern, time_str) for pattern in patterns):
        pytest.fail(f"{field_name} should be ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ), got: {time_str}")


def validate_departure(dep, allow_estimated_none: bool = True):
    """Validate a single departure entry has all required fields with proper types."""
    # Required fields
    assert dep.planned_time, "planned_time should not be empty"
    validate_time_format(dep.planned_time, "planned_time")

    assert dep.type, "type should not be empty"

    assert dep.number, "number should not be empty"

    assert dep.direction, "direction should not be empty"

    # Optional estimated_time
    if dep.estimated_time is not None:
        assert dep.estimated_time, "estimated_time should not be empty if present"
        validate_time_format(dep.estimated_time, "estimated_time")


def validate_leg(leg):
    """Validate a single trip leg has all required fields with proper types.

    Walking legs (type 99) may have empty number and direction fields.
    """
    leg_type = leg.type
    is_walking = leg_type == "99"

    assert leg.type, "type should not be empty"

    if not is_walking:
        assert leg.number, f"number should not be empty for non-walking leg (type={leg_type})"

    if not is_walking:
        assert leg.direction, f"direction should not be empty for non-walking leg (type={leg_type})"

    assert leg.departure_station, "departure_station should not be empty"
    assert leg.planned_departure_time, "planned_departure_time should not be empty"
    validate_time_format(leg.planned_departure_time, "planned_departure_time")

    assert leg.arrival_station, "arrival_station should not be empty"
    assert leg.planned_arrival_time, "planned_arrival_time should not be empty"
    validate_time_format(leg.planned_arrival_time, "planned_arrival_time")

    # Optional estimated times
    for field in ["estimated_departure_time", "estimated_arrival_time"]:
        val = getattr(leg, field)
        if val is not None:
            assert val, f"{field} should not be empty if present"
            validate_time_format(val, field)
