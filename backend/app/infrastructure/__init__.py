# infrastructure/__init__.py
"""
基础设施层

提供：
- config: 配置管理
- http: HTTP 客户端
- monitoring: 监控集成
- messaging: 消息服务

Usage:
    from app.infrastructure.config import get_settings
    from app.infrastructure.http import get_sync_http_client
    from app.infrastructure.monitoring import get_langfuse_handler
"""

from .config import (
    Settings,
    get_settings,
    validate_config,
    get_settings_dict,
    update_settings,
    APIKeyManager,
    get_api_key_manager,
)
from .http import (
    HTTPClientManager,
    AsyncHTTPClientManager,
    get_sync_http_client,
    get_async_http_client,
    close_http_clients,
)
from .monitoring import (
    LangfuseMonitor,
    get_langfuse_monitor,
    get_langfuse_handler,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    "validate_config",
    "get_settings_dict",
    "update_settings",
    "APIKeyManager",
    "get_api_key_manager",
    # HTTP
    "HTTPClientManager",
    "AsyncHTTPClientManager",
    "get_sync_http_client",
    "get_async_http_client",
    "close_http_clients",
    # Monitoring
    "LangfuseMonitor",
    "get_langfuse_monitor",
    "get_langfuse_handler",
]
