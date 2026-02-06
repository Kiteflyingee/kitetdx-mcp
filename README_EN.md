# kitetdx-mcp

An MCP (Model Context Protocol) server for [kitetdx](https://github.com/Kiteflyingee/kitetdx), providing access to Chinese stock market data and financial reports for LLMs.

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

- Python 3.10 - 3.12 (Recommended)
- `uv` (recommended) or `pip`

## Installation

### Method 1: Using `uv` (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd kitetdx-mcp

# Install dependencies and run (Recommend specifying Python version)
uv run --python 3.10 src/api_server.py
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
This server uses SSE and Streamable HTTP. You need to start `api_server.py` on your server/local machine first, and then connect using `mcp-remote`.

#### 1. Start the Server

Run on your machine:

```bash
# Using uv (Recommended)
uv run --python 3.10 src/api_server.py

# Or using python
python src/api_server.py
```

The server will listen at `http://<server-ip>:8010`.

#### 2. Configure Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kitetdx": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "--allow-http",
        "http://<server-ip>:8010/mcp"
      ]
    }
  }
}
```

Replace `<server-ip>` with your actual IP address (e.g., `http://127.0.0.1:8010/mcp` for local).

> **Note**:
> - The `--allow-http` flag is required when connecting to a remote (non-localhost) HTTP server.
> - Streamable HTTP Endpoint (Current Config): `/mcp`
> - SSE Endpoint: `/sse/`

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

### 3. `get_industries`

Get industry classification list (supports SWS and TDX).

- **Parameters**:
  - `source` (string, optional): Data source, "tdx" (TongdaXin) or "sws" (Shenwan). Defaults to "tdx".
  - `level` (int, optional): Industry level, 1 (Level 1) or 2 (Level 2). Defaults to 1.

### 4. `get_industry_stocks`

Get the list of constituent stocks for a specific industry.

- **Parameters**:
  - `industry_code` (string): Industry code (Txxxx), Block code (88xxxx), or Industry Name.
  - `source` (string, optional): Data source, "tdx" or "sws". Defaults to "tdx".

### 5. `get_stock_industry`

Get industry information for a specific stock.

- **Parameters**:
  - `stock_code` (string): Stock code.
  - `source` (string, optional): Data source, "tdx" or "sws". Defaults to "tdx".

### 6. `get_concept_blocks`

Get TDX local block and concept data.

- **Parameters**:
  - `concept_type` (string, optional): Filter type: "GN" (Concept), "FG" (Style), "ZS" (Index). Defaults to "GN".

### 7. `update_sws_data`

Manually update Shenwan (SWS) industry data. No parameters.


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
