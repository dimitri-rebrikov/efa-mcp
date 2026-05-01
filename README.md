# EFA MCP Server

An MCP (Model Context Protocol) server for querying EFA (Electronic Fahrplan Auskunft) transit APIs in Germany.

## Features

- **Find Stop**: Search for transit stops by name
- **Departure Monitor**: Get real-time departures from a stop
- **Trip Request**: Plan trips between stops with real-time data
- **Provider Management**: Set custom EFA providers or list available ones

## Installation

```bash
# Clone the repo
git clone https://github.com/dimitri-rebrikov/efa-mcp.git
cd efa-mcp

# Install with uv
uv sync
```

## Configuration

Set the default EFA provider URL via environment variable:

```bash
export EFA_BASE_URL="https://www.efa.de/efa/"
```

Default is `https://www.efa.de/efa/`.

## Running

### Local Development

```bash
uv run python main.py
```

### With Cline

Add to your `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "efa": {
      "command": "uv",
      "args": ["run", "python", "main.py"]
    }
  }
}
```

## API Reference

### Tools

#### `set_provider_url(url: str) -> str`
Set the EFA provider URL for all operations.

**Returns**: The provider URL string.

#### `list_providers() -> list`
List available EFA API providers from the public-transport/transport-apis repository.

**Returns**: List of `{"name": str, "url": str, "country": str, "info": dict}`

#### `find_stop(name: str) -> dict`
Find a stop by name and return the best match (the one with `isBest` flag).

**Returns**: `{"name": str, "id": str}`

#### `departure_monitor(stop_id: str, time?: str, limit?: int) -> list`
Get departures from a stop.

- `time`: Optional departure time in ISO 8601 format or other common formats.
  Examples: `"2026-05-01T19:43:00Z"`, `"2026-05-01 19:43"`, `"2026-05-01"`
- `limit`: Maximum number of departures to return (default: 10)

**Returns**: List of `{"planned_time": str, "estimated_time": str?, "type": str, "number": str, "direction": str}`

#### `trip_request(origin_id: str, dest_id: str, time?: str, is_arrival?: bool) -> list`
Get trip connections between two stops.

- `time`: Optional departure/arrival time in ISO 8601 format or other common formats.
  Examples: `"2026-05-01T19:43:00Z"`, `"2026-05-01 19:43"`, `"2026-05-01"`
- `is_arrival`: If True, time is treated as desired arrival time. If False, as departure time (default: False).

**Returns**: List of connections, each containing:
```json
{
  "legs": [
    {
      "type": str,
      "number": str,
      "direction": str,
      "departure_station": str,
      "planned_departure_time": str,
      "estimated_departure_time": str?,
      "arrival_station": str,
      "planned_arrival_time": str,
      "estimated_arrival_time": str?
    }
  ]
}
```

### Resources

#### `efa://provider_url` (Python: `get_provider_url()`)
Get the current EFA provider URL.

**Returns**: The provider URL as a plain string (e.g. `"https://www.efa.de/efa/"`)

## EFA Providers

The server supports any EFA-compatible API. Known providers:

- EFA (generic): `https://www.efa.de/efa/`
- VVS (Stuttgart): `https://www3.vvs.de/mngvvs/`

Use `list_providers()` to discover more.

## Testing

The project includes comprehensive tests that run against real EFA APIs:

### Test Coverage
- **Provider Management**: Setting and getting provider URLs
- **Stop Finding**: Searching for stops by name
- **Departure Monitor**: Getting departures with and without time filters
- **Trip Planning**: Planning trips between stops with and without time filters
- **Multi-Provider**: Tests run parametrized for both EFA and VVS providers
- **Time Format Validation**: Validates returned time strings match expected formats

### Run Tests
```bash
uv run pytest tests/ -v
```

Tests will show as PASSED when APIs are available, SKIPPED when unreachable.

## License

MIT