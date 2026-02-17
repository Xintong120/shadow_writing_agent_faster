# routers/history.py
# 历史记录路由 - 学习历史管理

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.models import HistoryListResponse, HistoryDetailResponse
from app.db import history_db
from app.db.history_db import LearningStatus
from datetime import datetime, timezone
from typing import Optional
import asyncio


async def extract_and_save_core_arguments(task_id: str):
    """后台任务：提取并保存核心观点"""
    try:
        record = history_db.get_by_task_id(task_id)
        if not record:
            print(f"[ArgumentExtractor] Record not found for task_id: {task_id}")
            return
        
        existing_args = history_db.get_core_arguments(task_id)
        if existing_args:
            print(f"[ArgumentExtractor] Core arguments already exist for task_id: {task_id}")
            return
        
        transcript = record.get('transcript')
        if not transcript or len(transcript) < 50:
            print(f"[ArgumentExtractor] No transcript found for task_id: {task_id}")
            return
        
        from app.services.argument_extractor import get_argument_extractor
        extractor = get_argument_extractor()
        
        print(f"[ArgumentExtractor] Starting extraction for task_id: {task_id}")
        core_arguments = extractor.extract(
            transcript=transcript,
            title=record.get('ted_title', ''),
            speaker=record.get('ted_speaker', '')
        )
        
        success = history_db.update_core_arguments(task_id, core_arguments)
        if success:
            print(f"[ArgumentExtractor] Successfully saved core arguments for task_id: {task_id}")
        else:
            print(f"[ArgumentExtractor] Failed to save core arguments for task_id: {task_id}")
            
    except Exception as e:
        print(f"[ArgumentExtractor] Error extracting arguments: {e}")


class StatusUpdateRequest(BaseModel):
    """状态更新请求"""
    status: str  # todo / in_progress / completed


class StatusResponse(BaseModel):
    """状态响应"""
    task_id: str
    status: str
    success: bool


router = APIRouter(prefix="/api/v1/history", tags=["history"])


def format_learned_at(learned_at_str: str) -> str:
    """将数据库的 UTC 时间转换为 ISO 8601 格式（带时区）"""
    try:
        dt = datetime.strptime(learned_at_str, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except:
        return learned_at_str


@router.get("", response_model=HistoryListResponse)
async def list_history(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """
    获取历史学习记录列表

    - 按学习时间倒序排列
    - 支持分页
    - 支持按状态过滤 (todo/in_progress/completed)
    """
    records = history_db.list_all(limit=limit, offset=offset, status=status)
    total = history_db.count()

    clean_records = []
    for r in records:
        clean_records.append({
            "id": r["id"],
            "task_id": r["task_id"],
            "ted_title": r["ted_title"],
            "ted_speaker": r["ted_speaker"],
            "ted_url": r["ted_url"],
            "ted_duration": r.get("ted_duration"),
            "ted_views": r.get("ted_views"),
            "result": r.get("result"),
            "status": r.get("status", LearningStatus.TODO),
            "learned_at": format_learned_at(r["learned_at"])
        })

    return HistoryListResponse(
        success=True,
        records=clean_records,
        total=total
    )


@router.get("/{record_id}", response_model=HistoryDetailResponse)
async def get_history_detail(record_id: str):
    """获取历史记录详情"""
    record = history_db.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return HistoryDetailResponse(
        success=True,
        record={
            "id": record["id"],
            "task_id": record["task_id"],
            "ted_title": record["ted_title"],
            "ted_speaker": record["ted_speaker"],
            "ted_url": record["ted_url"],
            "ted_duration": record.get("ted_duration"),
            "ted_views": record.get("ted_views"),
            "result": record.get("result"),
            "transcript": record.get("transcript"),
            "status": record.get("status", LearningStatus.TODO),
            "learned_at": format_learned_at(record["learned_at"])
        }
    )


@router.put("/{task_id}/status", response_model=StatusResponse)
async def update_task_status(task_id: str, request: StatusUpdateRequest, background_tasks: BackgroundTasks):
    """更新学习状态
    
    Args:
        task_id: 任务ID
        request: 状态更新请求 (todo/in_progress/completed)
    """
    valid_statuses = [LearningStatus.TODO, LearningStatus.IN_PROGRESS, LearningStatus.COMPLETED]
    
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效的状态: {request.status}")
    
    success = history_db.update_status(task_id, request.status)
    
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if request.status == LearningStatus.COMPLETED:
        background_tasks.add_task(extract_and_save_core_arguments, task_id)
    
    return StatusResponse(
        task_id=task_id,
        status=request.status,
        success=True
    )


@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    """获取学习状态"""
    status = history_db.get_status(task_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "task_id": task_id,
        "status": status
    }


@router.delete("/{record_id}")
async def delete_history(record_id: str):
    """删除历史记录"""
    if not history_db.get(record_id):
        raise HTTPException(status_code=404, detail="记录不存在")

    history_db.delete(record_id)
    return {"success": True, "message": "记录已删除"}
