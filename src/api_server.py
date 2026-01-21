import os
import datetime
import contextlib
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn
import pandas as pd

from kitetdx.reader import Reader
from kitetdx.affair import Affair
from mootdx.logger import logger
from mcp.server.fastmcp import FastMCP

from mcp.server.transport_security import TransportSecuritySettings

# 初始化 FastMCP
mcp = FastMCP(
    "kitetdx", 
    streamable_http_path="/", 
    sse_path="/", 
    stateless_http=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)
)

# 创建 MCP 应用（先创建，以便在 lifespan 中使用）
mcp_http_app = mcp.streamable_http_app()
mcp_sse_app = mcp.sse_app()

# 创建 lifespan 上下文管理器
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用生命周期，确保 MCP 会话正确初始化"""
    async with mcp.session_manager.run():
        yield

app = FastAPI(title="kitetdx API Server", lifespan=lifespan)

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取通达信目录 (默认为项目根目录下的 data)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TDX_DIR = os.environ.get("KITETDX_DIR", os.path.join(PROJECT_ROOT, "data"))
if not os.path.exists(TDX_DIR):
    os.makedirs(TDX_DIR, exist_ok=True)
reader = Reader.factory(market='std', tdxdir=TDX_DIR)

# 初始化调度器
scheduler = BackgroundScheduler()

# 财务数据下载目录 (与 Affair.parse 的默认目录保持一致)
FINANCIAL_DIR = os.path.join(TDX_DIR, "T0002", "hq_cache")

def check_and_download_financial_data():
    """
    检查并下载所有缺失的财务数据文件。
    
    直接从 Affair.files() 获取远程可用的所有文件列表，
    并下载本地缺失的文件到 FINANCIAL_DIR。
    """
    logger.info("开始全面检查并同步财务数据文件...")
    
    # 确保下载目录存在
    os.makedirs(FINANCIAL_DIR, exist_ok=True)
    
    # 获取远程可用的文件列表
    try:
        remote_files = Affair.files()
        if not remote_files:
            logger.warning("远程服务器未返回任何可用财务文件")
            return {"downloaded": 0, "total_remote": 0}
            
        logger.info(f"远程可用财务文件数量: {len(remote_files)}")
    except Exception as e:
        logger.error(f"获取远程文件列表失败: {e}")
        return {"error": str(e), "downloaded": 0}
    
    downloaded_count = 0
    missing_files = []
    
    for file_info in remote_files:
        filename = file_info.get('filename')
        if not filename:
            continue
            
        local_path = os.path.join(FINANCIAL_DIR, filename)
        
        # 检查本地是否存在，如果存在则跳过
        if os.path.exists(local_path):
            continue
        
        # 下载缺失的文件
        logger.info(f"正在下载财务文件: {filename}")
        try:
            Affair.fetch(downdir=FINANCIAL_DIR, filename=filename)
            downloaded_count += 1
        except Exception as e:
            logger.error(f"下载 {filename} 失败: {e}")
            missing_files.append(filename)
    
    logger.info(f"同步完成，本轮共下载了 {downloaded_count} 个文件")
    return {
        "downloaded": downloaded_count, 
        "total_remote": len(remote_files),
        "missing": missing_files
    }

def scheduled_update():
    """定时更新任务"""
    logger.info("开始执行定时数据更新任务 (18:00)...")
    try:
        # 更新 K 线数据
        reader.update_data()
        logger.info("K 线数据更新完成")
        
        # 检查并下载缺失的财务数据
        result = check_and_download_financial_data()
        logger.info(f"财务数据更新结果: {result}")
        
        logger.info("定时数据更新任务完成")
    except Exception as e:
        logger.error(f"定时数据更新任务失败: {e}")

# 每晚 18:00 执行更新
scheduler.add_job(scheduled_update, 'cron', hour=18, minute=0)
scheduler.start()


# --- MCP Tools ---

@mcp.tool(name="get_daily_kline")
def get_daily_kline_tool(
    symbol: str,
    adjust: Optional[str] = 'qfq',
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    获取股票日线数据
    
    Args:
        symbol: 股票代码，如 '000001', '600036'
        adjust: 复权方式，'qfq' 前复权，'hfq' 后复权，None 不复权
        start_date: 开始日期，格式 'YYYY-MM-DD'，可选
        end_date: 结束日期，格式 'YYYY-MM-DD'，可选
    """
    try:
        df = reader.daily(symbol=symbol, adjust=adjust)
        if df is None or df.empty:
            return f"未找到股票代码 {symbol} 的数据"
        
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        # 默认最近 100 个交易日
        if not start_date and not end_date:
            df = df.tail(100)
            
        df = df.reset_index()
        if 'date' not in df.columns and 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'date'})
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
        import json
        return json.dumps(df.to_dict(orient="records"), ensure_ascii=False)
    except Exception as e:
        return f"获取数据失败: {str(e)}"

@mcp.tool(name="get_financial_data")
def get_financial_data_tool(
    report_date: Optional[str] = None,
    symbol: Optional[str] = None
) -> str:
    """
    获取财务数据。服务器会自动获取最新可用的财报数据。
    
    如果不指定 report_date，服务器会自动查找并返回最新有数据的财报文件。
    财报通常在每年的 3月31日(一季报)、6月30日(中报)、9月30日(三季报)、12月31日(年报) 发布。
    
    Args:
        report_date: 报告日期，格式 'YYYYMMDD'，可选。如 '20241231' (2024年报), '20240630' (2024中报)
                     不指定时自动返回最新可用财报
        symbol: 股票代码，可选。如 '000938' 查询紫光股份。如果指定则只返回该股票的数据
    
    Returns:
        JSON 格式的财务数据，包含基本每股收益、净资产收益率等财务指标
    """
    try:
        # 获取所有可用的财务文件，按日期降序排列
        all_files = sorted(
            [f for f in os.listdir(FINANCIAL_DIR) if f.startswith('gpcw') and f.endswith('.zip')],
            reverse=True  # 最新的在前
        )
        
        if not all_files:
            return "暂无财务数据，请先执行同步"
        
        # 如果指定了日期，尝试使用该日期
        if report_date:
            target_filename = f"gpcw{report_date}.zip"
            if target_filename in all_files:
                files_to_try = [target_filename]
            else:
                return f"未找到 {report_date} 的财务数据文件"
        else:
            # 未指定日期，按最新到最旧的顺序尝试
            files_to_try = all_files
        
        # 尝试解析文件，如果为空或指定股票不存在则继续尝试下一个
        for filename in files_to_try:
            logger.info(f"尝试解析财务文件: {filename}")
            try:
                df = Affair.parse(downdir=FINANCIAL_DIR, filename=filename)
            except ValueError as ve:
                logger.warning(f"解析 {filename} 失败: {ve}")
                continue
                
            if df is None or df.empty:
                logger.info(f"财务文件 {filename} 内容为空，尝试下一个...")
                continue
            
            # 确保 code 是列而不是索引
            df = df.reset_index()
            
            # 如果指定了 symbol，过滤并检查是否有数据
            if symbol:
                df_filtered = df[df['code'].astype(str).str.contains(symbol)]
                if df_filtered.empty:
                    logger.info(f"财务文件 {filename} 中没有 {symbol} 的数据，尝试下一个...")
                    continue
                df = df_filtered
            
            # 找到有数据的文件
            logger.info(f"成功解析财务文件: {filename}，共 {len(df)} 条记录")
            
            # 如果指定了 report_date，尝试在该文件中进一步过滤
            if report_date:
                if 'report_date' in df.columns:
                    df = df[df['report_date'] == report_date]
                elif 'date' in df.columns:
                    df = df[df['date'] == report_date]
            
            import json
            return json.dumps(df.head(1000).to_dict(orient="records"), ensure_ascii=False)
        
        # 所有文件都为空
        return "所有财务数据文件均为空，请检查数据同步"
    except Exception as e:
        logger.exception("获取财务数据失败")
        return f"获取财务数据失败: {str(e)}"

# --- Mount MCP Server ---
# 将 MCP streamable HTTP 应用挂载到 FastAPI /mcp
app.mount("/mcp", mcp_http_app)
# 将 MCP SSE 应用挂载到 FastAPI /sse
app.mount("/sse", mcp_sse_app)

# --- Original API Endpoints ---
async def get_daily_kline(
    symbol: str,
    adjust: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """获取股票日线数据"""
    try:
        # 获取 K 线数据，reader.daily 已处理复权
        df = reader.daily(symbol=symbol, adjust=adjust)
        
        if df is None or df.empty:
            return {"error": f"未找到股票代码 {symbol} 的数据"}
        
        # 日期过滤
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
            
        # 转换格式
        df = df.reset_index()
        # 确保日期列名为 date 且为字符串
        if 'date' not in df.columns and 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'date'})
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
        return {"data": df.to_dict(orient="records")}
        
    except Exception as e:
        logger.error(f"获取 K 线数据失败: {e}")
        return {"error": str(e)}

@app.get("/api/financial_data")
async def get_financial_data(
    report_date: Optional[str] = None,
    symbol: Optional[str] = None
):
    """获取财务数据"""
    try:
        filename = None
        if report_date:
            filename = f"gpcw{report_date}.zip"
        
        if not filename:
            files = [f for f in os.listdir(FINANCIAL_DIR) if f.startswith('gpcw') and f.endswith('.zip')]
            if files:
                filename = sorted(files)[-1]
        
        if not filename:
            return {"error": "暂无财务数据，请先执行同步"}

        df = Affair.parse(downdir=FINANCIAL_DIR, filename=filename)
        
        if df is None or df.empty:
            return {"error": f"财务文件 {filename} 为空"}
        
        # 确保 code 是列而不是索引
        df = df.reset_index()
        
        # 过滤
        if symbol:
            # mootdx 返回的 code 可能是 '600000' 或 'sh600000'
            df = df[df['code'].astype(str).str.contains(symbol)]
            
        if report_date:
            # 报告日期通常在 'pub_date' 或其他列，取决于具体格式
            # 这里根据 mootdx 的常见字段过滤
            if 'report_date' in df.columns:
                df = df[df['report_date'] == report_date]
            elif 'date' in df.columns:
                df = df[df['date'] == report_date]
                
        return {"data": df.head(1000).to_dict(orient="records")} # 限制返回数量避免过大
        
    except Exception as e:
        logger.error(f"获取财务数据失败: {e}")
        return {"error": str(e)}

@app.post("/api/sync_financial")
async def sync_financial():
    """手动触发财务数据同步"""
    try:
        result = check_and_download_financial_data()
        return result
    except Exception as e:
        logger.error(f"手动同步财务数据失败: {e}")
        return {"error": str(e)}

@app.get("/api/status")
async def get_status():
    """获取服务器状态"""
    next_run = scheduler.get_jobs()[0].next_run_time if scheduler.get_jobs() else None
    return {
        "status": "running",
        "tdx_dir": TDX_DIR,
        "financial_dir": FINANCIAL_DIR,
        "mcp_sse_url": "/sse",
        "next_update": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "not scheduled"
    }

if __name__ == "__main__":
    # 默认运行在 8010 端口
    port = int(os.environ.get("KITETDX_API_PORT", 8010))
    uvicorn.run(app, host="0.0.0.0", port=port)
