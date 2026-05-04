"""EFA MCP server - exposes EFA transit API as MCP tools and resources.

This module provides a FastMCP server that wraps the EFA library for use
with AI agents via the Model Context Protocol (MCP).
"""

import os
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP

from efa_lib import EFAClient, set_default_provider, get_default_provider

# Initialize FastMCP app
mcp = FastMCP("efa")

# Global client instance
_client = EFAClient()


@mcp.resource("efa://provider_url")
@mcp.tool()
async def get_provider_url() -> str:
    """Get the current EFA provider URL."""
    return _client.base_url


@mcp.tool()
async def set_provider_url(url: str) -> str:
    """Set the EFA provider URL for all operations.

    Args:
        url: The EFA API provider URL.

    Returns:
        The URL that was set.
    """
    _client.base_url = url
    set_default_provider(url)
    return url


@mcp.tool()
async def list_providers() -> List[Dict[str, Any]]:
    """List available EFA API providers from public-transport/transport-apis repo.

    Returns:
        A list of providers with name, url, country, and info.
    """
    providers = await _client.list_providers()
    return [p.model_dump() for p in providers]


@mcp.tool()
async def find_stop(name: str) -> Dict[str, str]:
    """Find a stop by name and return the best match.

    Args:
        name: Name of the stop to search for.

    Returns:
        A dict with "name" and "id" of the matching stop.
    """
    stop = await _client.find_stop(name)
    return stop.model_dump()


@mcp.tool()
async def departure_monitor(
    stop_id: str,
    time: Optional[str] = None,
    limit: Optional[int] = 10,
) -> List[Dict[str, Any]]:
    """Get departures from a stop.

    Args:
        stop_id: Stop identifier.
        time: Optional departure time in ISO 8601 format or other common formats.
              Examples: "2026-05-01T19:43:00Z", "2026-05-01 19:43", "2026-05-01"
        limit: Maximum number of departures to return (default: 10).

    Returns:
        A list of departures with planned_time, estimated_time, type, number, direction.
    """
    departures = await _client.departure_monitor(stop_id, time, limit)
    return [d.model_dump() for d in departures]


@mcp.tool()
async def trip_request(
    origin_id: str,
    dest_id: str,
    time: Optional[str] = None,
    is_arrival: bool = False,
) -> List[Dict[str, Any]]:
    """Get trip connections between two stops.

    Args:
        origin_id: Origin stop identifier.
        dest_id: Destination stop identifier.
        time: Optional departure/arrival time in ISO 8601 format or other common formats.
              Examples: "2026-05-01T19:43:00Z", "2026-05-01 19:43", "2026-05-01"
        is_arrival: If True, time is treated as desired arrival time. If False, as departure time.

    Returns:
        A list of connections, each containing legs with transport details.
    """
    connections = await _client.trip_request(origin_id, dest_id, time, is_arrival)
    return [c.model_dump() for c in connections]


def main():
    """Entry point for the EFA MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
