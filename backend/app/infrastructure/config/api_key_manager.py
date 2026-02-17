import time
from collections import deque
from typing import Deque, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIKeyStatus:
    """API Key 状态"""
    key_id: str
    key: str
    failure_count: int = 0
    cooldown_until: float = 0.0
    total_calls: int = 0


class APIKeyManager:
    """
    API Key 轮换管理器

    Attributes:
        keys: API Key 队列
        cooldown_seconds: 冷却时间（秒）
        key_status: Key 状态字典
    """

    def __init__(
        self,
        keys: list[str],
        cooldown_seconds: int = 60,
        key_prefix: str = "KEY"
    ):
        if not keys:
            raise ValueError("At least one API Key is required")

        self._keys: Deque[str] = deque(keys)
        self._cooldown_seconds = cooldown_seconds
        self._key_prefix = key_prefix
        self._total_switches = 0

        self._status: Dict[str, APIKeyStatus] = {}
        for i, key in enumerate(keys):
            key_id = f"{key_prefix}_{i + 1}"
            self._status[key_id] = APIKeyStatus(
                key_id=key_id,
                key=key
            )

        self._register_to_monitor()
        logger.info(f"API Key Manager initialized: {len(keys)} Keys, cooldown {cooldown_seconds}s")

    def _register_to_monitor(self):
        """注册到监控器"""
        try:
            from app.monitoring import api_key_monitor
            for status in self._status.values():
                api_key_monitor.register_key(status.key_id, status.key)
        except ImportError:
            logger.warning("API Key monitor not available, skipping registration")

    def get_key(self) -> str:
        """获取当前可用的 Key"""
        current_time = time.time()

        for _ in range(len(self._keys)):
            key = self._keys[0]
            status = self._get_status_by_key(key)

            if status and current_time >= status.cooldown_until:
                status.total_calls += 1
                return key

            if status:
                remaining_time = int(status.cooldown_until - current_time)
                logger.debug(f"Key ***{key[-8:]} cooling, remaining {remaining_time}s")

            self._keys.rotate(-1)

        status = self._get_status_by_key(self._keys[0])
        if status and status.cooldown_until > current_time:
            wait_time = status.cooldown_until - current_time
            logger.info(f"All Keys cooling, waiting {int(wait_time)}s...")
            time.sleep(wait_time)

        return self._keys[0]

    def rotate_key(self) -> None:
        """切换到下一个 Key"""
        self._keys.rotate(-1)
        self._total_switches += 1
        new_key = self._keys[0]
        logger.info(f"Rotated to next API Key: ***{new_key[-8:]}")

    def mark_failure(self, key: str, error_message: str) -> None:
        """标记 Key 失败并处理"""
        status = self._get_status_by_key(key)
        if status:
            status.failure_count += 1

        error_lower = error_message.lower()
        is_rate_limit = any(k in error_lower for k in ['rate', 'limit', 'quota', 'exceeded', 'too many'])
        is_connection_error = any(k in error_lower for k in ['server disconnected', 'internal server error', 'connection', 'timeout', 'network', 'service unavailable'])

        if is_rate_limit or is_connection_error:
            if is_connection_error and not is_rate_limit:
                base_backoff = min(5, 2 ** ((status.failure_count or 1) - 1)) if status else 5
                max_backoff = 30
                error_type = "connection error"
            else:
                base_backoff = 2 ** ((status.failure_count or 1) - 1) if status else 1
                max_backoff = 60
                error_type = "rate limit"

            cooldown_seconds = min(base_backoff, max_backoff)
            import random
            jitter = cooldown_seconds * 0.25 * (random.random() * 2 - 1)
            cooldown_seconds = max(1, cooldown_seconds + jitter)

            if status:
                status.cooldown_until = time.time() + cooldown_seconds
                self._notify_cooling(status.key_id, int(cooldown_seconds))
                failure_count = status.failure_count
            else:
                failure_count = 0

            logger.info(f"[Exponential Backoff] Key ***{key[-8:]} hit {error_type}, waiting {cooldown_seconds:.1f}s")
            logger.info(f"Failure count: {failure_count}, base wait: {base_backoff}s")

            self.rotate_key()
        else:
            logger.error(f"Key ***{key[-8:]} call failed (non-rate-limit): {error_message[:100]}")

    def _get_status_by_key(self, key: str) -> Optional[APIKeyStatus]:
        """根据 Key 值获取状态"""
        for status in self._status.values():
            if status.key == key:
                return status
        return None

    def _notify_cooling(self, key_id: str, cooldown_seconds: int):
        """通知监控器进入冷却"""
        try:
            from app.monitoring import api_key_monitor
            api_key_monitor.mark_cooling(key_id, cooldown_seconds)
        except ImportError:
            pass

    @property
    def total_switches(self) -> int:
        """总切换次数"""
        return self._total_switches

    @property
    def available_key_count(self) -> int:
        """可用 Key 数量"""
        current_time = time.time()
        return sum(
            1 for s in self._status.values()
            if current_time >= s.cooldown_until
        )

    @property
    def all_keys(self) -> list:
        """所有 Key 的状态"""
        return list(self._status.values())


class ProviderKeyManager:
    """按 Provider 独立的 API Key 管理器"""

    _managers: dict = {}
    _SUPPORTED_PROVIDERS: list = ["groq", "mistral", "openai", "deepseek"]

    @classmethod
    def get_supported_providers(cls) -> list:
        """动态获取支持的 Provider 列表"""
        try:
            from app.infrastructure.config.llm_model_map import get_llm_model_map
            model_map = get_llm_model_map()
            providers = set()
            for config in model_map.values():
                if isinstance(config, dict) and "provider" in config:
                    providers.add(config["provider"])
            return list(providers) if providers else cls._SUPPORTED_PROVIDERS
        except Exception:
            return cls._SUPPORTED_PROVIDERS

    @classmethod
    def get_manager(cls, provider: str) -> APIKeyManager:
        """获取指定 Provider 的 Key Manager"""
        if provider not in cls._managers:
            cls._managers[provider] = cls._create_manager(provider)
        return cls._managers[provider]

    @classmethod
    def _create_manager(cls, provider: str) -> APIKeyManager:
        """创建指定 Provider 的 Key Manager"""
        from app.infrastructure.config import get_settings
        settings = get_settings()

        keys = []
        if provider == "groq":
            keys = settings.groq_api_keys or ([settings.groq_api_key] if settings.groq_api_key else [])
        elif provider == "mistral":
            keys = settings.mistral_api_keys or ([settings.mistral_api_key] if settings.mistral_api_key else [])
        elif provider == "openai":
            keys = [settings.openai_api_key] if settings.openai_api_key else []
        elif provider == "deepseek":
            keys = [settings.deepseek_api_key] if settings.deepseek_api_key else []
        else:
            keys = []

        if not keys:
            raise ValueError(f"No API keys found for provider: {provider}")

        return APIKeyManager(keys=keys, cooldown_seconds=60, key_prefix=provider.upper())

    @classmethod
    def get_key(cls, provider: str) -> str:
        """获取指定 Provider 的当前可用 Key"""
        manager = cls.get_manager(provider)
        return manager.get_key()

    @classmethod
    def rotate_key(cls, provider: str) -> None:
        """切换指定 Provider 到下一个 Key"""
        manager = cls.get_manager(provider)
        manager.rotate_key()

    @classmethod
    def mark_failure(cls, provider: str, key: str, error_message: str) -> None:
        """标记指定 Provider 的 Key 失败"""
        manager = cls.get_manager(provider)
        manager.mark_failure(key, error_message)

    @classmethod
    def clear_cache(cls, provider: str = None) -> None:
        """清除缓存"""
        if provider:
            cls._managers.pop(provider, None)
        else:
            cls._managers.clear()

    @classmethod
    def available_providers(cls) -> list:
        """获取有可用 Key 的 Provider 列表"""
        available = []
        supported = cls.get_supported_providers()
        for provider in supported:
            try:
                manager = cls.get_manager(provider)
                if manager.available_key_count > 0:
                    available.append(provider)
            except (ValueError, AttributeError):
                continue
        return available


_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """获取全局 API Key 管理器实例"""
    global _api_key_manager
    if _api_key_manager is None:
        from app.infrastructure.config import get_settings
        settings = get_settings()
        keys = []

        if settings.groq_api_key:
            keys.extend(settings.groq_api_keys or [settings.groq_api_key])
        if settings.mistral_api_key:
            keys.extend(settings.mistral_api_keys or [settings.mistral_api_key])
        if settings.openai_api_key:
            keys.append(settings.openai_api_key)
        if settings.deepseek_api_key:
            keys.append(settings.deepseek_api_key)

        if keys:
            _api_key_manager = APIKeyManager(keys=keys, cooldown_seconds=60)
        else:
            raise ValueError("No API keys available")

    return _api_key_manager


def create_api_key_manager(keys: list[str]) -> APIKeyManager:
    """创建新的 API Key 管理器实例"""
    return APIKeyManager(keys=keys)
