# routers/core.py
# 核心业务路由 - TED处理、搜索、任务管理

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from typing import Dict, Any, List, Optional
from app.models import (
    SearchRequest, SearchResponse, TEDCandidate,
    BatchProcessRequest, BatchProcessResponse,
    TaskStatusResponse, TaskCreateResponse, TaskDeleteResponse
)
from app.agent import process_ted_text
from app.tools.ted_txt_parsers import parse_ted_file
from app.workflows import create_search_workflow
from app.sse_manager import sse_manager
from app.batch_processor import process_urls_batch
from app.enums import TaskStatus, MessageType
from app.db import task_db, history_db, TaskStatus as DBTaskStatus
import time
import os
import tempfile
import asyncio
import uuid

router = APIRouter(prefix="/api/v1", tags=["core"])

# ============ 核心业务路由 ============

async def _run_processing_workflow(
    transcript: str,
    ted_data,
    task_id: str,
    is_batch: bool = False
):
    """内部：运行处理流程，同时更新 SSE 和数据库"""
    print(f"[WORKFLOW START] task_id: {task_id}")

    try:
        task_db.update_progress(task_id, DBTaskStatus.PARSING.value, 0, 1, "解析文件")

        await sse_manager.add_message(task_id, {
            "type": "processing_started",
            "message": "开始处理文件",
            "timestamp": time.time()
        })

        from app.agent import process_ted_text_stream
        results = []

        async for chunk_data in process_ted_text_stream(
            transcript, "", ted_data.title, ted_data.speaker, ted_data.url, task_id
        ):
            data_type = chunk_data.get("type")

            # 处理语义分块完成事件
            if data_type == "semantic_chunks_completed":
                total_chunks = chunk_data.get("total_chunks", 3)
                # 更新 chunks 总数，开始 shadow_writing 阶段
                task_db.update_chunks_info(task_id, total_chunks, completed_chunks=0)
                print(f"[WORKFLOW] 语义分块完成，总共 {total_chunks} 个块")
                continue

            # 处理每个 chunk 完成
            if data_type == "chunk_completed":
                results.append(chunk_data["result"])
                print(f"[WORKFLOW] 收到 chunk {len(results)}/{chunk_data.get('total_chunks', len(results))}")

        # 所有 chunks 完成，更新状态
        await sse_manager.add_message(task_id, {
            "type": "chunking_completed",
            "total_chunks": len(results),
            "message": f"语义分块和并行处理完成，共生成 {len(results)} 个结果",
            "timestamp": time.time()
        })

        task_db.update(task_id, {
            "status": DBTaskStatus.QUALITY_CHECK.value,
            "current_step": "质量检查",
            "progress": 80
        })

        await asyncio.sleep(0.5)

        task_db.update(task_id, {
            "status": DBTaskStatus.COMPLETED.value,
            "current_step": "完成",
            "progress": 100,
            "result": str(results)
        })

        await sse_manager.add_message(task_id, {
            "type": "processing_completed",
            "results": results,
            "result_count": len(results),
            "timestamp": time.time()
        })

        record_id = str(uuid.uuid4())
        history_db.create(
            record_id=record_id,
            task_id=task_id,
            ted_title=ted_data.title,
            ted_speaker=ted_data.speaker,
            ted_url=ted_data.url,
            ted_duration=ted_data.duration,
            ted_views=str(ted_data.views) if ted_data.views else None,
            result={"chunks": results},
            transcript=transcript
        )

    except Exception as e:
        error_msg = str(e)
        task_db.update(task_id, {
            "status": DBTaskStatus.FAILED.value,
            "current_step": "失败",
            "error": error_msg
        })
        await sse_manager.add_message(task_id, {
            "type": "error",
            "message": error_msg,
            "timestamp": time.time()
        })


# 1. 创建任务（文件上传）
@router.post("/tasks", response_model=TaskCreateResponse)
async def create_task(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    创建处理任务（文件上传）

    - 立即返回 task_id
    - 使用 GET /api/v1/tasks/{task_id} 轮询进度
    """
    if not file.filename or not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="只支持 .txt 文件格式")

    try:
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        ted_data = parse_ted_file(temp_file_path)
        os.unlink(temp_file_path)

        if not ted_data:
            raise HTTPException(status_code=400, detail="文件解析失败")

        transcript = ted_data.transcript
        if not transcript or len(transcript.strip()) < 50:
            raise HTTPException(status_code=400, detail="Transcript 内容太短，至少需要50个字符")

        task_id = str(uuid.uuid4())
        task_db.create(task_id, total=1)

        background_tasks.add_task(_run_processing_workflow, transcript, ted_data, task_id)

        return TaskCreateResponse(
            success=True,
            task_id=task_id,
            ted_info={
                "title": ted_data.title,
                "speaker": ted_data.speaker,
                "url": ted_data.url,
                "duration": ted_data.duration,
                "views": ted_data.views,
                "transcript_length": len(transcript)
            },
            message="任务已创建，请使用 /api/v1/tasks/{task_id} 查询进度"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


# 2. 查询任务状态
@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态（轮询方式）

    返回：
    - pending/parsing/semantic_chunk/shadow_writing/quality_check: 处理中
    - completed: 完成，结果在 result 字段
    - failed: 失败，错误信息在 error 字段
    """
    task = task_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = None
    if task.get("result"):
        try:
            result = eval(task["result"]) if isinstance(task["result"], str) else task["result"]
        except:
            pass

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        current_step=task.get("current_step"),
        progress=task.get("progress", 0),
        total=task.get("total", 0),
        current=task.get("current", 0),
        current_url=task.get("current_url"),
        result=result,
        error=task.get("error"),
        created_at=task.get("created_at"),
        updated_at=task.get("updated_at"),
        total_chunks=task.get("total_chunks", 0),
        completed_chunks=task.get("completed_chunks", 0)
    )


# 3. 删除任务
@router.delete("/tasks/{task_id}", response_model=TaskDeleteResponse)
async def delete_task(task_id: str):
    """删除任务记录"""
    exists = task_db.get(task_id)
    if not exists:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_db.delete(task_id)
    return TaskDeleteResponse(success=True, message="任务已删除")


# 4. 批量创建任务
@router.post("/tasks/batch", response_model=BatchProcessResponse)
async def create_batch_task(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """
    批量创建处理任务（URL列表）

    - 立即返回 task_id
    - 使用 GET /api/v1/tasks/{task_id} 轮询进度
    - 每个 URL 生成独立的 task_id
    """
    if not request.urls or len(request.urls) == 0:
        raise HTTPException(status_code=400, detail="URL列表不能为空")

    if len(request.urls) > 10:
        raise HTTPException(status_code=400, detail="最多支持10个URL")

    # 为每个 URL 生成独立的 task_id
    task_ids = []
    for url in request.urls:
        task_id = str(uuid.uuid4())
        task_ids.append(task_id)
        task_db.create(task_id, total=1)
        # 每个 URL 单独创建后台任务
        background_tasks.add_task(process_urls_batch, task_id, [url])

    # 返回第一个 task_id（兼容旧版）和所有 task_ids
    return BatchProcessResponse(
        success=True,
        task_id=task_ids[0],
        task_ids=task_ids,
        total=len(request.urls),
        message="任务已创建，每个URL独立处理"
    )


# ============ 原有接口（保留兼容） ============

@router.post("/process-file-stream", response_model=dict)
async def process_file_stream(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """流式处理TED文件（推荐使用 /api/v1/tasks）"""
    if not file.filename or not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="只支持 .txt 文件格式")

    try:
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        ted_data = parse_ted_file(temp_file_path)
        os.unlink(temp_file_path)

        if not ted_data:
            raise HTTPException(status_code=400, detail="文件解析失败")

        transcript = ted_data.transcript
        if not transcript or len(transcript.strip()) < 50:
            raise HTTPException(status_code=400, detail="Transcript 内容太短，至少需要50个字符")

        task_id = str(uuid.uuid4())
        task_db.create(task_id, total=1)
        background_tasks.add_task(_run_processing_workflow, transcript, ted_data, task_id)

        return {
            "success": True,
            "task_id": task_id,
            "ted_info": {
                "title": ted_data.title,
                "speaker": ted_data.speaker,
                "url": ted_data.url,
                "duration": ted_data.duration,
                "views": ted_data.views,
                "transcript_length": len(transcript)
            },
            "message": "Processing started. Connect to /api/v1/progress/{task_id} for real-time updates."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动流式处理时发生错误: {str(e)}")


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


@router.post("/process-file", response_model=dict)
async def process_file(file: UploadFile = File(...)):
    """上传TED txt文件并处理（同步方式，不推荐）"""
    if not file.filename or not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="只支持 .txt 文件格式")

    start_time = time.time()

    try:
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        ted_data = parse_ted_file(temp_file_path)
        os.unlink(temp_file_path)

        if not ted_data:
            raise HTTPException(status_code=400, detail="文件解析失败")

        transcript = ted_data.transcript
        if not transcript or len(transcript.strip()) < 50:
            raise HTTPException(status_code=400, detail="Transcript 内容太短，至少需要50个字符")

        result = process_ted_text(
            text=transcript,
            target_topic="",
            ted_title=ted_data.title,
            ted_speaker=ted_data.speaker,
            ted_url=ted_data.url
        )

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
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文件时发生错误: {str(e)}")


@router.get("/test-groq")
def test_groq_connection():
    """测试Groq API连接"""
    from app.config import settings
    if not settings.groq_api_key or settings.groq_api_key == "":
        raise HTTPException(status_code=500, detail="GROQ_API_KEY未配置")

    return {
        "status": "configured",
        "model": settings.model_name,
        "api_key_length": len(settings.groq_api_key)
    }


@router.post("/search-ted", response_model=SearchResponse)
async def search_ted(request: SearchRequest):
    """搜索TED演讲"""
    print(f"\n[API] 搜索TED演讲: {request.topic}")

    workflow = create_search_workflow()

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

    from app.dependencies import get_langfuse_handler
    langfuse_handler = get_langfuse_handler()

    if langfuse_handler:
        from langchain_core.runnables import RunnableConfig
        from typing import cast
        from app.state import Shadow_Writing_State
        config = cast(RunnableConfig, {"callbacks": [langfuse_handler]})
        result = await workflow.ainvoke(cast(Shadow_Writing_State, initial_state), config=config)
    else:
        from app.state import Shadow_Writing_State
        from typing import cast
        result = await workflow.ainvoke(cast(Shadow_Writing_State, initial_state))

    candidates_raw = result.get("ted_candidates", [])
    search_context = result.get("search_context", {})

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


@router.post("/process-batch", response_model=BatchProcessResponse)
async def process_batch(request: BatchProcessRequest, background_tasks: BackgroundTasks):
    """批量处理选中的TED URLs（推荐使用 /api/v1/tasks/batch）
    
    每个 URL 生成独立的 task_id
    """
    try:
        print(f"\n[API] 批量处理 {len(request.urls)} 个URLs")

        # 为每个 URL 生成独立的 task_id
        task_ids = []
        for url in request.urls:
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            task_db.create(task_id, total=1)
            background_tasks.add_task(process_urls_batch, task_id, [url])

        return BatchProcessResponse(
            success=True,
            task_id=task_ids[0],
            task_ids=task_ids,
            total=len(request.urls),
            message="任务已创建，每个URL独立处理"
        )

    except Exception as e:
        print(f"[ERROR] 创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_old(task_id: str):
    """查询任务状态（旧接口，保留兼容）"""
    task = task_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task["id"],
        status=task["status"],
        current_step=task.get("current_step"),
        progress=task.get("progress", 0),
        total=task.get("total", 0),
        current=task.get("current", 0),
        current_url=task.get("current_url"),
        result=None,
        error=task.get("error"),
        created_at=task.get("created_at"),
        updated_at=task.get("updated_at")
    )


# ============ 用户练习保存接口 ============

from pydantic import BaseModel

class PracticeItem(BaseModel):
    index: int
    inputs: List[str]

class UserPracticeRequest(BaseModel):
    practice: List[PracticeItem]

@router.put("/tasks/{task_id}/user-practice")
async def save_user_practice(task_id: str, request: UserPracticeRequest):
    """保存用户练习内容"""
    practice_data = [{"index": p.index, "inputs": p.inputs} for p in request.practice]
    success = history_db.update_user_practice(task_id, practice_data)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "message": "练习已保存"}

@router.get("/tasks/{task_id}/user-practice")
async def get_user_practice(task_id: str):
    """获取用户练习内容，返回空数组如果不存在"""
    practice = history_db.get_user_practice(task_id)
    return {"practice": practice if practice is not None else []}
