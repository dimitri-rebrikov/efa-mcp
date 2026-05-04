"""Tests for the EFA MCP server.

These tests verify that the MCP server tools correctly delegate to the
EFA library and return properly formatted responses.
"""

import pytest
from datetime import datetime, timedelta

from efa_mcp.server import (
    get_provider_url,
    set_provider_url,
    list_providers,
    find_stop,
    departure_monitor,
    trip_request,
)
from tests.conftest import (
    TEST_PROVIDERS,
    TEST_PROVIDERS_MULTI_LEG,
    TEST_PROVIDER_URL,
    NEW_TEST_PROVIDER_URL,
    validate_time_format,
)


class TestProviderTools:
    @pytest.mark.asyncio
    async def test_get_provider_url(self):
        """Test getting provider URL via MCP tool."""
        url = await get_provider_url()
        assert isinstance(url, str)
        assert url.startswith("http")

    @pytest.mark.asyncio
    async def test_set_provider_url(self):
        """Test setting provider URL via MCP tool."""
        result = await set_provider_url(TEST_PROVIDER_URL)
        assert result == TEST_PROVIDER_URL

    @pytest.mark.asyncio
    async def test_provider_change_reflected(self):
        """Test that setting provider updates the resource."""
        await set_provider_url(NEW_TEST_PROVIDER_URL)
        url = await get_provider_url()
        assert url == NEW_TEST_PROVIDER_URL

        # Reset back
        await set_provider_url(TEST_PROVIDER_URL)


class TestListProvidersTool:
    @pytest.mark.asyncio
    async def test_list_providers(self):
        """Test listing providers via MCP tool."""
        try:
            providers = await list_providers()
            assert isinstance(providers, list)
            assert len(providers) > 0

            provider = providers[0]
            assert "name" in provider and isinstance(provider["name"], str)
            assert "url" in provider and isinstance(provider["url"], str)
            assert "country" in provider and isinstance(provider["country"], str)
            assert provider["name"]

        except Exception as e:
            if "403" in str(e) or "rate limit" in str(e).lower() or "ConnectError" in str(type(e)):
                pytest.skip(f"GitHub API not accessible: {e}")
            else:
                raise


class TestFindStopTool:
    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_find_stop(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test finding a stop via MCP tool."""
        await set_provider_url(provider_url)
        try:
            result = await find_stop(stop_name)
            assert isinstance(result, dict)
            assert "name" in result and isinstance(result["name"], str)
            assert "id" in result and isinstance(result["id"], str)
            assert len(result["name"]) > 0
            assert len(result["id"]) > 0
            assert "Stuttgart" in result["name"]
            assert ":" in result["id"]

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise


class TestDepartureMonitorTool:
    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_departure_monitor(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test getting departures via MCP tool."""
        await set_provider_url(provider_url)
        try:
            stop = await find_stop(stop_name)
            departures = await departure_monitor(stop["id"])
            assert isinstance(departures, list)
            assert len(departures) > 0

            for dep in departures:
                assert "planned_time" in dep
                assert "estimated_time" in dep
                assert "type" in dep
                assert "number" in dep
                assert "direction" in dep
                validate_time_format(dep["planned_time"], "planned_time")

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise

    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_departure_monitor_with_time(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test departures with time via MCP tool."""
        await set_provider_url(provider_url)
        try:
            stop = await find_stop(stop_name)
            tomorrow = datetime.now() + timedelta(days=1)
            time_str = tomorrow.strftime('%Y-%m-%d') + 'T10:00:00'
            departures = await departure_monitor(stop["id"], time_str, 5)

            assert isinstance(departures, list)
            assert len(departures) > 0
            assert len(departures) <= 5

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise


class TestTripRequestTool:
    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_trip_request(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test trip planning via MCP tool."""
        await set_provider_url(provider_url)
        try:
            origin = await find_stop(stop_name)
            dest = await find_stop(dest_stop_name)

            connections = await trip_request(origin["id"], dest["id"])
            assert isinstance(connections, list)
            assert len(connections) > 0

            for conn in connections:
                assert isinstance(conn, dict)
                assert "legs" in conn
                assert isinstance(conn["legs"], list)
                assert len(conn["legs"]) > 0

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise

    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS_MULTI_LEG)
    @pytest.mark.asyncio
    async def test_trip_request_multi_leg(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test multi-leg trip planning via MCP tool."""
        await set_provider_url(provider_url)
        try:
            origin = await find_stop(stop_name)
            dest = await find_stop(dest_stop_name)

            connections = await trip_request(origin["id"], dest["id"])
            assert isinstance(connections, list)
            assert len(connections) > 0

            has_multi_leg = any(len(c["legs"]) > 1 for c in connections)
            assert has_multi_leg

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise
