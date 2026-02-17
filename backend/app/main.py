# main.py
# FastAPI 应用入口
#
# 职责：
# - 应用配置
# - 路由注册
# - 中间件配置
#
# 历史：
# - 2025-02-09: 重构后，从 718 行精简到 ~120 行
#

import asyncio
import json
import logging
import time
import os
import psutil
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.dependencies import (
    init_dependencies,
    shutdown_dependencies
)
from app.infrastructure.config import validate_config
from app.sse_manager import sse_manager, start_cleanup_task
from app.task_manager import task_manager
from app.enums import TaskStatus
from app.routers.core import router as core_router
from app.routers.memory import router as memory_router
from app.routers.config import router as config_router
from app.routers.settings import router as settings_router
from app.routers.history import router as history_router
from app.routers.dictionary import router as dictionary_router
from app.routers.vocab import router as vocab_router, init_db as init_vocab_db
from app.monitoring.api_key_dashboard import router as monitoring_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

PYSPY_AVAILABLE = True

monitor_router = APIRouter(prefix="/api/monitor", tags=["monitor"])

@monitor_router.get("/tasks")
async def get_current_tasks():
    try:
        loop = asyncio.get_running_loop()
        tasks = []
        for task in asyncio.all_tasks(loop):
            coro = task.get_coro()
            coro_name = getattr(coro, '__name__', str(coro))
            tasks.append({
                "id": id(task),
                "name": coro_name,
                "state": "RUNNING" if not task.done() else "DONE"
            })
        running = [t for t in tasks if t.get('state') in ["RUNNING", "PENDING"]]
        return {"total_tasks": len(tasks), "running_tasks": len(running), "done_tasks": len(tasks) - len(running), "timestamp": time.time()}
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}

@monitor_router.get("/pipeline-status")
async def get_pipeline_status():
    try:
        active = {tid: t for tid, t in task_manager.tasks.items() if t.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]}
        pipelines = [{"task_id": tid, "status": t.status.value, "total": t.total, "processed": t.current} for tid, t in active.items()]
        return {"active_pipelines": len(pipelines), "pipelines": pipelines, "timestamp": time.time()}
    except Exception as e:
        return {"error": str(e), "active_pipelines": 0, "timestamp": time.time()}

@monitor_router.post("/pyspy/top")
async def run_pyspy_top(duration: int = 10):
    try:
        if not PYSPY_AVAILABLE:
            return {"error": "py-spy not available", "timestamp": time.time()}
        current_pid = os.getpid()
        result = subprocess.run(["py-spy", "top", "--pid", str(current_pid), "--duration", str(duration)], capture_output=True, text=True, timeout=duration + 5)
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr, "timestamp": time.time()}
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}

@monitor_router.post("/pyspy/record")
async def run_pyspy_record(duration: int = 30, output_file: str = "pyspy_profile.speedscope"):
    try:
        if not PYSPY_AVAILABLE:
            return {"error": "py-spy not available", "timestamp": time.time()}
        current_pid = os.getpid()
        result = subprocess.run(["py-spy", "record", "--pid", str(current_pid), "--format", "speedscope", "--duration", str(duration), "--output", output_file], capture_output=True, text=True, timeout=duration + 10)
        return {"success": True, "output_file": output_file, "timestamp": time.time()}
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}

@monitor_router.get("/pyspy/status")
async def get_pyspy_status():
    try:
        result = subprocess.run(["py-spy", "--version"], capture_output=True, text=True, timeout=5)
        return {"available": True, "version": result.stdout.strip(), "current_pid": os.getpid(), "timestamp": time.time()}
    except Exception as e:
        return {"available": False, "error": str(e), "timestamp": time.time()}

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
    REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('app_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
    ACTIVE_REQUESTS = Gauge('app_active_requests', 'Active requests')
    CPU_USAGE = Gauge('app_cpu_usage_percent', 'CPU usage')
    MEMORY_USAGE = Gauge('app_memory_usage_mb', 'Memory usage')
except ImportError:
    PROMETHEUS_AVAILABLE = False
    generate_latest = None
    CONTENT_TYPE_LATEST = None

langfuse_handler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[STARTUP] 开始初始化应用...")

    from app.config import settings
    
    if os.getenv("ELECTRON_DEMO") != "true":
        validate_config()

    from app.utils import initialize_key_manager, initialize_mistral_key_manager, initialize_litellm_client
    initialize_key_manager(cooldown_seconds=60)
    if settings.mistral_api_keys:
        initialize_mistral_key_manager(cooldown_seconds=60)
    initialize_litellm_client()

    from app.dependencies import get_llm_service
    try:
        llm_service = get_llm_service()
        if llm_service:
            llm = llm_service.create_shadow_writing_llm()
            print("[OK] LLM Service 预初始化完成")
    except Exception as e:
        print(f"[WARNING] LLM Service 预初始化失败: {e}")

    start_cleanup_task()
    init_vocab_db()
    print("[OK] TED Agent API 启动成功！")
    print("[INFO] 访问文档：http://localhost:8000/docs")

    yield

    print("[SHUTDOWN] 开始清理资源...")
    try:
        from app.utils import http_client_manager
        http_client_manager.close()
        print("[SHUTDOWN] HTTP 连接池已清理")
    except Exception as e:
        print(f"[SHUTDOWN] HTTP 连接池清理失败: {e}")
    shutdown_dependencies()
    print("[SHUTDOWN] 资源清理完成")

app = FastAPI(title="TED Shadow Writing API", description="TED Shadow Writing API", version="2.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if PROMETHEUS_AVAILABLE:
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        start_time = time.time()
        ACTIVE_REQUESTS.inc()
        try:
            response = await call_next(request)
            REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
            return response
        finally:
            ACTIVE_REQUESTS.dec()
            REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(time.time() - start_time)

app.include_router(core_router)
app.include_router(memory_router)
app.include_router(config_router)
app.include_router(settings_router)
app.include_router(history_router)
app.include_router(dictionary_router)
app.include_router(vocab_router)
app.include_router(monitoring_router)
app.include_router(monitor_router)

# Debate module
try:
    from app.routers.debate_router import router as debate_router
    from app.routers.debate_router import add_langserve_routes
    app.include_router(debate_router)
    add_langserve_routes(app)
    print("[OK] Debate module registered")
except Exception as e:
    print(f"[WARNING] Debate module not available: {e}")
    import traceback
    traceback.print_exc()

if PROMETHEUS_AVAILABLE:
    @app.get("/metrics")
    async def metrics():
        CPU_USAGE.set(psutil.cpu_percent())
        MEMORY_USAGE.set(psutil.virtual_memory().used / 1024 / 1024)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/api/v1/progress/preconnect")
async def preconnect_stream():
    async def event_generator():
        yield f"data: {json.dumps({'type': 'preconnect_ready', 'timestamp': time.time()})}\n\n"
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

@app.post("/api/monitoring/sse-events")
async def log_sse_event(event_data: dict):
    print(f"[SSE埋点] {event_data.get('event', 'unknown')}: {event_data.get('data', {})}")
    return {"status": "logged"}

@app.get("/api/v1/progress/{task_id}")
async def progress_stream(task_id: str, last_event_id: str | None = None):
    print(f"[SSE] 新连接请求 - task_id: {task_id}")

    async def generate():
        connected_data = {"id": f"{task_id}_connected_{int(time.time() * 1000)}", "type": "connected", "task_id": task_id, "timestamp": time.time()}
        yield f"data: {json.dumps(connected_data)}\n\n"
        await asyncio.sleep(0)

        messages = await sse_manager.get_messages(task_id, last_event_id)
        for message in messages:
            yield f"id: {message['id']}\ndata: {json.dumps(message)}\n\n"

        last_sent_id = messages[-1]['id'] if messages else (last_event_id or "0")

        while True:
            all_messages = await sse_manager.get_messages(task_id)
            new_messages = [msg for msg in all_messages if msg['id'] > last_sent_id]
            for msg in new_messages:
                yield f"id: {msg['id']}\ndata: {json.dumps(msg)}\n\n"
                last_sent_id = msg['id']
                if msg.get('type') == 'completed':
                    return
            await asyncio.sleep(0.1)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
