# Contributing <!-- omit in toc -->

- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [Initial Setup](#initial-setup)
- [Running the Server](#running-the-server)
  - [Inside dev environment](#inside-dev-environment)
  - [Outside dev environment](#outside-dev-environment)
  - [With MCP Inspector](#with-mcp-inspector)
    - [Option 1: Connect using stdio transport](#option-1-connect-using-stdio-transport)
    - [Option 2: Connect using HTTP transport](#option-2-connect-using-http-transport)
- [Code Quality](#code-quality)
  - [Enable automatic execution on git commit](#enable-automatic-execution-on-git-commit)
  - [Manual execution](#manual-execution)
- [Testing](#testing)
- [Release Process](#release-process)

## Development Setup

### Prerequisites

- [Python 3.12](https://www.python.org/downloads) or later
- [uv](https://docs.astral.sh/uv/) — Python package and project manager
- [Google Chrome](https://www.google.com/chrome/) — required for browser-based authentication

### Initial Setup

> [!IMPORTANT]
> This server depends on [fastmcp-creds](https://github.com/stephaneberle9/fastmcp-creds) and
> [python-indy-compta](https://github.com/stephaneberle9/python-indy-compta) as local editable
> packages. Both repos must be cloned side by side before running `uv sync`.

```bash
git clone https://github.com/stephaneberle9/fastmcp-creds.git
git clone https://github.com/stephaneberle9/python-indy-compta.git
git clone https://github.com/stephaneberle9/mcp-server-indy-compta.git
cd mcp-server-indy-compta
uv sync
```

The expected directory layout:

```text
W:\GitHub\
├── fastmcp-creds\                ← credential management library (editable dependency)
├── mcp-server-indy-compta\       ← this repo
└── python-indy-compta\           ← Indy.fr client library (editable dependency)
```

Copy the environment template and configure your credentials:

```bash
cp .env.example .env   # Linux/macOS
copy .env.example .env  # Windows
```

## Running the Server

### Inside dev environment

```bash
# Run the MCP server (stdio transport by default)
uv run --env-file .env mcp-server-indy-compta [--debug]

# Run with HTTP transport on a port of your choice
uv run --env-file .env mcp-server-indy-compta --port 8000 --debug

# Stop the server
# Press Ctrl+C to exit
```

### Outside dev environment

```bash
# Run directly from the sources (no prior install needed)
uv run --project "/path/to/mcp-server-indy-compta" --env-file "/path/to/mcp-server-indy-compta/.env" mcp-server-indy-compta [options]

# Run as an editable install (enables live code reloading during development)
uv run --with-editable "/path/to/mcp-server-indy-compta" --env-file "/path/to/mcp-server-indy-compta/.env" mcp-server-indy-compta [options]
```

### With MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a browser-based tool for interactively testing MCP servers. It requires [Node.js](https://nodejs.org) 18+ with `npx`.

#### Option 1: Connect using stdio transport

Create an `mcp-stdio.json` file:

```jsonc
{
  "mcpServers": {
    "indy-compta": {
      "command": "uv",
      "args": [
        "run",
        "mcp-server-indy-compta",
        "--debug"
      ]
    }
  }
}
```

Start the MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector --config mcp-stdio.json --server indy-compta
```

In your browser, connect to the server and explore its tools and prompts:

- Connect to MCP server: `Connect` or `Restart`

  > [!NOTE]
  > The MCP server instance is started automatically by the inspector.

- List tools: `Tools` > `List Tools`
- List prompts: `Prompts` > `List Prompts`
- Find MCP server logs under `Server Notifications` and in `%TEMP%\mcp_server_indy_compta.log` (Windows) or `${TMPDIR:-/tmp}/mcp_server_indy_compta.log` (Linux/macOS)

#### Option 2: Connect using HTTP transport

From a terminal, start your MCP server:

```bash
uv run --env-file .env mcp-server-indy-compta --port 8000 --debug
```

From another terminal, start the MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector
```

In your browser, connect to the server:

| Setting | Value |
| ------- | ----- |
| **Transport Type** | `Streamable HTTP` |
| **URL** | `http://localhost:8000/mcp` |
| **Connection Type** | `Via Proxy` |

- Connect to MCP server: `Connect` or `Reconnect`

  > [!WARNING]
  > The MCP server instance must be started manually before connecting (see above).

- Find MCP server logs in the terminal where you started it

## Code Quality

This project uses `pre-commit` hooks for static checks to maintain high code quality standards:

| Hook | Purpose |
| ---- | ------- |
| `validate-pyproject` | Project configuration validation |
| `prettier` | JSON and YAML formatting |
| `ruff-check` | Python linting (with auto-fix) |
| `ruff-format` | Python code formatting |
| `ty check` | Modern type checking for Python |
| `codespell` | Common spelling error detection |

### Enable automatic execution on git commit

```bash
uv run pre-commit install
```

### Manual execution

```bash
# Run all checks on all files
uv run pre-commit run --all-files

# Run individual tools
uv run ruff format          # Code formatting
uv run ruff check --fix     # Linting with auto-fix
uv run ty check             # Type checking
```

## Testing

```bash
# Run all tests with coverage report
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_mcp_tools.py
```

## Release Process

1. Ensure all changes are committed and the `main` branch is up to date.

2. Create and push a version tag:

   ```bash
   git tag v1.x.x
   git push origin v1.x.x
   ```

3. Create a GitHub release from the tag and add release notes.

The package version is derived automatically from the git tag by
[uv-dynamic-versioning](https://github.com/nicoddemus/uv-dynamic-versioning).
