import pytest
import asyncio
import re
from datetime import datetime, timedelta
from main import set_provider_url, list_providers, find_stop, departure_monitor, trip_request, get_provider_url


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


def validate_departure(dep: dict, allow_estimated_none: bool = True):
    """Validate a single departure entry has all required fields with proper types."""
    assert isinstance(dep, dict), f"Departure should be a dict, got {type(dep)}"

    # Required fields
    assert "planned_time" in dep, "Missing planned_time"
    assert isinstance(dep["planned_time"], str), f"planned_time should be str, got {type(dep['planned_time'])}"
    assert len(dep["planned_time"]) > 0, "planned_time should not be empty"
    validate_time_format(dep["planned_time"], "planned_time")

    assert "type" in dep, "Missing type"
    assert isinstance(dep["type"], (str, int)), f"type should be str or int, got {type(dep['type'])}"
    assert len(str(dep["type"])) > 0, "type should not be empty"

    assert "number" in dep, "Missing number"
    assert isinstance(dep["number"], str), f"number should be str, got {type(dep['number'])}"
    assert len(dep["number"]) > 0, "number should not be empty"

    assert "direction" in dep, "Missing direction"
    assert isinstance(dep["direction"], str), f"direction should be str, got {type(dep['direction'])}"
    assert len(dep["direction"]) > 0, "direction should not be empty"

    # Optional estimated_time
    assert "estimated_time" in dep, "Missing estimated_time"
    if dep["estimated_time"] is not None:
        assert isinstance(dep["estimated_time"], str), f"estimated_time should be str or None, got {type(dep['estimated_time'])}"
        assert len(dep["estimated_time"]) > 0, "estimated_time should not be empty if present"
        validate_time_format(dep["estimated_time"], "estimated_time")


def validate_leg(leg: dict):
    """Validate a single trip leg has all required fields with proper types.

    Walking legs (type 99) may have empty number and direction fields.
    """
    assert isinstance(leg, dict), f"Leg should be a dict, got {type(leg)}"

    leg_type = leg.get("type", "")
    is_walking = (isinstance(leg_type, int) and leg_type == 99) or (isinstance(leg_type, str) and leg_type == "99")

    # Required fields
    assert "type" in leg, "Missing type"
    assert isinstance(leg["type"], (str, int)), f"type should be str or int, got {type(leg['type'])}"
    assert len(str(leg["type"])) > 0, "type should not be empty"

    assert "number" in leg, "Missing number"
    assert isinstance(leg["number"], str), f"number should be str, got {type(leg['number'])}"
    if not is_walking:
        assert len(leg["number"]) > 0, f"number should not be empty for non-walking leg (type={leg_type})"

    assert "direction" in leg, "Missing direction"
    assert isinstance(leg["direction"], str), f"direction should be str, got {type(leg['direction'])}"
    if not is_walking:
        assert len(leg["direction"]) > 0, f"direction should not be empty for non-walking leg (type={leg_type})"

    assert "departure_station" in leg, "Missing departure_station"
    assert isinstance(leg["departure_station"], str), f"departure_station should be str, got {type(leg['departure_station'])}"
    assert len(leg["departure_station"]) > 0, "departure_station should not be empty"

    assert "planned_departure_time" in leg, "Missing planned_departure_time"
    assert isinstance(leg["planned_departure_time"], str), f"planned_departure_time should be str, got {type(leg['planned_departure_time'])}"
    assert len(leg["planned_departure_time"]) > 0, "planned_departure_time should not be empty"
    validate_time_format(leg["planned_departure_time"], "planned_departure_time")

    assert "arrival_station" in leg, "Missing arrival_station"
    assert isinstance(leg["arrival_station"], str), f"arrival_station should be str, got {type(leg['arrival_station'])}"
    assert len(leg["arrival_station"]) > 0, "arrival_station should not be empty"

    assert "planned_arrival_time" in leg, "Missing planned_arrival_time"
    assert isinstance(leg["planned_arrival_time"], str), f"planned_arrival_time should be str, got {type(leg['planned_arrival_time'])}"
    assert len(leg["planned_arrival_time"]) > 0, "planned_arrival_time should not be empty"
    validate_time_format(leg["planned_arrival_time"], "planned_arrival_time")

    # Optional estimated times
    for field in ["estimated_departure_time", "estimated_arrival_time"]:
        assert field in leg, f"Missing {field}"
        if leg[field] is not None:
            assert isinstance(leg[field], str), f"{field} should be str or None, got {type(leg[field])}"
            assert len(leg[field]) > 0, f"{field} should not be empty if present"
            validate_time_format(leg[field], field)


# Test constants
TEST_PROVIDERS = [
    ("efa", "https://www.efa.de/efa/", "Stuttgart Hauptbahnhof", "Stuttgart Flughafen/Messe"),
    ("vvs", "https://www3.vvs.de/mngvvs/", "Stuttgart Hauptbahnhof", "Stuttgart Flughafen/Messe"),
]
TEST_PROVIDERS_MULTI_LEG = [
    ("efa", "https://www.efa.de/efa/", "Stuttgart Hauptbahnhof", "Stuttgart Ressestrasse"),
    ("vvs", "https://www3.vvs.de/mngvvs/", "Stuttgart Hauptbahnhof", "Stuttgart Ressestrasse"),
]
TEST_PROVIDER_URL = "https://www.efa.de/efa/"  # For non-parametrized tests
NEW_TEST_PROVIDER_URL = "https://projekte.kvv-efa.de/sl3/"


@pytest.mark.asyncio
async def test_set_provider_url():
    """Test setting a provider URL."""
    result = await set_provider_url(TEST_PROVIDER_URL)
    assert result == TEST_PROVIDER_URL


@pytest.mark.asyncio
async def test_list_providers():
    """Test listing providers from GitHub."""
    try:
        providers = await list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

        # Check structure and content
        provider = providers[0]
        assert "name" in provider and isinstance(provider["name"], str)
        assert "url" in provider and isinstance(provider["url"], str)
        assert "country" in provider and isinstance(provider["country"], str)
        assert provider["name"]  # Not empty
        if provider["url"]:  # Only check URL format if it's not empty
            assert provider["url"].startswith("http")  # Valid URL

    except Exception as e:
        # Skip test if GitHub API is rate limited or unreachable
        if "403" in str(e) or "rate limit" in str(e).lower() or "ConnectError" in str(type(e)):
            pytest.skip(f"GitHub API not accessible: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_find_stop(provider_name, provider_url, stop_name, dest_stop_name):
    """Test finding a stop."""
    # Set provider first
    await set_provider_url(provider_url)

    try:
        result = await find_stop(stop_name)
        assert isinstance(result, dict)
        assert "name" in result and isinstance(result["name"], str)
        assert "id" in result and isinstance(result["id"], str)

        # Check content quality
        assert len(result["name"]) > 0
        assert len(result["id"]) > 0
        assert "Stuttgart" in result["name"]  # Should contain search term
        assert ":" in result["id"]  # EFA IDs have colon format

    except Exception as e:
        # Skip test if API is not reachable
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.asyncio
async def test_current_provider_resource():
    """Test getting current provider resource."""
    # Set a known provider first
    await set_provider_url(TEST_PROVIDER_URL)

    provider_url = await get_provider_url()

    assert isinstance(provider_url, str)
    assert provider_url.startswith("http")
    assert provider_url == TEST_PROVIDER_URL


@pytest.mark.asyncio
async def test_provider_change_reflected_in_resource():
    """Test that setting provider updates the resource."""
    # Set new provider
    await set_provider_url(NEW_TEST_PROVIDER_URL)

    provider_url = await get_provider_url()

    assert isinstance(provider_url, str)
    assert provider_url == NEW_TEST_PROVIDER_URL


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_departure_monitor(provider_name, provider_url, stop_name, dest_stop_name):
    """Test getting departures from a stop.

    Uses Stuttgart Hauptbahnhof which is a major station and should always have departures.
    """
    # Set provider and find stop first
    await set_provider_url(provider_url)

    try:
        stop = await find_stop(stop_name)
        assert stop["id"]

        # Get departures - Stuttgart Hbf should always have departures
        departures = await departure_monitor(stop["id"])
        assert isinstance(departures, list)
        assert len(departures) > 0, f"Expected at least 1 departure from {stop['name']}, got 0"

        # Validate every departure has all required fields
        for dep in departures:
            validate_departure(dep)

    except Exception as e:
        # Skip test if API is not reachable
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_departure_monitor_with_time(provider_name, provider_url, stop_name, dest_stop_name):
    """Test departures with specific time.

    Uses tomorrow 10:00 which should have departures at any major station.
    """
    await set_provider_url(provider_url)

    try:
        stop = await find_stop(stop_name)

        # Use tomorrow 10:00 - a time that should have departures
        tomorrow = datetime.now() + timedelta(days=1)
        time_str = tomorrow.strftime('%Y-%m-%d') + 'T10:00:00'
        departures = await departure_monitor(stop["id"], time_str, 5)

        assert isinstance(departures, list)
        assert len(departures) > 0, f"Expected at least 1 departure at {time_str} from {stop['name']}, got 0"
        assert len(departures) <= 5

        # Validate every departure has all required fields
        for dep in departures:
            validate_departure(dep)

    except Exception as e:
        # Skip test if API is not reachable
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_trip_request(provider_name, provider_url, stop_name, dest_stop_name):
    """Test trip planning between stops.

    Uses Stuttgart Hauptbahnhof -> Stuttgart Flughafen/Messe which should always have connections.
    """
    await set_provider_url(provider_url)

    try:
        origin_stop = await find_stop(stop_name)
        dest_stop = await find_stop(dest_stop_name)

        connections = await trip_request(origin_stop["id"], dest_stop["id"])
        assert isinstance(connections, list)
        assert len(connections) > 0, f"Expected at least 1 connection from {stop_name} to {dest_stop_name}, got 0"

        # Validate every connection
        for connection in connections:
            assert isinstance(connection, dict)
            assert "legs" in connection
            assert isinstance(connection["legs"], list)
            assert len(connection["legs"]) > 0, "Each connection should have at least 1 leg"

            for leg in connection["legs"]:
                validate_leg(leg)

    except Exception as e:
        # Treat connection errors as test failures (not skips)
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS_MULTI_LEG)
@pytest.mark.asyncio
async def test_trip_request_multi_leg(provider_name, provider_url, stop_name, dest_stop_name):
    """Test trip planning with multiple legs.

    Uses Stuttgart Hauptbahnhof -> Stuttgart Ressestraße which requires
    changing transport (e.g. U-Bahn + Bus) and should produce multi-leg connections.
    """
    await set_provider_url(provider_url)

    try:
        origin_stop = await find_stop(stop_name)
        dest_stop = await find_stop(dest_stop_name)

        connections = await trip_request(origin_stop["id"], dest_stop["id"])
        assert isinstance(connections, list)
        assert len(connections) > 0, f"Expected at least 1 connection from {stop_name} to {dest_stop_name}, got 0"

        # At least one connection should have multiple legs (changing transport)
        has_multi_leg = any(len(c["legs"]) > 1 for c in connections)
        assert has_multi_leg, f"Expected at least one multi-leg connection from {stop_name} to {dest_stop_name}, all connections have single leg"

        # Validate every connection
        for connection in connections:
            assert isinstance(connection, dict)
            assert "legs" in connection
            assert isinstance(connection["legs"], list)
            assert len(connection["legs"]) > 0, "Each connection should have at least 1 leg"

            for leg in connection["legs"]:
                validate_leg(leg)

    except Exception as e:
        # Treat connection errors as test failures (not skips)
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_trip_request_with_time(provider_name, provider_url, stop_name, dest_stop_name):
    """Test trip request with specific departure time.

    Uses tomorrow 10:00 which should have connections between major stops.
    """
    await set_provider_url(provider_url)

    try:
        origin_stop = await find_stop(stop_name)
        dest_stop = await find_stop(dest_stop_name)

        # Use tomorrow 10:00 - a time that should have connections
        tomorrow = datetime.now() + timedelta(days=1)
        time_str = tomorrow.strftime('%Y-%m-%d') + 'T10:00:00'

        connections = await trip_request(origin_stop["id"], dest_stop["id"], time_str, False)
        assert isinstance(connections, list)
        assert len(connections) > 0, f"Expected at least 1 connection at {time_str} from {stop_name} to {dest_stop_name}, got 0"

        # Validate every connection
        for connection in connections:
            assert isinstance(connection, dict)
            assert "legs" in connection
            assert isinstance(connection["legs"], list)
            assert len(connection["legs"]) > 0, "Each connection should have at least 1 leg"

            for leg in connection["legs"]:
                validate_leg(leg)

    except Exception as e:
        # Treat connection errors as test failures (not skips)
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise