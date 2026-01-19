# api_key_dashboard.py
# API Key监控仪表板API

from fastapi import APIRouter, HTTPException
from typing import Dict, List
from app.monitoring.api_key_monitor import api_key_monitor
from app.monitoring.api_key_stats import APIKeyStats, MonitoringSummary

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/summary", response_model=MonitoringSummary)
async def get_monitoring_summary():
    """
    获取监控总览
    
    Returns:
        MonitoringSummary: 包含总Key数、总调用数、成功率等
    """
    return api_key_monitor.get_summary()


@router.get("/keys", response_model=Dict[str, APIKeyStats])
async def get_all_key_stats():
    """
    获取所有Key的详细统计
    
    Returns:
        Dict[str, APIKeyStats]: {key_id: 统计数据}
    """
    return api_key_monitor.get_all_stats()


# 【重要】具体路径必须放在动态路径之前，否则会被 /keys/{key_id} 匹配
@router.get("/keys/top/success", response_model=List[APIKeyStats])
async def get_top_keys_by_success(limit: int = 5):
    """
    获取成功率最高的Keys
    
    Args:
        limit: 返回数量（默认5）
        
    Returns:
        List[APIKeyStats]: 按成功率排序的Key列表
    """
    stats = list(api_key_monitor.get_all_stats().values())
    sorted_stats = sorted(stats, key=lambda s: s.success_rate, reverse=True)
    return sorted_stats[:limit]


@router.get("/keys/top/usage", response_model=List[APIKeyStats])
async def get_top_keys_by_usage(limit: int = 5):
    """
    获取使用次数最多的Keys
    
    Args:
        limit: 返回数量（默认5）
        
    Returns:
        List[APIKeyStats]: 按调用次数排序的Key列表
    """
    stats = list(api_key_monitor.get_all_stats().values())
    sorted_stats = sorted(stats, key=lambda s: s.total_calls, reverse=True)
    return sorted_stats[:limit]


@router.get("/keys/healthy", response_model=Dict[str, APIKeyStats])
async def get_healthy_keys():
    """
    获取所有健康的Keys（未失效且未冷却）
    
    Returns:
        Dict[str, APIKeyStats]: {key_id: 统计数据}
    """
    return api_key_monitor.get_healthy_keys()


@router.get("/keys/invalid", response_model=Dict[str, APIKeyStats])
async def get_invalid_keys():
    """
    获取所有失效的Keys
    
    Returns:
        Dict[str, APIKeyStats]: {key_id: 统计数据}
    """
    return api_key_monitor.get_invalid_keys()


# 【重要】动态路径必须放在最后，避免匹配具体路径
@router.get("/keys/{key_id}", response_model=APIKeyStats)
async def get_key_stats(key_id: str):
    """
    获取单个Key的统计信息
    
    Args:
        key_id: Key标识（如：KEY_1）
        
    Returns:
        APIKeyStats: Key的统计数据
    """
    stat = api_key_monitor.get_key_stats(key_id)
    if not stat:
        raise HTTPException(status_code=404, detail=f"Key {key_id} not found")
    return stat


@router.post("/reset")
async def reset_monitoring():
    """
    重置监控统计
    
    Returns:
        {"message": str}
    """
    api_key_monitor.reset_stats()
    return {"message": "Monitoring stats reset successfully"}


@router.get("/health")
async def health_check():
    """
    健康检查接口
    
    Returns:
        {"status": str, "summary": dict}
    """
    summary = api_key_monitor.get_summary()
    return {
        "status": "healthy",
        "total_keys": summary.total_keys,
        "active_keys": summary.active_keys,
        "invalid_keys": summary.invalid_keys,
        "uptime_seconds": summary.uptime_seconds
    }
