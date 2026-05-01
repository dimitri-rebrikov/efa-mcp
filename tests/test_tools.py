import pytest
import asyncio
import re
from datetime import datetime, timedelta
from main import set_provider_url, list_providers, find_stop, departure_monitor, trip_request, get_provider_url


def validate_time_format(time_str: str, field_name: str):
    """Validate that a time string is in a reasonable format.

    EFA APIs typically return times in formats like:
    - ISO format: "2026-05-01T19:43:00Z"
    - Date-time: "2026-05-01 19:43:00"
    - Time only: "19:43"
    - Date only: "2026-05-01"
    """
    if not time_str or not isinstance(time_str, str):
        pytest.fail(f"{field_name} should be a non-empty string: {time_str}")

    # Check for common time patterns
    patterns = [
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$',  # ISO format with optional Z
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$',  # ISO with timezone offset
        r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$',  # Date-time with space
        r'^\d{2}:\d{2}$',  # Time only (HH:MM)
        r'^\d{4}-\d{2}-\d{2}$',  # Date only (YYYY-MM-DD)
        r'^\d{2}:\d{2}:\d{2}$',  # Time with seconds (HH:MM:SS)
    ]

    if not any(re.match(pattern, time_str) for pattern in patterns):
        # If it doesn't match common patterns, at least check it contains digits and time-like characters
        if not any(c.isdigit() for c in time_str):
            pytest.fail(f"{field_name} should contain digits: {time_str}")
        if not (':' in time_str or 'T' in time_str or '-' in time_str):
            pytest.fail(f"{field_name} should contain time/date separators (:, T, -): {time_str}")

# Test constants
TEST_PROVIDERS = [
    ("efa", "https://www.efa.de/efa/", "Stuttgart Hauptbahnhof", "Stuttgart Flughafen/Messe"),
    ("vvs", "https://www3.vvs.de/mngvvs/", "Stuttgart Hauptbahnhof", "Stuttgart Flughafen/Messe"),
]
TEST_PROVIDER_URL = "https://www.efa.de/efa/"  # For non-parametrized tests
NEW_TEST_PROVIDER_URL = "https://projekte.kvv-efa.de/sl3/"
TEST_STOP_ID = "de:08111:6118"  # Known Stuttgart Hbf ID
TEST_DEST_STOP_ID = "de:08111:6116"  # Known Stuttgart Airport ID


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
    # Provider is now returned as a string directly

    assert isinstance(provider_url, str)
    assert provider_url.startswith("http")
    assert provider_url == TEST_PROVIDER_URL


@pytest.mark.asyncio
async def test_provider_change_reflected_in_resource():
    """Test that setting provider updates the resource."""
    # Set new provider
    await set_provider_url(NEW_TEST_PROVIDER_URL)

    provider_url = await get_provider_url()
    # Provider is now returned as a string directly

    assert isinstance(provider_url, str)
    assert provider_url == NEW_TEST_PROVIDER_URL


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_departure_monitor(provider_name, provider_url, stop_name, dest_stop_name):
    """Test getting departures from a stop."""
    # Set provider and find stop first
    await set_provider_url(provider_url)

    try:
        stop = await find_stop(stop_name)
        assert stop["id"]

        # Get departures
        departures = await departure_monitor(stop["id"])
        assert isinstance(departures, list)

        # Check structure of any returned departures
        if len(departures) > 0:
            dep = departures[0]
            assert isinstance(dep, dict)
            assert "planned_time" in dep and isinstance(dep["planned_time"], str)
            assert "type" in dep and isinstance(dep["type"], str)
            assert "number" in dep and isinstance(dep["number"], str)
            assert "direction" in dep and isinstance(dep["direction"], str)

            # Check content quality
            assert len(dep["type"]) > 0
            assert len(dep["number"]) > 0
            assert len(dep["direction"]) > 0

            # Check time format - should be valid time-like string
            if dep["planned_time"]:
                validate_time_format(dep["planned_time"], "planned_time")
            if dep.get("estimated_time") and dep["estimated_time"]:
                validate_time_format(dep["estimated_time"], "estimated_time")

    except Exception as e:
        # Skip test if API is not reachable
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_departure_monitor_with_time(provider_name, provider_url, stop_name, dest_stop_name):
    """Test departures with specific time."""
    await set_provider_url(provider_url)

    try:
        stop = await find_stop(stop_name)

        # Time 1 hour from now
        future_time = (datetime.now() + timedelta(hours=1)).isoformat()
        departures = await departure_monitor(stop["id"], future_time, 5)

        assert isinstance(departures, list)
        assert len(departures) <= 5

        # If we got results, check their structure
        for dep in departures:
            assert isinstance(dep, dict)
            assert "planned_time" in dep
            assert "type" in dep
            assert "number" in dep
            assert "direction" in dep

    except Exception as e:
        # Skip test if API is not reachable
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_trip_request(provider_name, provider_url, stop_name, dest_stop_name):
    """Test trip planning between stops."""
    await set_provider_url(provider_url)

    try:
        origin_stop = await find_stop(stop_name)
        dest_stop = await find_stop(dest_stop_name)

        connections = await trip_request(origin_stop["id"], dest_stop["id"])
        assert isinstance(connections, list)

        # If we got results, check their structure
        if len(connections) > 0:
            connection = connections[0]
            assert isinstance(connection, dict)
            assert "legs" in connection
            assert isinstance(connection["legs"], list)
            assert len(connection["legs"]) > 0

            for leg in connection["legs"]:
                assert isinstance(leg, dict)
                assert "type" in leg and (isinstance(leg["type"], str) or isinstance(leg["type"], int))
                assert "number" in leg and isinstance(leg["number"], str)
                assert "direction" in leg and isinstance(leg["direction"], str)
                assert "departure_station" in leg and isinstance(leg["departure_station"], str)
                assert "planned_departure_time" in leg and isinstance(leg["planned_departure_time"], str)

                # Check content quality
                type_str = str(leg["type"])
                assert len(type_str) > 0
                assert len(leg["number"]) > 0
                assert len(leg["direction"]) > 0
                assert len(leg["departure_station"]) > 0

                # Check time formats - should be valid time-like strings
                if leg["planned_departure_time"]:
                    validate_time_format(leg["planned_departure_time"], "planned_departure_time")
                if leg.get("estimated_departure_time") and leg["estimated_departure_time"]:
                    validate_time_format(leg["estimated_departure_time"], "estimated_departure_time")
                if leg.get("planned_arrival_time") and leg["planned_arrival_time"]:
                    validate_time_format(leg["planned_arrival_time"], "planned_arrival_time")
                if leg.get("estimated_arrival_time") and leg["estimated_arrival_time"]:
                    validate_time_format(leg["estimated_arrival_time"], "estimated_arrival_time")

    except Exception as e:
        # Treat connection errors as test failures (not skips)
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise


@pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
@pytest.mark.asyncio
async def test_trip_request_with_time(provider_name, provider_url, stop_name, dest_stop_name):
    """Test trip request with specific departure time."""
    await set_provider_url(provider_url)

    try:
        origin_stop = await find_stop(stop_name)
        dest_stop = await find_stop(dest_stop_name)

        future_time = (datetime.now() + timedelta(hours=2)).isoformat()

        connections = await trip_request(origin_stop["id"], dest_stop["id"], future_time, False)
        assert isinstance(connections, list)

    except Exception as e:
        # Treat connection errors as test failures (not skips)
        if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
            pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
        else:
            raise
