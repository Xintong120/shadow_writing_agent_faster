# routers/memory.py
# Memory系统API路由

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.memory import MemoryService, get_global_store
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/memory", tags=["memory"])

# 全局Memory服务实例
memory_service = MemoryService(store=get_global_store())


# ==================== 请求/响应模型 ====================

class AddLearningRecordRequest(BaseModel):
    """添加学习记录请求"""
    user_id: str = Field(..., description="用户ID")
    ted_url: str = Field(..., description="TED URL")
    ted_title: str = Field(..., description="TED标题")
    ted_speaker: str = Field(..., description="演讲者")
    original: str = Field(..., description="原始句子")
    imitation: str = Field(..., description="改写句子")
    word_map: Dict[str, List[str]] = Field(..., description="词汇映射")
    paragraph: str = Field(..., description="原始段落")
    quality_score: float = Field(..., description="质量评分", ge=0, le=10)
    tags: Optional[List[str]] = Field(default=None, description="标签列表")


class TEDHistoryResponse(BaseModel):
    """TED观看历史响应"""
    url: str
    title: str
    speaker: str
    watched_at: str
    search_topic: str
    chunks_processed: int
    shadow_writing_count: int
    metadata: Dict[str, Any]


class SearchHistoryResponse(BaseModel):
    """搜索历史响应"""
    search_id: str
    original_query: str
    optimized_query: str
    alternative_queries: List[str]
    results_count: int
    selected_url: Optional[str]
    selected_title: Optional[str]
    searched_at: str
    search_duration_ms: int
    new_results: int
    filtered_seen: int


# ==================== API端点 ====================

@router.get("/ted-history/{user_id}", response_model=List[TEDHistoryResponse])
async def get_ted_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="返回数量")
):
    """
    获取用户的TED观看历史
    
    Args:
        user_id: 用户ID
        limit: 返回数量限制（1-200）
        
    Returns:
        TED观看历史列表，按时间倒序
    """
    try:
        seen_urls = memory_service.get_seen_ted_urls(user_id)
        
        # 获取每个URL的详细信息
        history = []
        for url in list(seen_urls)[:limit]:
            info = memory_service.get_ted_info(user_id, url)
            if info:
                history.append(info)
        
        # 按watched_at倒序排序
        history.sort(key=lambda x: x.get("watched_at", ""), reverse=True)
        
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取TED历史失败: {str(e)}")


@router.get("/search-history/{user_id}", response_model=List[SearchHistoryResponse])
async def get_search_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="返回数量")
):
    """
    获取用户的搜索历史
    
    Args:
        user_id: 用户ID
        limit: 返回数量限制（1-200）
        
    Returns:
        搜索历史列表，按时间倒序
    """
    try:
        searches = memory_service.get_recent_searches(user_id, limit=limit)
        return searches
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取搜索历史失败: {str(e)}")


@router.get("/learning-records/{user_id}")
async def get_learning_records(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="返回数量"),
    ted_url: Optional[str] = Query(default=None, description="按TED URL过滤"),
    min_quality: Optional[float] = Query(default=None, ge=0, le=10, description="最小质量分数"),
    tags: Optional[str] = Query(default=None, description="按标签过滤，逗号分隔")
):
    """
    获取用户的学习记录
    
    Args:
        user_id: 用户ID
        limit: 返回数量限制（1-200）
        ted_url: 按TED URL过滤（可选）
        min_quality: 最小质量分数过滤（可选）
        tags: 按标签过滤，逗号分隔（可选）
        
    Returns:
        学习记录列表，按时间倒序
        
    Examples:
        - GET /memory/learning-records/user_123
        - GET /memory/learning-records/user_123?limit=20
        - GET /memory/learning-records/user_123?min_quality=7.0
        - GET /memory/learning-records/user_123?tags=leadership,innovation
        - GET /memory/learning-records/user_123?ted_url=https://ted.com/...
    """
    try:
        # 解析tags参数
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        
        records = memory_service.get_learning_records(
            user_id=user_id,
            limit=limit,
            ted_url=ted_url,
            min_quality=min_quality,
            tags=tag_list
        )
        
        return {
            "user_id": user_id,
            "total": len(records),
            "records": records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学习记录失败: {str(e)}")


@router.get("/learning-records/{user_id}/{record_id}")
async def get_learning_record_by_id(
    user_id: str,
    record_id: str
):
    """
    根据ID获取单条学习记录
    
    Args:
        user_id: 用户ID
        record_id: 记录ID
        
    Returns:
        学习记录详情
    """
    try:
        record = memory_service.get_learning_record_by_id(user_id, record_id)
        
        if not record:
            raise HTTPException(
                status_code=404, 
                detail=f"记录不存在: {record_id}"
            )
        
        return record
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记录失败: {str(e)}")


@router.get("/stats/{user_id}")
async def get_learning_stats(user_id: str):
    """
    获取用户的学习统计数据
    
    Args:
        user_id: 用户ID
        
    Returns:
        统计数据，包含：
        - total_records: 总记录数
        - avg_quality_score: 平均质量分
        - top_tags: 热门标签
        - records_by_ted: 按TED分组统计
        - recent_activity: 最近活动时间
        - quality_trend: 质量趋势
    """
    try:
        stats = memory_service.get_learning_stats(user_id)
        
        # 同时获取TED和搜索历史的统计
        seen_urls = memory_service.get_seen_ted_urls(user_id)
        recent_searches = memory_service.get_recent_searches(user_id, limit=10)
        
        return {
            "user_id": user_id,
            "learning_records": stats,
            "ted_history": {
                "total_watched": len(seen_urls),
                "watched_urls": list(seen_urls)
            },
            "search_history": {
                "total_searches": len(recent_searches),
                "recent_searches": recent_searches[:5]  # 只返回最近5次
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@router.post("/learning-records", status_code=201)
async def add_learning_record(request: AddLearningRecordRequest):
    """
    手动添加学习记录
    
    Args:
        request: 学习记录数据
        
    Returns:
        记录ID
        
    Note:
        通常由系统自动调用，用户也可以手动添加自定义记录
    """
    try:
        record_id = memory_service.add_learning_record(
            user_id=request.user_id,
            ted_url=request.ted_url,
            ted_title=request.ted_title,
            ted_speaker=request.ted_speaker,
            original=request.original,
            imitation=request.imitation,
            word_map=request.word_map,
            paragraph=request.paragraph,
            quality_score=request.quality_score,
            tags=request.tags
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "学习记录已添加"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加记录失败: {str(e)}")


@router.delete("/learning-records/{user_id}/{record_id}")
async def delete_learning_record(
    user_id: str,
    record_id: str
):
    """
    删除学习记录
    
    Args:
        user_id: 用户ID
        record_id: 记录ID
        
    Returns:
        删除结果
    """
    try:
        success = memory_service.delete_learning_record(user_id, record_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"记录不存在或删除失败: {record_id}"
            )
        
        return {
            "success": True,
            "message": f"记录已删除: {record_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记录失败: {str(e)}")


# ==================== 额外的便捷接口 ====================

@router.get("/summary/{user_id}")
async def get_user_summary(user_id: str):
    """
    获取用户Memory系统总览
    
    一次性返回所有关键统计数据
    """
    try:
        # 学习统计
        learning_stats = memory_service.get_learning_stats(user_id)
        
        # TED历史
        seen_urls = memory_service.get_seen_ted_urls(user_id)
        
        # 搜索历史
        recent_searches = memory_service.get_recent_searches(user_id, limit=5)
        
        return {
            "user_id": user_id,
            "summary": {
                "total_learning_records": learning_stats.get("total_records", 0),
                "avg_quality_score": learning_stats.get("avg_quality_score", 0),
                "total_ted_watched": len(seen_urls),
                "total_searches": len(memory_service.get_recent_searches(user_id, limit=1000)),
                "recent_activity": learning_stats.get("recent_activity")
            },
            "top_tags": learning_stats.get("top_tags", [])[:10],
            "recent_searches": [s.get("original_query") for s in recent_searches]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取总览失败: {str(e)}")
