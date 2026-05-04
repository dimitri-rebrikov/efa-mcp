# EFA MCP

A Python toolkit for querying EFA (Electronic Fahrplan Auskunft) transit APIs in Germany. Provides three integration options:

- **📦 efa-lib** — Core library for embedding in Python applications
- **🖥️ efa-mcp** — MCP server for AI agent integration (Model Context Protocol)
- **⌨️ efa** — CLI for exploratory testing and scripting

## Features

- **Find Stop**: Search for transit stops by name
- **Departure Monitor**: Get real-time departures from a stop
- **Trip Request**: Plan trips between stops with real-time data
- **Provider Management**: Set custom EFA providers or list available ones

## Usage

No project checkout is required. All three integration options can be used directly from the GitHub repository.

---

### 📦 As a Library (efa-lib)

Add the library to your Python project:

```bash
uv add "git+https://github.com/dimitri-rebrikov/efa-mcp.git"
```

Then use it in your code:

```python
import asyncio
from efa_lib import EFAClient

async def main():
    client = EFAClient("https://www.efa.de/efa/")

    # Find a stop
    stop = await client.find_stop("Stuttgart Hauptbahnhof")
    print(f"Found: {stop.name} ({stop.id})")

    # Get departures
    departures = await client.departure_monitor(stop.id, limit=5)
    for dep in departures:
        print(f"{dep.planned_time} - {dep.type} {dep.number} -> {dep.direction}")

    # Plan a trip
    dest = await client.find_stop("Stuttgart Flughafen/Messe")
    connections = await client.trip_request(stop.id, dest.id)
    for conn in connections:
        for leg in conn.legs:
            print(f"{leg.departure_station} -> {leg.arrival_station} via {leg.number}")

asyncio.run(main())
```

---

### 🖥️ As an MCP Server (efa-mcp)

For AI agents that support the Model Context Protocol (OpenClaw, Hermes, Claude Desktop, etc.).

Add to your MCP client settings:

```json
{
  "mcpServers": {
    "efa": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/dimitri-rebrikov/efa-mcp.git",
        "--refresh",
        "efa-mcp"
      ]
    }
  }
}
```

`uvx` automatically fetches and runs the package from GitHub — no manual installation needed. The `--refresh` flag ensures dependencies are updated on each start.

#### MCP Tools

| Tool | Description |
|---|---|
| `get_provider_url()` | Get the current EFA provider URL |
| `set_provider_url(url)` | Set the EFA provider URL |
| `list_providers()` | List available EFA API providers |
| `find_stop(name)` | Find a stop by name |
| `departure_monitor(stop_id, time?, limit?)` | Get departures from a stop |
| `trip_request(origin_id, dest_id, time?, is_arrival?)` | Plan a trip between stops |

#### MCP Resources

| Resource | Description |
|---|---|
| `efa://provider_url` | Current EFA provider URL |

---

### ⌨️ As a CLI (efa)

For terminal-based exploration and scripting.

Run any command directly with `uvx` — no installation needed:

```bash
# Show current provider URL
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa status

# Set a custom provider
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa set-url "https://www3.vvs.de/mngvvs/"

# Find a stop
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa find-stop "Stuttgart Hauptbahnhof"

# Get departures (default: 10)
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa departures "de:08111:..."

# Get departures with time and limit
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa departures "de:08111:..." --time "2026-05-01T10:00:00" --limit 5

# Plan a trip
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa trip "de:08111:..." "de:08111:..."

# Plan a trip with arrival time
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa trip "de:08111:..." "de:08111:..." --time "2026-05-01T10:00:00" --arrival

# List available providers
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa list-providers

# Override provider URL for a single command (--url must come before the subcommand)
uvx --from "git+https://github.com/dimitri-rebrikov/efa-mcp.git" efa --url "https://www3.vvs.de/mngvvs/" find-stop "Stuttgart Hbf"
```

---

## Configuration

Set the default EFA provider URL via environment variable:

```bash
export EFA_BASE_URL="https://www.efa.de/efa/"
```

Default is `https://www.efa.de/efa/`.

## EFA Providers

The server supports any EFA-compatible API. Known providers:

- EFA (generic): `https://www.efa.de/efa/`
- VVS (Stuttgart): `https://www3.vvs.de/mngvvs/`

Use `list-providers` or `efa list-providers` to discover more.

## Testing

### Automated Tests

The project includes comprehensive tests that run against real EFA APIs:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_efa_lib/ -v    # Library tests
uv run pytest tests/test_efa_mcp/ -v    # MCP server tests
uv run pytest tests/test_efa_cli/ -v    # CLI tests

# Run with coverage
uv run pytest tests/ -v --cov=src
```

Tests will show as PASSED when APIs are available, SKIPPED when unreachable.

### Manual Testing (MCP Inspector)

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) lets you interactively test the MCP server:

```bash
npx @modelcontextprotocol/inspector uv run efa-mcp
```

Open `http://localhost:5173` in your browser to test the tools.

## Project Structure

```
efa-mcp/
├── src/
│   ├── efa_lib/          # Core library (embed in Python apps)
│   │   ├── client.py     # EFAClient - HTTP logic
│   │   ├── models.py     # Pydantic data models
│   │   └── exceptions.py # Custom exceptions
│   ├── efa_mcp/          # MCP server (AI agent integration)
│   │   └── server.py     # FastMCP app with tools & resources
│   └── efa_cli/          # CLI (terminal usage)
│       └── cli.py        # argparse-based command-line interface
├── tests/
│   ├── conftest.py       # Shared fixtures and test helpers
│   ├── test_efa_lib/     # Library tests
│   ├── test_efa_mcp/     # MCP server tests
│   └── test_efa_cli/     # CLI tests
├── pyproject.toml
└── README.md
```

## License

MIT
