# api_key_monitor.py
# API Key使用监控器（单例模式）

from datetime import datetime, timedelta
from typing import Dict, Optional
from app.monitoring.api_key_stats import APIKeyStats, MonitoringSummary


class APIKeyMonitor:
    """
    API Key使用监控器（单例模式）
    
    功能：
    - 追踪每个Key的调用统计
    - 记录成功率、失败率、响应时间
    - 监控冷却状态
    - 失效检测（连续失败、高失败率）
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.stats: Dict[str, APIKeyStats] = {}  # key_id -> stats
        self.start_time = datetime.now()
        self._initialized = True
        print("[MONITOR] API Key监控器已启动")
    
    def register_key(self, key_id: str, key_value: str):
        """
        注册一个API Key
        
        Args:
            key_id: Key标识（如：KEY_1）
            key_value: Key的实际值
        """
        if key_id not in self.stats:
            key_suffix = key_value[-4:] if len(key_value) >= 4 else "****"
            self.stats[key_id] = APIKeyStats(
                key_id=key_id,
                key_suffix=key_suffix
            )
            print(f"[MONITOR] 注册Key: {key_id} (后缀: ...{key_suffix})")
    
    def record_call(self, 
                   key_id: str, 
                   success: bool, 
                   response_time: float,
                   rate_limited: bool = False,
                   response_headers: Optional[Dict] = None):
        """
        记录一次API调用
        
        Args:
            key_id: Key标识
            success: 是否成功
            response_time: 响应时间（秒）
            rate_limited: 是否触发速率限制
            response_headers: 响应头（用于提取配额信息）
        """
        if key_id not in self.stats:
            return
        
        stat = self.stats[key_id]
        
        # 更新调用统计
        stat.total_calls += 1
        if success:
            stat.successful_calls += 1
        else:
            stat.failed_calls += 1
        
        if rate_limited:
            stat.rate_limit_hits += 1
        
        # 更新响应时间
        stat.total_response_time += response_time
        stat.avg_response_time = stat.total_response_time / stat.total_calls
        stat.last_used_at = datetime.now()
        
        # 解析响应头配额信息
        if response_headers:
            stat.current_rpm_limit = response_headers.get('x-ratelimit-limit-requests')
            stat.current_rpm_remaining = response_headers.get('x-ratelimit-remaining-requests')
            stat.current_tpm_limit = response_headers.get('x-ratelimit-limit-tokens')
            stat.current_tpm_remaining = response_headers.get('x-ratelimit-remaining-tokens')
            stat.reset_time = response_headers.get('x-ratelimit-reset-requests')
        
        # 【失效检测】更新失败率窗口（保持最近50次）
        stat.failure_rate_window.append(success)
        if len(stat.failure_rate_window) > 50:
            stat.failure_rate_window.pop(0)
        
        # 【失效检测】连续失败检测
        if success:
            stat.consecutive_failures = 0
        else:
            stat.consecutive_failures += 1
            
            # 触发失效标记：连续失败10次
            if stat.consecutive_failures >= 10:
                print(f"[MONITOR] [WARNING] {key_id} 连续失败{stat.consecutive_failures}次，标记为疑似失效")
                stat.is_valid = False
                stat.invalidation_reason = f"Consecutive failures: {stat.consecutive_failures}"
                stat.invalidated_at = datetime.now()
        
        # 【失效检测】失败率检测（最近50次 > 80%）
        if len(stat.failure_rate_window) >= 50 and stat.recent_failure_rate > 80:
            print(f"[MONITOR] [WARNING] {key_id} 失败率{stat.recent_failure_rate:.1f}%，标记为疑似失效")
            stat.is_valid = False
            stat.invalidation_reason = f"High failure rate: {stat.recent_failure_rate:.1f}%"
            stat.invalidated_at = datetime.now()
    
    def mark_cooling(self, key_id: str, cooling_seconds: int = 60):
        """
        标记Key进入冷却状态
        
        Args:
            key_id: Key标识
            cooling_seconds: 冷却时长（秒）
        """
        if key_id in self.stats:
            self.stats[key_id].is_cooling = True
            self.stats[key_id].cooling_until = datetime.now() + timedelta(seconds=cooling_seconds)
            print(f"[MONITOR] 🧊 {key_id} 进入冷却（{cooling_seconds}秒）")
    
    def update_cooling_status(self):
        """更新所有Key的冷却状态"""
        now = datetime.now()
        for stat in self.stats.values():
            if stat.is_cooling and stat.cooling_until:
                if now >= stat.cooling_until:
                    stat.is_cooling = False
                    stat.cooling_until = None
    
    def get_key_stats(self, key_id: str) -> Optional[APIKeyStats]:
        """
        获取单个Key的统计信息
        
        Args:
            key_id: Key标识
            
        Returns:
            APIKeyStats或None
        """
        return self.stats.get(key_id)
    
    def get_all_stats(self) -> Dict[str, APIKeyStats]:
        """
        获取所有Key的统计信息
        
        Returns:
            {key_id: APIKeyStats}
        """
        self.update_cooling_status()
        return self.stats
    
    def get_summary(self) -> MonitoringSummary:
        """
        获取监控总览
        
        Returns:
            MonitoringSummary
        """
        self.update_cooling_status()
        
        total_calls = sum(s.total_calls for s in self.stats.values())
        total_successes = sum(s.successful_calls for s in self.stats.values())
        total_failures = sum(s.failed_calls for s in self.stats.values())
        total_rate_limits = sum(s.rate_limit_hits for s in self.stats.values())
        
        active_keys = sum(1 for s in self.stats.values() if s.last_used_at)
        cooling_keys = sum(1 for s in self.stats.values() if s.is_cooling)
        invalid_keys = sum(1 for s in self.stats.values() if not s.is_valid)
        
        avg_success_rate = (total_successes / total_calls * 100) if total_calls > 0 else 0.0
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return MonitoringSummary(
            total_keys=len(self.stats),
            active_keys=active_keys,
            cooling_keys=cooling_keys,
            invalid_keys=invalid_keys,
            total_calls=total_calls,
            total_successes=total_successes,
            total_failures=total_failures,
            total_rate_limits=total_rate_limits,
            avg_success_rate=avg_success_rate,
            monitoring_start_time=self.start_time,
            uptime_seconds=uptime
        )
    
    def reset_stats(self):
        """重置所有统计数据"""
        self.stats.clear()
        self.start_time = datetime.now()
        print("[MONITOR] [RETRY] 统计数据已重置")
    
    def get_healthy_keys(self) -> Dict[str, APIKeyStats]:
        """
        获取所有健康的Key（未失效且未冷却）
        
        Returns:
            {key_id: APIKeyStats}
        """
        self.update_cooling_status()
        return {
            key_id: stat
            for key_id, stat in self.stats.items()
            if stat.is_valid and not stat.is_cooling
        }
    
    def get_invalid_keys(self) -> Dict[str, APIKeyStats]:
        """
        获取所有失效的Key
        
        Returns:
            {key_id: APIKeyStats}
        """
        return {
            key_id: stat
            for key_id, stat in self.stats.items()
            if not stat.is_valid or stat.is_suspended
        }


# 全局单例
api_key_monitor = APIKeyMonitor()
