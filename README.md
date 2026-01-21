# kitetdx MCP Server

为 kitetdx 提供 MCP (Model Context Protocol) 服务，使 LLM 能够访问 A 股 K 线数据和财务报表。

**支持局域网共享** - 您运行 API 服务器，局域网伙伴配置 MCP Wrapper 即可使用。

---

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    服务器端 (您的电脑)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  FastAPI HTTP Server (端口 8000)                 │   │
│  │  - /api/daily_kline                              │   │
│  │  - /api/financial_data                           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP (局域网)
                          ▼
              ┌───────────────────────┐
              │  局域网伙伴的电脑      │
              │  Claude Desktop       │
              │    + MCP Wrapper      │
              └───────────────────────┘
```

---

## 服务器端 (您的电脑)

### 启动 API 服务器
```bash
conda activate ai_trade
cd kitetdx-mcp
export KITETDX_DIR="/stock/new_tdx"
python src/kitetdx_mcp/api_server.py
```

服务器将在 `http://YOUR_IP:8010` 上运行。

### 验证

浏览器访问 `http://localhost:8010/docs` 查看 API 文档。

---

## Claude Desktop 配置 (推荐)

使用 SSE (Server-Sent Events) 方式配置，无需下载任何脚本，直接连接服务器。

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kitetdx": {
      "url": "http://服务器IP:8010/sse"
    }
  }
}
```

> 将 `服务器IP` 替换为运行 API 服务器的电脑 IP 地址。

---

## 提供的 Tools

| Tool | 功能 |
| :--- | :--- |
| `get_daily_kline` | 获取股票日线数据 (支持前/后复权) |
| `get_financial_data` | 获取指定报告期财务数据 |

---

## 开发与脚本运行 (Legacy)

如果您仍想通过本地脚本运行 MCP (stdio 模式):

```bash
conda activate ai_trade
python src/kitetdx_mcp/api_server.py # 必须先启动服务器
```

> **注意**：默认情况下，程序会在当前目录下创建 `data` 文件夹作为数据存储目录。
