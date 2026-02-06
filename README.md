# kitetdx-mcp

[English](./README_EN.md) | 中文

[kitetdx](https://github.com/Kiteflyingee/kitetdx) 的 MCP (Model Context Protocol) 服务器，为 LLM 提供中国股票市场 K 线数据和财务数据访问能力。

该服务器允许 LLM（如 Claude）实现：
- 获取历史日线 K 线数据（支持复权）。
- 获取详细的财务报表数据。
- 自动每日同步和更新数据。

## 功能特性

- **日线数据**：获取前复权(QFQ)、后复权(HFQ)或不复权的日线数据。
- **财务数据**：获取详细财务指标（每股收益、净资产收益率等）。如果最新财报没有指定股票的数据，会自动向前查找最近可用的财报。
- **自动同步**：内置定时任务（默认每天 18:00）保持本地数据新鲜。
- **高效传输**：使用 Streamable HTTP 传输协议，性能更稳定。
- **零配置数据**：按需自动下载所需的数据文件。

## 环境要求

- Python 3.10 - 3.12 (推荐)
- `uv` (推荐) 或 `pip`

## 安装指南

### 方法 1: 使用 `uv` (推荐)

```bash
# 克隆仓库
git clone <repository-url>
cd kitetdx-mcp

# 安装依赖并运行 (推荐指定 Python 版本)
uv run --python 3.10 src/api_server.py
```

### 方法 2: 使用标准 pip

```bash
# 克隆仓库
git clone <repository-url>
cd kitetdx-mcp

# 安装依赖
pip install -r requirements.txt

# 运行服务器
python src/api_server.py
```

## 配置说明

服务器默认监听 `8010` 端口。可以通过环境变量修改配置：

| 环境变量 | 描述 | 默认值 |
|----------|------|--------|
| `KITETDX_API_PORT` | 服务器监听端口 | `8010` |
| `KITETDX_DIR` | 数据存储目录 | `./data` |
| `KITETDX_ALLOW_ORIGINS` | 允许的跨域来源 | `*` (默认) |

### 安全说明

为了支持从任意 IP 地址（包括 Docker 容器或局域网设备）访问，本服务器默认禁用了 **DNS Rebinding 保护**。请仅在受信任的网络环境中使用。

### Claude Desktop 配置

本服务器使用 Streamable HTTP 传输协议。你需要先在服务器上启动 `api_server.py`，然后通过 `mcp-remote` 连接。

#### 1. 启动服务器

在服务器上运行：

```bash
# 使用 uv (推荐)
uv run --python 3.10 src/api_server.py

# 或使用 python
python src/api_server.py
```

服务器将在 `http://<server-ip>:8010` 上监听。

#### 2. 配置 Claude Desktop

在你的 `claude_desktop_config.json` 中添加如下配置，使用 `mcp-remote` 连接远程服务器：

```json
{
  "mcpServers": {
    "kitetdx": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "--allow-http",
        "http://<server-ip>:8010/sse/"
      ]
    }
  }
}
```

将 `<server-ip>` 替换为你的服务器 IP 地址，例如 `http://192.168.1.100:8010/sse/`。

> **注意**: 
> - 连接远程服务器（非 localhost）时必须添加 `--allow-http` 参数。
> - SSE 端点 (推荐配置): `/sse/`
> - Streamable HTTP 端点: `/mcp`

## 可用工具

### 1. `get_daily_kline`

获取股票日线 K 线数据。

- **参数**:
  - `symbol` (string): 股票代码 (例如 "000001")。
  - `adjust` (string, 可选): 复权方式 ("qfq", "hfq", 或 null)。默认为 "qfq"。
  - `start_date` (string, 可选): 开始日期 "YYYY-MM-DD"。
  - `end_date` (string, 可选): 结束日期 "YYYY-MM-DD"。

### 2. `get_financial_data`

获取财务报表数据。如果不指定日期，会自动查找最新可用的财报。

- **参数**:
  - `symbol` (string, 可选): 股票代码过滤 (例如 "000938")。
  - `report_date` (string, 可选): 指定财报日期 "YYYYMMDD" (例如 "20241231")。

### 3. `get_industries`

获取行业分类列表 (支持申万和通达信)。

- **参数**:
  - `source` (string, 可选): 数据源，"tdx" (通达信) 或 "sws" (申万)。默认为 "tdx"。
  - `level` (int, 可选): 行业级别，1 (一级) 或 2 (二级)。默认为 1。

### 4. `get_industry_stocks`

获取指定行业的成分股列表。

- **参数**:
  - `industry_code` (string): 行业代码 (Txxxx)、板块代码 (88xxxx) 或行业名称。
  - `source` (string, 可选): 数据源，"tdx" 或 "sws"。默认为 "tdx"。

### 5. `get_stock_industry`

获取指定股票的所属行业信息。

- **参数**:
  - `stock_code` (string): 股票代码。
  - `source` (string, 可选): 数据源，"tdx" 或 "sws"。默认为 "tdx"。

### 6. `get_concept_blocks`

获取通达信本地板块与概念数据。

- **参数**:
  - `concept_type` (string, 可选): 筛选类型: "GN" (概念), "FG" (风格), "ZS" (指数)。默认为 "GN"。

### 7. `update_sws_data`

手动更新申万行业数据。无参数。


## 项目结构

```
kitetdx-mcp/
├── src/
│   └── api_server.py    # 服务器核心实现
├── data/                # 数据存储目录 (自动生成)
├── pyproject.toml       # 项目配置
├── requirements.txt     # 依赖列表
├── README.md            # 中文文档
└── README_EN.md         # English Documentation
```

## 许可证

MIT
