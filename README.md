# EFA MCP Server

An MCP (Model Context Protocol) server for querying EFA (Electronic Fahrplan Auskunft) transit APIs in Germany.

## Features

- **Find Stop**: Search for transit stops by name
- **Departure Monitor**: Get real-time departures from a stop
- **Trip Request**: Plan trips between stops with real-time data
- **Provider Management**: Set custom EFA providers or list available ones

## Configuration

Set the default EFA provider URL via environment variable:

```bash
export EFA_BASE_URL="https://www.efa.de/efa/"
```

Default is `https://www.efa.de/efa/`.

## Running

### Development Setup

```bash
# Clone the repo
git clone https://github.com/dimitri-rebrikov/efa-mcp.git
cd efa-mcp

# Install dependencies with uv
uv sync

# Run locally
uv run python main.py
```

### MCP Client Configuration (for any AI agent)

To use this MCP server with any AI agent that supports MCP (e.g. Cline, Claude Desktop, Hermes, etc.), add the following to your MCP client configuration file:

```json
{
  "mcpServers": {
    "efa": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/dimitri-rebrikov/efa-mcp.git",
        "python", "main.py"
      ]
    }
  }
}
```

> **Note**: `uvx` automatically fetches and runs the package from the specified Git repository, so no manual installation is needed when using this method. The configuration above works with any MCP-compatible client.

## API Reference

### Tools

#### `get_provider_url() -> str`
Get the current EFA provider URL.

**Returns**: The provider URL as a plain string (e.g. `"https://www.efa.de/efa/"`)

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

#### `efa://provider_url` (also available as tool `get_provider_url()`)
Get the current EFA provider URL.

**Returns**: The provider URL as a plain string (e.g. `"https://www.efa.de/efa/"`)

## EFA Providers

The server supports any EFA-compatible API. Known providers:

- EFA (generic): `https://www.efa.de/efa/`
- VVS (Stuttgart): `https://www3.vvs.de/mngvvs/`

Use `list_providers()` to discover more.

## Testing

### Automated Tests

The project includes comprehensive tests that run against real EFA APIs:

#### Test Coverage
- **Provider Management**: Setting and getting provider URLs
- **Stop Finding**: Searching for stops by name
- **Departure Monitor**: Getting departures with and without time filters
- **Trip Planning**: Planning trips between stops with and without time filters
- **Multi-Provider**: Tests run parametrized for both EFA and VVS providers
- **Time Format Validation**: Validates returned time strings match expected formats

#### Run Tests
```bash
uv run pytest tests/ -v
```

Tests will show as PASSED when APIs are available, SKIPPED when unreachable.

### Manual Testing (MCP Inspector)

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a web-based tool that lets you interactively test your MCP server. It provides a GUI to call tools, read resources, and inspect responses.

The Inspector automatically starts the MCP server for you — you only need to run one command.

**Prerequisites**: Node.js (v18 or later)

**Steps**:

1. **Launch the Inspector** (this starts the MCP server automatically):
   ```bash
   npx @modelcontextprotocol/inspector uv run python main.py
   ```

2. **Open the Inspector** in your browser at `http://localhost:5173`

3. **Test the tools** via the web interface:
   - Click **"List Tools"** to see all available tools
   - Select a tool (e.g. `find_stop`), enter parameters (e.g. `{"name": "Stuttgart Hauptbahnhof"}`), and click **"Call Tool"**
   - Try `departure_monitor` with a stop ID, or `trip_request` with origin and destination IDs
   - Use `set_provider_url` to switch between providers (EFA, VVS, etc.)
   - Read the `efa://provider_url` resource to see the current provider


## License

MIT