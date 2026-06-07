# Indy.fr Accounting MCP Server <!-- omit in toc -->

A [Model Context Protocol](https://modelcontextprotocol.com) (MCP) server that exposes accounting data from the [Indy.fr](https://app.indy.fr) platform. It enables MCP clients to query transactions, invoices, and clients, and to create invoice drafts directly from an AI assistant.

- [Usage](#usage)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [Configuration](#configuration)
  - [CLI Reference](#cli-reference)
  - [MCP Tools and Prompts](#mcp-tools-and-prompts)
    - [Tools](#tools)
    - [Prompts](#prompts)
  - [Connect MCP client](#connect-mcp-client)
    - [Claude Desktop](#claude-desktop)
      - [Option 1: Using stdio transport](#option-1-using-stdio-transport)
      - [Option 2: Using HTTP transport](#option-2-using-http-transport)
    - [Claude Code](#claude-code)
  - [Example prompts](#example-prompts)
  - [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Usage

### Prerequisites

- [Python 3.12](https://www.python.org/downloads) or later
- [uv](https://docs.astral.sh/uv/) — Python package and project manager
- An active [Indy.fr](https://app.indy.fr) account

### Quick Start

This server depends on [fastmcp-creds](https://github.com/stephaneberle9/fastmcp-creds) and [python-indy-compta](https://github.com/stephaneberle9/python-indy-compta) as local editable packages. Clone all repositories side by side:

```bash
git clone https://github.com/stephaneberle9/fastmcp-creds.git
git clone https://github.com/stephaneberle9/python-indy-compta.git
git clone https://github.com/stephaneberle9/mcp-server-indy-compta.git
cd mcp-server-indy-compta
uv sync
```

Copy the environment template and configure your credentials:

```bash
cp .env.example .env   # Linux/macOS
copy .env.example .env  # Windows
```

Run the server:

```bash
uv run --env-file .env mcp-server-indy-compta
```

On the first tool call, if `INDY_TOKEN` is not set, a browser window opens automatically and waits for you to log in to Indy.fr. The token is then captured and cached for subsequent runs. The browser defaults to Google Chrome; set `INDY_BROWSER` to use Edge or Chromium instead.

### Configuration

Credentials are provided via environment variables (copy `.env.example` to `.env` and fill in):

| Variable | Description |
| -------- | ----------- |
| `INDY_TOKEN` | Optional Indy.fr HS512 JWT. If unset, browser-based auth is used on the first tool call (a supported browser must be installed — see `INDY_BROWSER`). See `.env.example` for capture instructions. |
| `INDY_BROWSER` | Browser the login flow drives when `INDY_TOKEN` is unset: `chrome` (default), `edge`, or `chromium`. The flow reuses the browser's existing profile, so the chosen browser must be installed. Use `edge` when Chrome isn't available — Edge ships with Windows. |
| `INDY_TOKEN_CACHE_PATH` | Override the token cache file location (default: `~/.cache/mcp-server-indy-compta/token.json`). |
| `INDY_COMPTA_DEBUG` | Set to `true` or `1` to enable debug logging (equivalent to `--debug` flag). |

Two authentication modes are supported:

| Mode | How it works |
| ---- | ------------ |
| **Browser auth** | Leave `INDY_TOKEN` unset. On the first tool call, a browser window opens (Chrome by default; override with `INDY_BROWSER`), you complete the Indy.fr login, and the token is cached at `~/.cache/mcp-server-indy-compta/token.json`. Subsequent starts reuse the cached token; the browser only reopens on 401. |
| **Static token** | Set `INDY_TOKEN` in `.env` to a JWT captured from your browser's DevTools (see `.env.example` for instructions). No browser required at runtime. |

Override the token cache location with `INDY_TOKEN_CACHE_PATH`.

### CLI Reference

| Flag | Description |
| ---- | ----------- |
| `-p`, `--port` | Port to run the MCP server on with HTTP transport (omit to use stdio transport instead) |
| `--silent` | Show only error messages |
| `--debug` | Enable detailed debug logging (also settable via `INDY_COMPTA_DEBUG=1`) |

### MCP Tools and Prompts

#### Tools

| Tool | Description |
| ---- | ----------- |
| `get_transaction_filters` | Return filter metadata for transactions: available date ranges, bank accounts, and categories. Call this first to discover valid filter values. |
| `list_transactions` | Return a paginated list of transactions (30 per page) with optional filters. |
| `list_all_transactions` | Fetch all transactions across all pages as a flat list. Use with care — may return large amounts of data. |
| `list_pending_transactions` | Return pending and upcoming (not yet booked) transactions. |
| `get_receipts_for_transaction` | Return the receipt/invoice documents **attached** to a transaction (filtered to `pairingStatus: "PAIRED"`; the account-wide pool of unattached receipts is excluded). |
| `get_client_suggestions` | Return the full unfiltered list of billing clients. |
| `list_clients` | Search billing clients with pagination. |
| `list_products` | Return all saved products and services from the product library. |
| `list_invoice_drafts` | Return a paginated list of invoice drafts. |
| `list_invoices` | Return a paginated list of finalized invoices, optionally filtered by status. |
| `create_invoice_draft` | Create a new invoice draft for a client with line items and payment terms. |

**Typical workflow:** call `get_transaction_filters` first to discover valid filter values, then use `list_transactions` or `list_all_transactions` with those filters. For invoicing, call `list_clients` to look up a client ID, `list_products` to check the product library, then `create_invoice_draft` to file a draft directly.

#### Prompts

| Prompt | Parameters | Description |
| ------ | ---------- | ----------- |
| `monthly_expense_summary` | `year`, `month` | Guide the assistant to fetch and group expense transactions for a calendar month into a category-breakdown table. |
| `create_invoice_workflow` | `client_name`, `service_description`, `amount_euros` | Step-by-step flow to look up a client, check the product library, and create an invoice draft. |
| `cash_flow_analysis` | `start_date`, `end_date` | Fetch income and expenses for a date range, calculate the net balance, and surface pending transactions. |
| `unreceipted_transactions` | `start_date`, `end_date` | Find expense transactions with no receipt attached — useful for VAT/tax hygiene checks. |

### Connect MCP client

#### Claude Desktop

##### Option 1: Using stdio transport

- Open the *Claude Desktop* configuration file (accessible from *Claude Desktop* >
  `Settings...` > `Developer` > `Edit Config`)
- Add the following entry under `mcpServers`:

  ```jsonc
  {
    "mcpServers": {
      "indy-compta": {
        "command": "uv",
        "args": [
          "run",
          "--with-editable", "/path/to/mcp-server-indy-compta",
          "mcp-server-indy-compta"
        ]
      }
    }
  }
  ```

  On the first tool call, a browser window opens automatically for Indy.fr login. Alternatively, if you prefer a static token over browser auth, add `INDY_TOKEN` to the `env` block:

  ```jsonc
  {
    "mcpServers": {
      "indy-compta": {
        "command": "uv",
        "args": [
          "run",
          "--with-editable", "/path/to/mcp-server-indy-compta",
          "mcp-server-indy-compta"
        ],
        "env": {
          "INDY_TOKEN": "your-hs512-jwt-here"
        }
      }
    }
  }
  ```

- Replace `/path/to/mcp-server-indy-compta` with the actual path to the cloned repository.
- Close *Claude Desktop* and restart it to apply the changes. The server is ready when `indy-compta` appears in the list of connected MCP servers.

##### Option 2: Using HTTP transport

From a terminal, start the MCP server with HTTP transport:

```bash
uv run --env-file .env mcp-server-indy-compta --port 8000 --debug
```

As of writing, *Claude Desktop* only supports local MCP servers using stdio transport out of the box. You therefore need to use a local proxy server that supports stdio transport and forwards all traffic to the actual local MCP server using HTTP transport. This can be easily achieved by using [mcp-remote](https://www.npmjs.com/package/mcp-remote) (requires [Node.js](https://nodejs.org) 18+ with `npx`).

- Open the *Claude Desktop* configuration JSON file (accessible from *Claude Desktop* >
  `Settings...` > `Developer` > `Edit Config`)
- Add the following entry under `mcpServers`:

  ```jsonc
  {
    "mcpServers": {
      "indy-compta": {
        "command": "npx",
        "args": [
          "-y",
          "mcp-remote@latest",
          "http://localhost:8000/mcp"
        ]
      }
    }
  }
  ```

- Close *Claude Desktop* and restart it to apply the changes.

#### Claude Code

Add the server to your Claude Code configuration:

```bash
claude mcp add indy-compta -- uv run --with-editable /path/to/mcp-server-indy-compta mcp-server-indy-compta
```

Or add it manually to `.claude/settings.json` (project) or `~/.claude/settings.json` (global):

```jsonc
{
  "mcpServers": {
    "indy-compta": {
      "command": "uv",
      "args": [
        "run",
        "--with-editable", "/path/to/mcp-server-indy-compta",
        "mcp-server-indy-compta"
      ]
    }
  }
}
```

### Example prompts

The following example prompts can be used to exercise the MCP server in Claude Desktop, Claude Code, or any other MCP client.

- Show me all my expenses for March 2025, grouped by category
- What is my net cash flow for Q1 2025?
- Create an invoice draft for ACME Corp for 3 days of consulting at €800/day
- Which of my expense transactions from last year have no receipt attached?
- List all overdue invoices
- Show me all pending transactions

### Troubleshooting

**Server fails to start in Claude Desktop**

Check the Claude Desktop logs:

- **Windows:** `%LOCALAPPDATA%\Claude\Logs\mcp-server-indy-compta.log`
- **macOS:** `~/Library/Logs/Claude/mcp-server-indy-compta.log`

Or go to `Settings > Developer`, select `indy-compta` and click `Open Logs Folder`.

**Browser does not open for authentication**

Ensure the selected browser is installed. The browser-based auth flow drives Google Chrome by default (via Playwright); set `INDY_BROWSER=edge` to use the Edge browser that ships with Windows, or `INDY_BROWSER=chromium` for a bundled Chromium fallback (which may be blocked by Cloudflare). If it still fails, capture a token manually and set `INDY_TOKEN` in your `.env` file (see `.env.example` for instructions).

**Token expires and tools stop working**

The cached token at `~/.cache/mcp-server-indy-compta/token.json` has expired. Delete it and restart the server — the browser login flow will run again automatically.

**Still having issues?**

Run the server with `--debug` and open an issue on GitHub with the relevant log output.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, running the server locally, code quality checks, testing, and the release process.

## License

MIT — see [LICENSE](LICENSE).
