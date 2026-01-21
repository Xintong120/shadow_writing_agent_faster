# routers/core.py
# 核心业务路由 - TED处理、搜索、任务管理

from fastapi import APIRouter, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, BackgroundTasks
from app.models import (
    SearchRequest, SearchResponse, TEDCandidate,
    BatchProcessRequest, BatchProcessResponse,
    TaskStatusResponse
)
from app.agent import process_ted_text
from app.tools.ted_txt_parsers import parse_ted_file
from app.workflows import create_search_workflow
from app.task_manager import task_manager
from app.sse_manager import sse_manager
from app.batch_processor import process_urls_batch
from app.enums import TaskStatus, MessageType
import time
import os
import tempfile
import asyncio

router = APIRouter(prefix="/api/v1", tags=["core"])

# ============ 核心业务路由 ============

# 1. 健康检查接口（移到v1，但保留原有路径兼容性）
@router.get("/health")
def health_check():
    """健康检查"""
    from app.config import settings
    return {
        "status": "ok",
        "model": settings.model_name,
        "temperature": settings.temperature,
        "version": "v1"
    }

# 2. 文件上传处理接口
@router.post("/process-file", response_model=dict)
async def process_file(file: UploadFile = File(...)):
    """
    上传TED txt文件并处理

    请求格式：
        - 文件类型：.txt
        - 文件格式：TED演讲文本（包含Title, Speaker, Transcript等字段）

    返回格式：
        {
            "success": true,
            "ted_info": {...},
            "results": [...],
            "result_count": 5,
            "processing_time": 12.34
        }
    """
    # 验证文件类型
    if not file.filename or not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="只支持 .txt 文件格式"
        )

    # 记录处理时间
    start_time = time.time()

    try:
        # 1. 创建临时文件保存上传内容
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            # 读取上传的文件内容
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # 2. 调用 parse_ted_file() 解析文件
        ted_data = parse_ted_file(temp_file_path)

        # 3. 删除临时文件
        os.unlink(temp_file_path)

        # 4. 验证解析结果
        if not ted_data:
            raise HTTPException(
                status_code=400,
                detail="文件解析失败：请检查文件格式是否正确"
            )

        # 5. 提取 transcript
        transcript = ted_data.transcript

        if not transcript or len(transcript.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Transcript 内容太短，至少需要50个字符"
            )

        # 6. 调用 process_ted_text() 处理（传递 TED 元数据）
        result = process_ted_text(
            text=transcript,
            target_topic="",
            ted_title=ted_data.title,
            ted_speaker=ted_data.speaker,
            ted_url=ted_data.url
        )

        # 7. 添加 TED 元数据和处理时间
        result["ted_info"] = {
            "title": ted_data.title,
            "speaker": ted_data.speaker,
            "url": ted_data.url,
            "duration": ted_data.duration,
            "views": ted_data.views,
            "transcript_length": len(transcript)
        }
        result["processing_time"] = time.time() - start_time

        return result

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        # 捕获其他异常
        raise HTTPException(
            status_code=500,
            detail=f"处理文件时发生错误: {str(e)}"
        )

# 3. 测试Groq连接（可选）
@router.get("/test-groq")
def test_groq_connection():
    """测试Groq API连接"""
    from app.config import settings
    if not settings.groq_api_key or settings.groq_api_key == "":
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY未配置"
        )

    return {
        "status": "configured",
        "model": settings.model_name,
        "api_key_length": len(settings.groq_api_key)
    }


# ============ 搜索和批量处理端点 ============

# 4. 搜索TED演讲
@router.post("/search-ted", response_model=SearchResponse)
async def search_ted(request: SearchRequest):
    """
    搜索TED演讲，返回候选列表

    请求格式：
        {
            "topic": "AI ethics",
            "user_id": "user123"  // 可选
        }

    返回格式：
        {
            "success": true,
            "candidates": [
                {
                    "title": "...",
                    "speaker": "...",
                    "url": "...",
                    "duration": "...",
                    "views": "...",
                    "description": "...",
                    "relevance_score": 0.95
                },
                ...
            ],
            "search_context": {
                "original_topic": "AI ethics",
                "optimized_query": "artificial intelligence ethics morality"
            },
            "total": 10
        }
    """
    try:
        print(f"\n[API] 搜索TED演讲: {request.topic}")

        # 使用Communication Agent搜索
        workflow = create_search_workflow()

        # 初始状态
        initial_state = {
            "topic": request.topic,
            "user_id": request.user_id,
            "ted_candidates": [],
            "selected_ted_url": None,
            "awaiting_user_selection": False,
            "search_context": {},
            "file_path": None,
            "text": "",
            "target_topic": "",
            "ted_title": None,
            "ted_speaker": None,
            "ted_url": None,
            "semantic_chunks": [],
            "raw_shadows_chunks": [],
            "validated_shadow_chunks": [],
            "quality_shadow_chunks": [],
            "failed_quality_chunks": [],
            "corrected_shadow_chunks": [],
            "final_shadow_chunks": [],
            "current_node": "",
            "processing_logs": [],
            "errors": [],
            "error_message": None
        }

        # 获取全局Langfuse处理器
        from app.main import langfuse_handler

        # 运行工作流（带Langfuse监控）
        if langfuse_handler:
            from langchain_core.runnables import RunnableConfig
            from typing import cast
            from app.state import Shadow_Writing_State
            config = cast(RunnableConfig, {"callbacks": [langfuse_handler]})
            result = workflow.invoke(cast(Shadow_Writing_State, initial_state), config=config)
        else:
            from app.state import Shadow_Writing_State
            from typing import cast
            result = workflow.invoke(cast(Shadow_Writing_State, initial_state))

        # 提取候选列表
        candidates_raw = result.get("ted_candidates", [])
        search_context = result.get("search_context", {})

        # 转换为TEDCandidate格式
        candidates = []
        for c in candidates_raw:
            try:
                candidates.append(TEDCandidate(
                    title=c.get("title", ""),
                    speaker=c.get("speaker", "Unknown"),
                    url=c.get("url", ""),
                    duration=c.get("duration", ""),
                    views=c.get("views"),
                    description=c.get("description", ""),
                    relevance_score=c.get("score", 0.0)
                ))
            except Exception as e:
                print(f"[WARNING] 候选转换失败: {e}")
                continue

        print(f"[API] 找到 {len(candidates)} 个候选")

        return SearchResponse(
            success=True,
            candidates=candidates,
            search_context=search_context,
            total=len(candidates)
        )

    except Exception as e:
        print(f"[ERROR] 搜索失败: {e}")
        return SearchResponse(
            success=False,
            candidates=[],
            search_context={"error": str(e)},
            total=0
        )


# 5. 批量处理选中的TED URLs
@router.post("/process-batch", response_model=BatchProcessResponse)
async def process_batch(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """
    批量处理选中的TED URLs（异步）

    请求格式：
        {
            "urls": [
                "https://www.ted.com/talks/...",
                "https://www.ted.com/talks/...",
                ...
            ],
            "user_id": "user123"  // 可选
        }

    返回格式：
        {
            "success": true,
            "task_id": "uuid-string",
            "total": 3,
            "message": "Processing started. Connect to /ws/progress/{task_id} for updates."
        }

    说明：
        - 返回task_id后立即返回
        - 使用WebSocket连接 /ws/progress/{task_id} 获取实时进度
    """
    try:
        print(f"\n[API] 批量处理 {len(request.urls)} 个URLs")

        # 创建任务
        task_id = task_manager.create_task(request.urls, request.user_id or "")

        # 后台异步处理
        background_tasks.add_task(process_urls_batch, task_id, request.urls)

        return BatchProcessResponse(
            success=True,
            task_id=task_id,
            total=len(request.urls),
            message=f"Processing started. Connect to /ws/progress/{task_id} for updates."
        )

    except Exception as e:
        print(f"[ERROR] 创建任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create task: {str(e)}"
        )


# 6. 查询任务状态（备选，供轮询使用）
@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态（轮询方式）

    返回格式：
        {
            "task_id": "uuid",
            "status": "processing",
            "total": 3,
            "current": 1,
            "urls": [...],
            "results": [...],
            "errors": [...],
            "current_url": "https://..."
        }
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,  # 转换枚举为字符串
        total=task.total,
        current=task.current,
        urls=task.urls,
        results=task.results,
        errors=task.errors,
        current_url=task.current_url
    )


# ============ WebSocket处理 ============

# 全局WebSocket路由（需要在main.py中特殊处理）
def get_websocket_router():
    """返回WebSocket路由（因为FastAPI APIRouter不支持WebSocket）"""
    return None

# WebSocket端点需要在main.py中直接定义，不能放在APIRouter中
