# kitetdx-mcp

An MCP (Model Context Protocol) server for `kitetdx`, providing access to Chinese stock market data and financial reports for LLMs.

This server enables LLMs (like Claude) to:
- Retrieve historical K-line data (daily, adjustable queries).
- Access financial reports and fundamental data.
- Automatically sync and update data daily.

## Features

- **Daily K-line Data**: Get adjusted (QFQ/HFQ) or unadjusted daily stock prices.
- **Financial Data**: Retrieve detailed financial reports (EPS, ROE, etc.). Automatically falls back to previous reports if the latest one contains no data for a specific stock.
- **Automated Sync**: Scheduled tasks (default 18:00 daily) to keep local data fresh.
- **Efficient Transport**: Uses Streamable HTTP transport for stable performance.
- **Zero-Config Data**: Automatically downloads required data files on demand.

## Prerequisites

- Python 3.10+
- `uv` (recommended) or `pip`

## Installation

### Method 1: Using `uv` (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd kitetdx-mcp

# Install dependencies and run
uv run src/api_server.py
```

### Method 2: Standard pip

```bash
# Clone the repository
git clone <repository-url>
cd kitetdx-mcp

# Install requirements
pip install -r requirements.txt

# Run the server
python src/api_server.py
```

## Configuration

The server runs on port `8010` by default. You can override settings using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `KITETDX_API_PORT` | Server listening port | `8010` |
| `KITETDX_DIR` | Data storage directory | `./data` |

### Claude Desktop Configuration

Configure the MCP server in your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kitetdx": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/kitetdx-mcp",
        "src/api_server.py"
      ]
    }
  }
}
```

Or if you prefer using `python` directly:

```json
{
  "mcpServers": {
    "kitetdx": {
      "command": "/path/to/python",
      "args": [
        "/absolute/path/to/kitetdx-mcp/src/api_server.py"
      ]
    }
  }
}
```

## Available Tools

### 1. `get_daily_kline`

Get daily stock market K-line data.

- **Parameters**:
  - `symbol` (string): Stock code (e.g., "000001").
  - `adjust` (string, optional): Adjustment type ("qfq", "hfq", or null). Defaults to "qfq".
  - `start_date` (string, optional): "YYYY-MM-DD".
  - `end_date` (string, optional): "YYYY-MM-DD".

### 2. `get_financial_data`

Get financial report data. Automatically finds the latest available report if not specified.

- **Parameters**:
  - `symbol` (string, optional): Filter by stock code (e.g., "000938").
  - `report_date` (string, optional): Specific report date "YYYYMMDD" (e.g., "20241231").

## Project Structure

```
kitetdx-mcp/
├── src/
│   └── api_server.py    # Main server implementation
├── data/                # Data storage (auto-generated)
├── pyproject.toml       # Project configuration
├── requirements.txt     # Dependency list
└── README.md
```

## License

MIT
