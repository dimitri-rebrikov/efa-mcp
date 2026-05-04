"""EFA API client - core library for querying EFA transit APIs."""

import os
from typing import Optional, List
from datetime import datetime
from dateutil import parser
import httpx

from efa_lib.models import Stop, Departure, TripConnection, Provider
from efa_lib.exceptions import EFAConnectionError, EFAAPIError, EFAStopNotFoundError

# Default provider URL from environment variable
_DEFAULT_PROVIDER_URL = os.getenv("EFA_BASE_URL", "https://www.efa.de/efa/")

# HTTP request timeout in seconds
HTTP_TIMEOUT = 10.0


def set_default_provider(url: str) -> str:
    """Set the default EFA provider URL for all new client instances.

    Args:
        url: The EFA API provider URL.

    Returns:
        The URL that was set.
    """
    global _DEFAULT_PROVIDER_URL
    _DEFAULT_PROVIDER_URL = url
    return url


def get_default_provider() -> str:
    """Get the current default EFA provider URL.

    Returns:
        The current default provider URL.
    """
    return _DEFAULT_PROVIDER_URL


class EFAClient:
    """Client for querying EFA (Electronic Fahrplan Auskunft) transit APIs.

    Args:
        base_url: The EFA API provider URL. Defaults to the global default
            (from EFA_BASE_URL env var or "https://www.efa.de/efa/").
        timeout: HTTP request timeout in seconds. Defaults to 10.0.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = HTTP_TIMEOUT):
        self._base_url = base_url or _DEFAULT_PROVIDER_URL
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        """Get the current provider URL for this client instance."""
        return self._base_url

    @base_url.setter
    def base_url(self, url: str) -> None:
        """Set the provider URL for this client instance."""
        self._base_url = url

    async def find_stop(self, name: str) -> Stop:
        """Find a stop by name and return the best match.

        Args:
            name: Name of the stop to search for.

        Returns:
            A Stop object with the name and id of the best matching stop.

        Raises:
            EFAConnectionError: If the EFA API is unreachable.
            EFAAPIError: If the EFA API returns an error message.
            EFAStopNotFoundError: If no stop is found.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            params = {
                "commonMacro": "stopfinder",
                "type_sf": "any",
                "name_sf": name,
                "outputFormat": "rapidJSON",
            }
            try:
                resp = await client.get(
                    f"{self._base_url}XML_STOPFINDER_REQUEST", params=params
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise EFAConnectionError(f"Failed to connect to EFA API: {e}") from e

            data = resp.json()

            # Check for API errors
            self._check_api_errors(data)

            # Find stops
            locations = data.get("locations", [])
            if not locations:
                raise EFAStopNotFoundError(f"No stops found for '{name}'")

            # Find the best match
            best = next(
                (loc for loc in locations if loc.get("isBest")), locations[0]
            )
            if not best:
                raise EFAStopNotFoundError(f"No stop found for '{name}'")

            return Stop(name=best["name"], id=best["id"])

    async def departure_monitor(
        self,
        stop_id: str,
        time: Optional[str] = None,
        limit: Optional[int] = 10,
    ) -> List[Departure]:
        """Get departures from a stop.

        Args:
            stop_id: Stop identifier.
            time: Optional departure time in ISO 8601 format or other common formats.
                Examples: "2026-05-01T19:43:00Z", "2026-05-01 19:43", "2026-05-01"
            limit: Maximum number of departures to return (default: 10).

        Returns:
            A list of Departure objects.

        Raises:
            EFAConnectionError: If the EFA API is unreachable.
            EFAAPIError: If the EFA API returns an error message.
        """
        params = {
            "commonMacro": "dm",
            "type_dm": "any",
            "name_dm": stop_id,
            "useRealtime": "1",
            "limit": str(limit),
            "mode": "direct",
            "outputFormat": "rapidJSON",
        }
        if time:
            dt = parser.parse(time)
            params["itdDate"] = dt.strftime("%Y%m%d")
            params["itdTime"] = dt.strftime("%H%M")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}XML_DM_REQUEST", params=params
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise EFAConnectionError(f"Failed to connect to EFA API: {e}") from e

            data = resp.json()

            # Check for API errors
            self._check_api_errors(data)

            departures = []
            for event in data.get("stopEvents", []):
                dep = event.get("departureTimePlanned", "")
                est = event.get("departureTimeEstimated", "")
                trans = event.get("transportation", {})
                departures.append(
                    Departure(
                        planned_time=dep,
                        estimated_time=est if est else None,
                        type=str(trans.get("product", {}).get("class", "")),
                        number=trans.get("number", ""),
                        direction=trans.get("destination", {}).get("name", ""),
                    )
                )
            return departures

    async def trip_request(
        self,
        origin_id: str,
        dest_id: str,
        time: Optional[str] = None,
        is_arrival: bool = False,
    ) -> List[TripConnection]:
        """Get trip connections between two stops.

        Args:
            origin_id: Origin stop identifier.
            dest_id: Destination stop identifier.
            time: Optional departure/arrival time in ISO 8601 format or other
                common formats.
                Examples: "2026-05-01T19:43:00Z", "2026-05-01 19:43", "2026-05-01"
            is_arrival: If True, time is treated as desired arrival time.
                If False, as departure time.

        Returns:
            A list of TripConnection objects.

        Raises:
            EFAConnectionError: If the EFA API is unreachable.
            EFAAPIError: If the EFA API returns an error message.
        """
        params = {
            "commonMacro": "trip",
            "type_origin": "any",
            "name_origin": origin_id,
            "type_destination": "any",
            "name_destination": dest_id,
            "useRealtime": "1",
            "outputFormat": "rapidJSON",
        }
        if time:
            dt = parser.parse(time)
            params["itdDate"] = dt.strftime("%Y%m%d")
            params["itdTime"] = dt.strftime("%H%M")
            params["itdTripDateTimeDepArr"] = "arr" if is_arrival else "dep"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(
                    f"{self._base_url}XML_TRIP_REQUEST2", params=params
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise EFAConnectionError(f"Failed to connect to EFA API: {e}") from e

            data = resp.json()

            # Check for API errors
            self._check_api_errors(data)

            connections = []
            for journey in data.get("journeys", []):
                legs = []
                for leg in journey.get("legs", []):
                    trans = leg.get("transportation", {})
                    dep = leg.get("origin", {})
                    arr = leg.get("destination", {})
                    legs.append(
                        {
                            "type": str(
                                trans.get("product", {}).get("class", "")
                            ),
                            "number": trans.get("number", ""),
                            "direction": trans.get("destination", {}).get(
                                "name", ""
                            ),
                            "departure_station": dep.get("name", ""),
                            "planned_departure_time": dep.get(
                                "departureTimePlanned", ""
                            ),
                            "estimated_departure_time": dep.get(
                                "departureTimeEstimated", ""
                            )
                            or None,
                            "arrival_station": arr.get("name", ""),
                            "planned_arrival_time": arr.get(
                                "arrivalTimePlanned", ""
                            ),
                            "estimated_arrival_time": arr.get(
                                "arrivalTimeEstimated", ""
                            )
                            or None,
                        }
                    )
                connections.append(TripConnection(legs=legs))
            return connections

    async def list_providers(self) -> List[Provider]:
        """List available EFA API providers from public-transport/transport-apis repo.

        Returns:
            A list of Provider objects with name, url, country, and info.

        Raises:
            EFAConnectionError: If the GitHub API is unreachable.
        """
        providers = []

        async def recurse_github(path: str):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://api.github.com/repos/public-transport/transport-apis/contents/{path}?ref=v1"
                    )
                    resp.raise_for_status()
                    contents = resp.json()
                    for item in contents:
                        if item["type"] == "file" and item["name"].endswith(
                            ".json"
                        ):
                            data_resp = await client.get(item["download_url"])
                            data_resp.raise_for_status()
                            data = data_resp.json()
                            if data.get("type", {}).get("efa"):
                                providers.append(
                                    Provider(
                                        name=item["name"]
                                        .replace("-efa.json", "")
                                        .replace("-", " ")
                                        .title(),
                                        url=data.get("source", ""),
                                        country=path.split("/")[-2]
                                        if "/" in path
                                        else "unknown",
                                        info=data,
                                    )
                                )
                        elif item["type"] == "dir":
                            await recurse_github(item["path"])
            except httpx.HTTPError as e:
                raise EFAConnectionError(
                    f"Failed to fetch providers from GitHub: {e}"
                ) from e

        await recurse_github("data")
        return providers

    @staticmethod
    def _check_api_errors(data: dict) -> None:
        """Check EFA API response for error messages and raise if found.

        Args:
            data: The parsed JSON response from the EFA API.

        Raises:
            EFAAPIError: If the API response contains an error message.
        """
        if "systemMessages" in data:
            for msg in data["systemMessages"]:
                if msg.get("type") == "error" and msg.get("text", "").strip():
                    raise EFAAPIError(msg["text"])
