# api_key_stats.py
# API Key统计数据模型

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class APIKeyStats(BaseModel):
    """单个API Key的统计数据"""
    
    key_id: str = Field(..., description="Key标识（如：KEY_1）")
    key_suffix: str = Field(..., description="Key后4位（用于显示）")
    
    # 调用统计
    total_calls: int = Field(default=0, description="总调用次数")
    successful_calls: int = Field(default=0, description="成功次数")
    failed_calls: int = Field(default=0, description="失败次数")
    rate_limit_hits: int = Field(default=0, description="429错误次数")
    
    # 时间统计
    total_response_time: float = Field(default=0.0, description="总响应时间（秒）")
    avg_response_time: float = Field(default=0.0, description="平均响应时间")
    last_used_at: Optional[datetime] = Field(default=None, description="最后使用时间")
    
    # 配额信息（从响应头获取）
    current_rpm_limit: Optional[int] = Field(default=None, description="RPM限制")
    current_rpm_remaining: Optional[int] = Field(default=None, description="剩余RPM")
    current_tpm_limit: Optional[int] = Field(default=None, description="TPM限制")
    current_tpm_remaining: Optional[int] = Field(default=None, description="剩余TPM")
    reset_time: Optional[int] = Field(default=None, description="重置时间（秒）")
    
    # 冷却状态
    is_cooling: bool = Field(default=False, description="是否在冷却中")
    cooling_until: Optional[datetime] = Field(default=None, description="冷却结束时间")
    
    # 健康状态（用于失效检测）
    is_valid: bool = Field(default=True, description="Key是否有效")
    is_suspended: bool = Field(default=False, description="是否被封禁")
    last_health_check: Optional[datetime] = Field(default=None, description="最后健康检查时间")
    health_check_failures: int = Field(default=0, description="健康检查连续失败次数")
    
    # 失效检测
    consecutive_failures: int = Field(default=0, description="连续失败次数")
    failure_rate_window: List[bool] = Field(default_factory=list, description="最近50次调用的成功/失败记录")
    invalidation_reason: Optional[str] = Field(default=None, description="失效原因")
    invalidated_at: Optional[datetime] = Field(default=None, description="失效时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        return 100 - self.success_rate
    
    @property
    def recent_failure_rate(self) -> float:
        """最近50次调用的失败率"""
        if not self.failure_rate_window:
            return 0.0
        failures = sum(1 for success in self.failure_rate_window if not success)
        return (failures / len(self.failure_rate_window)) * 100


class MonitoringSummary(BaseModel):
    """监控总览"""
    
    total_keys: int = Field(..., description="总Key数量")
    active_keys: int = Field(..., description="活跃Key数量")
    cooling_keys: int = Field(..., description="冷却中Key数量")
    invalid_keys: int = Field(default=0, description="失效Key数量")
    
    total_calls: int = Field(..., description="总调用次数")
    total_successes: int = Field(..., description="总成功次数")
    total_failures: int = Field(..., description="总失败次数")
    total_rate_limits: int = Field(..., description="总速率限制次数")
    
    avg_success_rate: float = Field(..., description="平均成功率")
    monitoring_start_time: datetime = Field(..., description="监控开始时间")
    uptime_seconds: float = Field(..., description="运行时长（秒）")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
