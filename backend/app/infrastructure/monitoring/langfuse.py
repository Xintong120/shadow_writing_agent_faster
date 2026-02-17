# infrastructure/monitoring/langfuse.py
"""
Langfuse 监控集成

职责：
- Langfuse 客户端初始化
- 回调处理器提供
- 监控状态管理
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LangfuseMonitor:
    """Langfuse 监控器"""

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        base_url: str = "https://cloud.langfuse.com"
    ):
        self.public_key = public_key
        self.secret_key = secret_key
        self.base_url = base_url
        self._client = None
        self._handler = None

        self._initialize()

    def _initialize(self) -> None:
        """初始化 Langfuse 客户端"""
        try:
            from langfuse import Langfuse
            from langfuse.langchain import CallbackHandler

            self._client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.base_url
            )

            self._handler = CallbackHandler()
            logger.info("[LANGFUSE] Langfuse monitoring enabled")

        except ImportError as e:
            logger.warning(f"[LANGFUSE] Langfuse not installed: {e}")
            self._client = None
            self._handler = None
        except Exception as e:
            logger.error(f"[LANGFUSE] Langfuse initialization failed: {e}")
            self._client = None
            self._handler = None

    @property
    def enabled(self) -> bool:
        """是否已启用"""
        return self._handler is not None

    @property
    def client(self):
        """获取 Langfuse 客户端"""
        return self._client

    @property
    def handler(self):
        """获取回调处理器"""
        return self._handler

    def shutdown(self) -> None:
        """关闭 Langfuse"""
        if self._client:
            try:
                self._client.shutdown()
                logger.info("[LANGFUSE] Langfuse shutdown")
            except Exception as e:
                logger.error(f"[LANGFUSE] Shutdown failed: {e}")


_langfuse_monitor: Optional[LangfuseMonitor] = None


def get_langfuse_monitor() -> Optional[LangfuseMonitor]:
    """获取全局 Langfuse 监控器实例"""
    global _langfuse_monitor
    if _langfuse_monitor is None:
        from app.infrastructure.config import get_settings
        settings = get_settings()

        if settings.langfuse_enabled and settings.langfuse_public_key and settings.langfuse_secret_key:
            _langfuse_monitor = LangfuseMonitor(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                base_url=settings.langfuse_base_url
            )
        else:
            logger.info("[LANGFUSE] Langfuse not enabled (missing config)")

    return _langfuse_monitor


def get_langfuse_handler():
    """获取 Langfuse 回调处理器（兼容旧 API）"""
    monitor = get_langfuse_monitor()
    if monitor:
        return monitor.handler
    return None
