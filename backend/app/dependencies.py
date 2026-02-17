# dependencies.py
"""
依赖注入容器

职责：
- 管理全局单例实例
- 提供依赖获取接口
- 处理生命周期
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DependencyContainer:
    """依赖注入容器"""

    def __init__(self):
        self._instances = {}
        self._initialized = False

    def initialize(self) -> None:
        """初始化所有全局依赖"""
        if self._initialized:
            return

        # 初始化配置
        from app.infrastructure.config import get_settings, validate_config
        settings = get_settings()
        validate_config()

        # 初始化 API Key 管理器
        from app.infrastructure.config.api_key_manager import APIKeyManager
        self._instances["api_key_manager"] = APIKeyManager.from_settings(settings)

        # 初始化 HTTP 客户端
        from app.infrastructure.http import close_http_clients
        self._instances["close_http_clients"] = close_http_clients

        # 初始化 LLM 服务
        from app.services.llm import LLMService
        self._instances["llm_service"] = LLMService(
            key_manager=self._instances["api_key_manager"]
        )

        # 初始化 Langfuse
        from app.infrastructure.monitoring import get_langfuse_monitor
        self._instances["langfuse_monitor"] = get_langfuse_monitor()

        self._initialized = True
        logger.info("[DEPENDENCY] Container initialized")

    def shutdown(self) -> None:
        """关闭所有资源"""
        close_http = self._instances.get("close_http_clients")
        if close_http:
            import asyncio
            asyncio.run(close_http())

        monitor = self._instances.get("langfuse_monitor")
        if monitor:
            monitor.shutdown()

        self._instances.clear()
        self._initialized = False
        logger.info("[DEPENDENCY] Container shutdown")

    @property
    def settings(self):
        """获取配置"""
        from app.infrastructure.config import get_settings
        return get_settings()

    @property
    def api_key_manager(self):
        """获取 API Key 管理器"""
        return self._instances.get("api_key_manager")

    @property
    def llm_service(self):
        """获取 LLM 服务"""
        return self._instances.get("llm_service")

    @property
    def langfuse_handler(self):
        """获取 Langfuse 处理器"""
        monitor = self._instances.get("langfuse_monitor")
        if monitor:
            return monitor.handler
        return None


_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """获取全局容器实例"""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def init_dependencies() -> None:
    """初始化依赖（应用启动时调用）"""
    container = get_container()
    container.initialize()


def shutdown_dependencies() -> None:
    """关闭依赖（应用关闭时调用）"""
    global _container
    if _container:
        _container.shutdown()
        _container = None


def get_langfuse_handler():
    """获取 Langfuse 处理器（兼容旧 API）"""
    container = get_container()
    return container.langfuse_handler


def get_llm_service():
    """获取 LLM 服务"""
    container = get_container()
    return container.llm_service


def get_api_key_manager():
    """获取 API Key 管理器"""
    container = get_container()
    return container.api_key_manager
