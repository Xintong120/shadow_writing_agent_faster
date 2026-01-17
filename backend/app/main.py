# main.py
# 作用：FastAPI应用入口
# 功能：应用配置、路由注册、WebSocket端点、中间件配置

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import time
import logging
from app.config import settings, validate_config

# 配置日志 - 确保应用日志能正确输出，不被uvicorn覆盖
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # 强制覆盖任何现有的配置
)
logger = logging.getLogger(__name__)

# 确保根logger也设置为INFO级别
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
from app.utils import initialize_key_manager, initialize_mistral_key_manager
from app.sse_manager import sse_manager, start_cleanup_task
from app.task_manager import task_manager
# from app.websocket import ws_manager  # TODO: WebSocket功能暂未实现
from app.enums import TaskStatus, MessageType
from app.routers.core import router as core_router
from app.routers.memory import router as memory_router
from app.routers.config import router as config_router
from app.routers.settings import router as settings_router
from app.monitoring.api_key_dashboard import router as monitoring_router
import asyncio

# 创建FastAPI应用
app = FastAPI(
    title="TED Shadow Writing API",
    description="TED Shadow Writing API",
    version="2.0.0"
)

# 配置CORS（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（按功能分组）
app.include_router(core_router)         # 核心业务路由 (/api/v1/...)
app.include_router(memory_router)       # Memory路由 (/api/memory/...)
app.include_router(config_router)       # 配置路由 (/api/config/...)
app.include_router(settings_router)     # 设置路由 (/api/settings/...)
app.include_router(monitoring_router)   # 监控路由 (/api/monitoring/...)

# 兼容性路由：保留原有路径
@app.get("/health")
def health_check():
    """健康检查（兼容性保留）"""
    return {
        "status": "ok",
        "model": settings.model_name,
        "temperature": settings.temperature,
        "note": "Please use /api/v1/health for new implementations"
    }

# 启动时验证配置
@app.on_event("startup")
async def startup_event():
    # 在Electron环境下跳过API验证（演示模式）
    import os
    if os.getenv("ELECTRON_DEMO") != "true":
        validate_config()
    else:
        print("[DEMO] Electron演示模式，跳过API配置验证")

    # 初始化 API Key 管理器
    initialize_key_manager(cooldown_seconds=60)  # GROQ Key 管理器

    # 初始化 Mistral API Key 管理器（独立）
    if settings.mistral_api_keys:
        initialize_mistral_key_manager(cooldown_seconds=60)

    # 启动SSE消息清理任务
    start_cleanup_task()

    print("[OK] TED Agent API 启动成功！")
    print("[INFO] 访问文档：http://localhost:8000/docs")
    print("[INFO] API v1 端点：http://localhost:8000/api/v1/...")


# ============ SSE处理 ============

# SSE端点 - 替换WebSocket，使用流式响应推送进度消息
@app.get("/api/v1/progress/{task_id}")
async def progress_stream(task_id: str, last_event_id: str | None = None):
    """
    SSE端点，实时推送处理进度，支持断点续传

    使用方法：
        const eventSource = new EventSource('/api/v1/progress/task_123');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Progress:', data);
        };

    支持断点续传：
        const eventSource = new EventSource('/api/v1/progress/task_123', {
            headers: { 'Last-Event-ID': 'last_received_id' }
        });

    消息格式：
        id: message_id
        data: {"type": "started|progress|step|url_completed|completed", ...}

        例如：
        id: task_123_1640995200000
        data: {"type": "started", "timestamp": 1640995200.123}
    """

    async def generate():
        """生成SSE消息流"""
        try:
            # 获取缓存的消息，支持断点续传
            messages = await sse_manager.get_messages(task_id, last_event_id)

            print(f"[SSE] [{task_id}] 发送 {len(messages)} 条缓存消息")

            # 发送缓存的消息
            for message in messages:
                event_data = f"id: {message['id']}\ndata: {json.dumps(message)}\n\n"
                yield event_data

            # 如果没有断点续传，发送连接确认消息
            if not last_event_id:
                connected_message = {
                    "id": f"{task_id}_connected_{int(time.time() * 1000)}",
                    "type": "connected",
                    "task_id": task_id,
                    "message": f"Connected to progress stream for task {task_id}",
                    "timestamp": time.time()
                }
                event_data = f"id: {connected_message['id']}\ndata: {json.dumps(connected_message)}\n\n"
                yield event_data

            # 持续监听新消息（保持连接活跃）
            last_sent_id = messages[-1]['id'] if messages else (last_event_id or "0")

            while True:
                try:
                    # 检查是否有新消息
                    latest_message = await sse_manager.get_latest_message(task_id)
                    if latest_message and latest_message['id'] != last_sent_id:
                        # 发送新消息
                        event_data = f"id: {latest_message['id']}\ndata: {json.dumps(latest_message)}\n\n"
                        yield event_data
                        last_sent_id = latest_message['id']
                        print(f"[SSE] [{task_id}] 发送新消息: {latest_message['type']}")

                        # 如果是完成消息，结束流
                        if latest_message.get('type') == 'completed':
                            break

                    await asyncio.sleep(0.1)  # 短暂延迟，避免CPU占用过高

                except Exception as e:
                    print(f"[SSE] [{task_id}] 流式响应错误: {e}")
                    break

        except Exception as e:
            print(f"[SSE] [{task_id}] SSE端点错误: {e}")
            error_message = {
                "id": f"{task_id}_error_{int(time.time() * 1000)}",
                "type": "error",
                "message": f"SSE stream error: {str(e)}",
                "timestamp": time.time()
            }
            yield f"id: {error_message['id']}\ndata: {json.dumps(error_message)}\n\n"

    # 返回SSE流式响应
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Last-Event-ID"
        }
    )

# WebSocket端点（暂未实现）
# TODO: 实现WebSocket功能用于实时进度推送
# @app.websocket("/ws/progress/{task_id}")
# async def websocket_progress(websocket: WebSocket, task_id: str):
#     pass


# 运行方式：
# uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
