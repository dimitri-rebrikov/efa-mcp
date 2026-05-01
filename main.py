import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from dateutil import parser
import httpx
from fastmcp import FastMCP

# Initialize FastMCP app
mcp = FastMCP("efa")

# Global state for current provider URL
current_provider_url = os.getenv("EFA_BASE_URL", "https://www.efa.de/efa/")

@mcp.resource("efa://provider_url")
async def get_provider_url() -> str:
    """Get the current EFA provider URL."""
    return current_provider_url

@mcp.tool()
async def set_provider_url(url: str) -> str:
    """Set the EFA provider URL for all operations."""
    global current_provider_url
    current_provider_url = url
    return url

@mcp.tool()
async def list_providers() -> List[Dict[str, Any]]:
    """List available EFA API providers from public-transport/transport-apis repo."""
    providers = []
    async def recurse_github(path: str):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://api.github.com/repos/public-transport/transport-apis/contents/{path}?ref=v1")
                resp.raise_for_status()
                contents = resp.json()
                for item in contents:
                    if item['type'] == 'file' and item['name'].endswith('.json'):
                        data_resp = await client.get(item['download_url'])
                        data_resp.raise_for_status()
                        data = data_resp.json()
                        if data.get('type', {}).get('efa'):
                            providers.append({
                                "name": item['name'].replace('-efa.json', '').replace('-', ' ').title(),
                                "url": data.get('source', ''),
                                "country": path.split('/')[-2] if '/' in path else 'unknown',
                                "info": data
                            })
                    elif item['type'] == 'dir':
                        await recurse_github(item['path'])
        except Exception as e:
            raise ValueError(f"Failed to fetch providers: {e}")
    await recurse_github('data')
    return providers

@mcp.tool()
async def find_stop(name: str) -> Dict[str, str]:
    """Find a stop by name and return the best match."""
    async with httpx.AsyncClient() as client:
        params = {
            'commonMacro': 'stopfinder',
            'type_sf': 'any',
            'name_sf': name,
            'outputFormat': 'rapidJSON'
        }
        resp = await client.get(f"{current_provider_url}XML_STOPFINDER_REQUEST", params=params)
        resp.raise_for_status()
        data = resp.json()

        # Check for errors - only raise for non-empty error messages
        if 'systemMessages' in data:
            for msg in data['systemMessages']:
                if msg.get('type') == 'error' and msg.get('text', '').strip():
                    raise ValueError(f"EFA API error: {msg['text']}")

        # Find stops
        locations = data.get('locations', [])
        if not locations:
            raise ValueError("No stops found")

        # Find the best match
        best = next((loc for loc in locations if loc.get('isBest')), locations[0])
        if not best:
            raise ValueError("No stop found")

        return {"name": best['name'], "id": best['id']}

@mcp.tool()
async def departure_monitor(stop_id: str, time: Optional[str] = None, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
    """Get departures from a stop.

    Args:
        stop_id: Stop identifier
        time: Optional departure time in ISO 8601 format or other common formats.
              Examples: "2026-05-01T19:43:00Z", "2026-05-01 19:43", "2026-05-01"
        limit: Maximum number of departures to return (default: 10)
    """
    params = {
        'commonMacro': 'dm',
        'type_dm': 'any',
        'name_dm': stop_id,
        'useRealtime': '1',
        'limit': str(limit),
        'outputFormat': 'rapidJSON'
    }
    if time:
        dt = parser.parse(time)
        params['itdDate'] = dt.strftime('%Y%m%d')
        params['itdTime'] = dt.strftime('%H%M')
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{current_provider_url}XML_DM_REQUEST", params=params)
        resp.raise_for_status()
        data = resp.json()

        # Check for errors - only raise for non-empty error messages
        if 'systemMessages' in data:
            for msg in data['systemMessages']:
                if msg.get('type') == 'error' and msg.get('text', '').strip():
                    raise ValueError(f"EFA API error: {msg['text']}")

        departures = []
        for event in data.get('stopEvents', []):
            dep = event.get('departureTimePlanned', '')
            est = event.get('departureTimeEstimated', '')
            trans = event.get('transportation', {})
            departures.append({
                "planned_time": dep,
                "estimated_time": est if est else None,
                "type": trans.get('product', {}).get('class', ''),
                "number": trans.get('number', ''),
                "direction": trans.get('destination', {}).get('name', '')
            })
        return departures

@mcp.tool()
async def trip_request(origin_id: str, dest_id: str, time: Optional[str] = None, is_arrival: bool = False) -> List[Dict[str, Any]]:
    """Get trip connections between two stops.

    Args:
        origin_id: Origin stop identifier
        dest_id: Destination stop identifier
        time: Optional departure/arrival time in ISO 8601 format or other common formats.
              Examples: "2026-05-01T19:43:00Z", "2026-05-01 19:43", "2026-05-01"
        is_arrival: If True, time is treated as desired arrival time. If False, as departure time.
    """
    params = {
        'commonMacro': 'trip',
        'type_origin': 'any',
        'name_origin': origin_id,
        'type_destination': 'any',
        'name_destination': dest_id,
        'useRealtime': '1',
        'outputFormat': 'rapidJSON'
    }
    if time:
        dt = parser.parse(time)
        params['itdDate'] = dt.strftime('%Y%m%d')
        params['itdTime'] = dt.strftime('%H%M')
        params['itdTripDateTimeDepArr'] = 'arr' if is_arrival else 'dep'
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{current_provider_url}XML_TRIP_REQUEST2", params=params)
        resp.raise_for_status()
        data = resp.json()

        # Check for errors - only raise for non-empty error messages
        if 'systemMessages' in data:
            for msg in data['systemMessages']:
                if msg.get('type') == 'error' and msg.get('text', '').strip():
                    raise ValueError(f"EFA API error: {msg['text']}")

        connections = []
        for journey in data.get('journeys', []):
            legs = []
            for leg in journey.get('legs', []):
                trans = leg.get('transportation', {})
                dep = leg.get('origin', {})
                arr = leg.get('destination', {})
                legs.append({
                    "type": trans.get('product', {}).get('class', ''),
                    "number": trans.get('number', ''),
                    "direction": trans.get('destination', {}).get('name', ''),
                    "departure_station": dep.get('name', ''),
                    "planned_departure_time": dep.get('departureTimePlanned', ''),
                    "estimated_departure_time": dep.get('departureTimeEstimated', ''),
                    "arrival_station": arr.get('name', ''),
                    "planned_arrival_time": arr.get('arrivalTimePlanned', ''),
                    "estimated_arrival_time": arr.get('arrivalTimeEstimated', '')
                })
            connections.append({"legs": legs})
        return connections

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run())