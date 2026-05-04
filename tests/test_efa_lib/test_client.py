"""Integration tests for EFAClient against real EFA APIs."""

import pytest
from datetime import datetime, timedelta

from efa_lib import EFAClient, set_default_provider, get_default_provider
from efa_lib.exceptions import EFAConnectionError, EFAAPIError, EFAStopNotFoundError
from tests.conftest import (
    TEST_PROVIDERS,
    TEST_PROVIDERS_MULTI_LEG,
    TEST_PROVIDER_URL,
    NEW_TEST_PROVIDER_URL,
    validate_departure,
    validate_leg,
)


@pytest.fixture
def client():
    """Create a fresh EFAClient for each test."""
    return EFAClient(base_url=TEST_PROVIDER_URL)


class TestProviderManagement:
    @pytest.mark.asyncio
    async def test_default_provider_url(self):
        """Test the default provider URL."""
        url = get_default_provider()
        assert url.startswith("http")

    @pytest.mark.asyncio
    async def test_set_default_provider(self):
        """Test setting the default provider URL."""
        result = set_default_provider(TEST_PROVIDER_URL)
        assert result == TEST_PROVIDER_URL
        assert get_default_provider() == TEST_PROVIDER_URL

    @pytest.mark.asyncio
    async def test_client_base_url_property(self, client):
        """Test client base_url property."""
        assert client.base_url == TEST_PROVIDER_URL

    @pytest.mark.asyncio
    async def test_client_base_url_setter(self, client):
        """Test setting client base_url."""
        client.base_url = NEW_TEST_PROVIDER_URL
        assert client.base_url == NEW_TEST_PROVIDER_URL

    @pytest.mark.asyncio
    async def test_client_custom_url(self):
        """Test creating client with custom URL."""
        c = EFAClient(base_url=NEW_TEST_PROVIDER_URL)
        assert c.base_url == NEW_TEST_PROVIDER_URL


class TestListProviders:
    @pytest.mark.asyncio
    async def test_list_providers(self, client):
        """Test listing providers from GitHub."""
        try:
            providers = await client.list_providers()
            assert isinstance(providers, list)
            assert len(providers) > 0

            # Check structure and content
            provider = providers[0]
            assert provider.name
            if provider.url:
                assert provider.url.startswith("http")
            assert provider.country

        except Exception as e:
            if "403" in str(e) or "rate limit" in str(e).lower() or "ConnectError" in str(type(e)):
                pytest.skip(f"GitHub API not accessible: {e}")
            else:
                raise


class TestFindStop:
    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_find_stop(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test finding a stop."""
        c = EFAClient(base_url=provider_url)
        try:
            result = await c.find_stop(stop_name)
            assert result.name
            assert result.id
            assert "Stuttgart" in result.name
            assert ":" in result.id

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_find_stop_not_found(self, client):
        """Test finding a non-existent stop.

        Note: Some EFA providers may return results for any input
        (fuzzy matching). This test is best-effort.
        """
        try:
            result = await client.find_stop("ZZZZNOTEXISTSTOP12345")
            # If we get here, the provider returned a fuzzy match
            # This is acceptable behavior from some EFA providers
        except EFAStopNotFoundError:
            # Expected: no stop found
            pass
        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.skip(f"EFA API not reachable: {e}")
            else:
                raise


class TestDepartureMonitor:
    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_departure_monitor(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test getting departures from a stop."""
        c = EFAClient(base_url=provider_url)
        try:
            stop = await c.find_stop(stop_name)
            departures = await c.departure_monitor(stop.id)
            assert len(departures) > 0

            for dep in departures:
                validate_departure(dep)

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise

    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_departure_monitor_with_time(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test departures with specific time."""
        c = EFAClient(base_url=provider_url)
        try:
            stop = await c.find_stop(stop_name)
            tomorrow = datetime.now() + timedelta(days=1)
            time_str = tomorrow.strftime('%Y-%m-%d') + 'T10:00:00'
            departures = await c.departure_monitor(stop.id, time_str, 5)

            assert len(departures) > 0
            assert len(departures) <= 5

            for dep in departures:
                validate_departure(dep)

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.skip(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise


class TestTripRequest:
    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_trip_request(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test trip planning between stops."""
        c = EFAClient(base_url=provider_url)
        try:
            origin_stop = await c.find_stop(stop_name)
            dest_stop = await c.find_stop(dest_stop_name)

            connections = await c.trip_request(origin_stop.id, dest_stop.id)
            assert len(connections) > 0

            for conn in connections:
                assert len(conn.legs) > 0
                for leg in conn.legs:
                    validate_leg(leg)

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise

    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS_MULTI_LEG)
    @pytest.mark.asyncio
    async def test_trip_request_multi_leg(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test trip planning with multiple legs."""
        c = EFAClient(base_url=provider_url)
        try:
            origin_stop = await c.find_stop(stop_name)
            dest_stop = await c.find_stop(dest_stop_name)

            connections = await c.trip_request(origin_stop.id, dest_stop.id)
            assert len(connections) > 0

            has_multi_leg = any(len(conn.legs) > 1 for conn in connections)
            assert has_multi_leg

            for conn in connections:
                assert len(conn.legs) > 0
                for leg in conn.legs:
                    validate_leg(leg)

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise

    @pytest.mark.parametrize("provider_name,provider_url,stop_name,dest_stop_name", TEST_PROVIDERS)
    @pytest.mark.asyncio
    async def test_trip_request_with_time(self, provider_name, provider_url, stop_name, dest_stop_name):
        """Test trip request with specific departure time."""
        c = EFAClient(base_url=provider_url)
        try:
            origin_stop = await c.find_stop(stop_name)
            dest_stop = await c.find_stop(dest_stop_name)

            tomorrow = datetime.now() + timedelta(days=1)
            time_str = tomorrow.strftime('%Y-%m-%d') + 'T10:00:00'

            connections = await c.trip_request(origin_stop.id, dest_stop.id, time_str, False)
            assert len(connections) > 0

            for conn in connections:
                assert len(conn.legs) > 0
                for leg in conn.legs:
                    validate_leg(leg)

        except Exception as e:
            if "ConnectError" in str(type(e)) or "getaddrinfo" in str(e):
                pytest.fail(f"EFA API not reachable for {provider_name}: {e}")
            else:
                raise
