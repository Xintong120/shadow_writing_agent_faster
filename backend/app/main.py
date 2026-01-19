# main.py
# 作用：FastAPI应用入口
# 功能：应用配置、路由注册、WebSocket端点、中间件配置

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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
from app.utils import initialize_key_manager, initialize_mistral_key_manager, initialize_litellm_client
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

# 导入 py-spy 相关工具（通过 subprocess 调用）
import subprocess
import os
import signal
import psutil

PYSPY_AVAILABLE = True  # py-spy 在 requirements-dev.txt 中已安装
print("[MONITOR] py-spy monitoring enabled")

# 自定义异步监控端点（备用方案）
import asyncio
from fastapi import APIRouter
monitor_router = APIRouter(prefix="/api/monitor", tags=["monitor"])

@monitor_router.get("/tasks")
async def get_current_tasks():
    """获取当前运行的异步任务状态"""
    try:
        loop = asyncio.get_running_loop()
        tasks = []

        # 使用基础 asyncio 任务信息 + py-spy 统计
        for task in asyncio.all_tasks(loop):
            coro = task.get_coro()
            coro_name = getattr(coro, '__name__', str(coro))
            tasks.append({
                "id": id(task),
                "name": coro_name,
                "state": "RUNNING" if not task.done() else "DONE",
                "created": getattr(task, '_creation_time', None),
                "coro_name": coro_name,
                "source": "asyncio-basic"
            })

        # 计算统计信息
        running_tasks = [t for t in tasks if t.get('state') == 'RUNNING' or t.get('state') == 'PENDING']
        done_tasks = [t for t in tasks if t.get('state') == 'DONE']

        return {
            "total_tasks": len(tasks),
            "running_tasks": len(running_tasks),
            "done_tasks": len(done_tasks),
            "tasks": tasks,
            "monitor_type": "basic",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_tasks": 0,
            "running_tasks": 0,
            "done_tasks": 0,
            "tasks": [],
            "monitor_type": "error",
            "timestamp": time.time()
        }

@monitor_router.get("/pipeline-status")
async def get_pipeline_status():
    """获取pipeline执行状态"""
    try:
        # 获取所有任务，过滤出活跃的（非完成状态）
        all_tasks = task_manager.tasks
        active_tasks = {
            task_id: task for task_id, task in all_tasks.items()
            if task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]
        }

        pipeline_info = []
        for task_id, task in active_tasks.items():
            pipeline_info.append({
                "task_id": task_id,
                "status": task.status.value,
                "total_urls": task.total,
                "processed_urls": task.current,
                "current_url": task.current_url,
                "results_count": len(task.results),
                "errors_count": len(task.errors),
                "created_at": task.created_at.isoformat() if task.created_at else None
            })

        return {
            "active_pipelines": len(pipeline_info),
            "pipelines": pipeline_info,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": str(e),
            "active_pipelines": 0,
            "pipelines": [],
            "timestamp": time.time()
        }

@monitor_router.post("/pyspy/top")
async def run_pyspy_top(duration: int = 10):
    """运行 py-spy top 分析当前进程的性能"""
    try:
        if not PYSPY_AVAILABLE:
            return {
                "error": "py-spy not available",
                "available": False,
                "timestamp": time.time()
            }

        # 获取当前进程ID
        current_pid = os.getpid()

        # 构建 py-spy top 命令
        cmd = [
            "py-spy", "top",
            "--pid", str(current_pid),
            "--duration", str(duration)
        ]

        print(f"[PYSPY] Running: {' '.join(cmd)}")

        # 执行命令并捕获输出
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 5  # 额外5秒超时
        )

        return {
            "success": True,
            "command": " ".join(cmd),
            "pid": current_pid,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "timestamp": time.time()
        }

    except subprocess.TimeoutExpired:
        return {
            "error": f"py-spy analysis timed out after {duration + 5} seconds",
            "success": False,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False,
            "timestamp": time.time()
        }

@monitor_router.post("/pyspy/record")
async def run_pyspy_record(duration: int = 30, output_file: str = "pyspy_profile.speedscope"):
    """运行 py-spy record 生成性能分析文件"""
    try:
        if not PYSPY_AVAILABLE:
            return {
                "error": "py-spy not available",
                "available": False,
                "timestamp": time.time()
            }

        # 获取当前进程ID
        current_pid = os.getpid()

        # 构建 py-spy record 命令
        cmd = [
            "py-spy", "record",
            "--pid", str(current_pid),
            "--format", "speedscope",
            "--duration", str(duration),
            "--output", output_file
        ]

        print(f"[PYSPY] Running: {' '.join(cmd)}")

        # 执行命令并捕获输出
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 10  # 额外10秒超时
        )

        return {
            "success": True,
            "command": " ".join(cmd),
            "pid": current_pid,
            "duration": duration,
            "output_file": output_file,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "timestamp": time.time()
        }

    except subprocess.TimeoutExpired:
        return {
            "error": f"py-spy recording timed out after {duration + 10} seconds",
            "success": False,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False,
            "timestamp": time.time()
        }

@monitor_router.get("/pyspy/status")
async def get_pyspy_status():
    """获取 py-spy 状态信息"""
    try:
        # 检查 py-spy 是否可用
        result = subprocess.run(
            ["py-spy", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        return {
            "available": True,
            "version": result.stdout.strip(),
            "current_pid": os.getpid(),
            "process_info": {
                "pid": os.getpid(),
                "name": psutil.Process(os.getpid()).name(),
                "cpu_percent": psutil.Process(os.getpid()).cpu_percent(),
                "memory_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            },
            "timestamp": time.time()
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return {
            "available": False,
            "error": "py-spy not installed or not accessible",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "timestamp": time.time()
        }

# 定义 lifespan 事件处理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动逻辑
    print("[STARTUP] 开始初始化应用...")

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

    # 初始化 LiteLLM 全局 HTTP 客户端
    initialize_litellm_client()

    # 启动SSE消息清理任务
    start_cleanup_task()

    # py-spy 监控已启用
    print("[MONITOR] py-spy monitoring enabled")
    print("[MONITOR] HTTP API monitoring available at /api/monitor/")
    print("[MONITOR] Use 'py-spy top --pid $(pgrep -f uvicorn)' for real-time analysis")

    print("[OK] TED Agent API 启动成功！")
    print("[INFO] 访问文档：http://localhost:8000/docs")
    print("[INFO] API v1 端点：http://localhost:8000/api/v1/...")

    yield  # 应用运行中

    # 关闭逻辑
    print("[SHUTDOWN] 开始清理资源...")

    # 清理 HTTP 连接池
    try:
        from app.utils import http_client_manager
        http_client_manager.close()
        print("[SHUTDOWN] HTTP 连接池已清理")
    except Exception as e:
        print(f"[SHUTDOWN] HTTP 连接池清理失败: {e}")

    print("[SHUTDOWN] 资源清理完成")

# 创建FastAPI应用
app = FastAPI(
    title="TED Shadow Writing API",
    description="TED Shadow Writing API",
    version="2.0.0",
    lifespan=lifespan
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
app.include_router(monitor_router)      # 异步监控路由 (/api/monitor/...)

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
