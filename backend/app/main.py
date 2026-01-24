# main.py
# 作用：FastAPI应用入口
# 功能：应用配置、路由注册、WebSocket端点、中间件配置

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import time
import logging
from app.config import settings, validate_config

# Prometheus监控指标
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True

    # 定义业务指标
    REQUEST_COUNT = Counter('app_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('app_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])
    ERROR_COUNT = Counter('app_errors_total', 'Total number of errors', ['method', 'endpoint', 'status'])

    # 系统指标
    CPU_USAGE = Gauge('app_cpu_usage_percent', 'CPU usage percentage')
    MEMORY_USAGE = Gauge('app_memory_usage_mb', 'Memory usage in MB')
    ACTIVE_REQUESTS = Gauge('app_active_requests', 'Number of active requests')

    print("[MONITOR] Prometheus metrics enabled")
except ImportError:
    PROMETHEUS_AVAILABLE = False
    generate_latest = None
    CONTENT_TYPE_LATEST = None
    print("[MONITOR] Prometheus client not available, metrics disabled")

# Langfuse初始化
langfuse_handler = None
if settings.langfuse_enabled and settings.langfuse_public_key and settings.langfuse_secret_key:
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        # 初始化Langfuse客户端
        langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_base_url
        )

        # 创建回调处理器
        langfuse_handler = CallbackHandler()
        print("[LANGFUSE] Langfuse monitoring enabled")
    except Exception as e:
        print(f"[LANGFUSE] Failed to initialize Langfuse: {e}")
        langfuse_handler = None
else:
    print("[LANGFUSE] Langfuse monitoring disabled")

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

# 添加Prometheus监控中间件
if PROMETHEUS_AVAILABLE:
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        start_time = time.time()
        ACTIVE_REQUESTS.inc()

        try:
            response = await call_next(request)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            return response
        except Exception as e:
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
            raise
        finally:
            ACTIVE_REQUESTS.dec()
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(time.time() - start_time)

# 注册路由（按功能分组）
app.include_router(core_router)         # 核心业务路由 (/api/v1/...)
app.include_router(memory_router)       # Memory路由 (/api/memory/...)
app.include_router(config_router)       # 配置路由 (/api/config/...)
app.include_router(settings_router)     # 设置路由 (/api/settings/...)
app.include_router(monitoring_router)   # 监控路由 (/api/monitoring/...)
app.include_router(monitor_router)      # 异步监控路由 (/api/monitor/...)


# Prometheus指标端点
if PROMETHEUS_AVAILABLE:
    @app.get("/metrics")
    async def metrics():
        """Prometheus指标收集端点"""
        # 更新系统指标
        CPU_USAGE.set(psutil.cpu_percent())
        MEMORY_USAGE.set(psutil.virtual_memory().used / 1024 / 1024)

        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

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

# 预连接SSE端点 - 用于提前建立连接
@app.get("/api/v1/progress/preconnect")
async def preconnect_stream():
    """
    预连接SSE端点，用于提前建立SSE连接，避免处理时的连接延迟

    返回心跳消息保持连接活跃
    """

    async def event_generator():
        # 发送连接确认
        yield f"data: {json.dumps({'type': 'preconnect_ready', 'timestamp': time.time()})}\n\n"

        # 保持连接活跃，定期发送心跳
        while True:
            await asyncio.sleep(30)  # 每30秒发送心跳
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Last-Event-ID"
        }
    )

# SSE埋点监控端点
@app.post("/api/monitoring/sse-events")
async def log_sse_event(event_data: dict):
    """
    记录SSE事件埋点数据

    用于监控SSE连接状态、性能指标等
    """
    try:
        event_name = event_data.get('event', 'unknown')
        data = event_data.get('data', {})

        print(f"[SSE埋点] {event_name}: {data}")

        # 这里可以保存到数据库、日志系统或监控平台
        # 暂时只打印到控制台，便于调试

        return {"status": "logged", "event": event_name}

    except Exception as e:
        print(f"[SSE埋点错误] {e}")
        return {"status": "error", "message": str(e)}

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

    # 详细的连接诊断日志
    request_start_time = time.time()
    print("\n[SSE诊断] =========================================")
    print(f"[SSE诊断] 新SSE连接请求 - 任务ID: {task_id}")
    print(f"[SSE诊断] 请求开始时间: {time.strftime('%H:%M:%S', time.localtime(request_start_time))}")
    print(f"[SSE诊断] 请求时间戳: {request_start_time}")
    print(f"[SSE诊断] last_event_id参数: {last_event_id}")
    print(f"[SSE诊断] 请求URL: /api/v1/progress/{task_id}")
    print(f"[SSE诊断] 当前活跃任务数量: {sse_manager.get_active_tasks_count()}")
    print(f"[SSE诊断] 当前任务消息数量: {sse_manager.get_task_message_count(task_id)}")

    # 检查任务是否存在于task_manager中
    task_info = task_manager.get_task(task_id)
    if task_info:
        print(f"[SSE诊断] 任务状态: {task_info.status.value}")
        print(f"[SSE诊断] 任务URL数量: {task_info.total}")
        print(f"[SSE诊断] 已处理数量: {task_info.current}")
        print(f"[SSE诊断] 当前URL: {task_info.current_url}")
    else:
        print(f"[SSE诊断] 警告: 任务 {task_id} 在task_manager中不存在")

    async def generate():
        """生成SSE消息流"""
        stream_start_time = time.time()
        print(f"[SSE诊断] 流生成器启动 - 耗时: {stream_start_time - request_start_time:.3f}秒")

        try:
            # ============ 立即发送连接确认消息，让前端知道连接已建立 ============
            # 简化格式，直接使用data:前缀，符合SSE规范
            connected_data = {
                "id": f"{task_id}_connected_{int(time.time() * 1000)}",
                "type": "connected",
                "task_id": task_id,
                "message": f"Connected to progress stream for task {task_id}",
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(connected_data)}\n\n"
            print(f"[SSE] 立即发送连接确认消息 - 简化格式")

            # 让事件循环处理，确保消息发送
            await asyncio.sleep(0)

            # 获取缓存的消息，支持断点续传
            get_messages_start = time.time()
            messages = await sse_manager.get_messages(task_id, last_event_id)
            get_messages_duration = time.time() - get_messages_start

            print(f"[SSE诊断] 获取缓存消息完成 - 数量: {len(messages)}, 耗时: {get_messages_duration:.3f}秒")

            if messages:
                print(f"[SSE诊断] 缓存消息详情:")
                for i, msg in enumerate(messages[:5]):  # 只显示前5条
                    print(f"  [{i+1}] 类型: {msg.get('type')}, ID: {msg.get('id')}, 时间戳: {msg.get('timestamp')}")

            # 发送缓存的消息
            send_cached_start = time.time()
            cached_count = 0
            for message in messages:
                event_data = f"id: {message['id']}\ndata: {json.dumps(message)}\n\n"
                yield event_data
                cached_count += 1

            send_cached_duration = time.time() - send_cached_start
            print(f"[SSE诊断] 发送缓存消息完成 - 发送数量: {cached_count}, 耗时: {send_cached_duration:.3f}秒")

            # 持续监听新消息（保持连接活跃）
            last_sent_id = messages[-1]['id'] if messages else (last_event_id or "0")
            message_check_count = 0
            new_messages_sent = 0

            print(f"[SSE诊断] 开始监听新消息 - 初始last_sent_id: {last_sent_id}")

            while True:
                try:
                    message_check_count += 1

                    # 检查是否有新消息
                    check_start = time.time()
                    latest_message = await sse_manager.get_latest_message(task_id)
                    check_duration = time.time() - check_start

                    if latest_message and latest_message['id'] != last_sent_id:
                        # 发送新消息
                        send_msg_start = time.time()
                        event_data = f"id: {latest_message['id']}\ndata: {json.dumps(latest_message)}\n\n"
                        yield event_data
                        send_duration = time.time() - send_msg_start

                        new_messages_sent += 1
                        last_sent_id = latest_message['id']

                        print(f"[SSE诊断] 发送新消息 #{new_messages_sent} - 类型: {latest_message.get('type')}, ID: {latest_message['id']}, 检查耗时: {check_duration:.3f}秒, 发送耗时: {send_duration:.3f}秒")

                        # 如果是完成消息，结束流
                        if latest_message.get('type') == 'completed':
                            total_stream_duration = time.time() - stream_start_time
                            print(f"[SSE诊断] 检测到完成消息，结束流 - 总流持续时间: {total_stream_duration:.3f}秒")
                            print(f"[SSE诊断] 消息检查次数: {message_check_count}, 新消息数量: {new_messages_sent}")
                            break

                    # 每100次检查输出一次状态
                    if message_check_count % 100 == 0:
                        elapsed = time.time() - stream_start_time
                        print(f"[SSE诊断] 状态更新 - 检查次数: {message_check_count}, 新消息: {new_messages_sent}, 持续时间: {elapsed:.1f}秒")

                    await asyncio.sleep(0.1)  # 短暂延迟，避免CPU占用过高

                except Exception as e:
                    error_time = time.time() - stream_start_time
                    print(f"[SSE诊断] 流式响应错误 - 发生时间: {error_time:.3f}秒, 错误: {e}")
                    break

        except Exception as e:
            error_time = time.time() - stream_start_time
            print(f"[SSE诊断] SSE端点错误 - 发生时间: {error_time:.3f}秒, 错误: {e}")
            error_message = {
                "id": f"{task_id}_error_{int(time.time() * 1000)}",
                "type": "error",
                "message": f"SSE stream error: {str(e)}",
                "timestamp": time.time()
            }
            yield f"id: {error_message['id']}\ndata: {json.dumps(error_message)}\n\n"

    # 返回SSE流式响应
    print(f"[SSE诊断] 返回StreamingResponse - 请求总耗时: {time.time() - request_start_time:.3f}秒")
    print(f"[SSE诊断] =========================================")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",  # 保持SSE媒体类型，因为我们发送的是SSE格式数据
        headers={
            "Cache-Control": "no-cache",  # 仅保留必要的缓存控制
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
