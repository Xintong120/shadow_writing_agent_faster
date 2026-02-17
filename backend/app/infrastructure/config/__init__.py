# infrastructure/config/__init__.py
"""
配置模块

提供：
- Settings: 配置类
- get_settings(): 获取全局配置
- validate_config(): 验证配置
- APIKeyManager: API Key 轮换管理器

Usage:
    from app.infrastructure.config import get_settings, validate_config
    from app.infrastructure.config import get_api_key_manager

    settings = get_settings()
    key_manager = get_api_key_manager()
"""

from .settings import Settings, get_settings, validate_config, get_settings_dict, update_settings
from .api_key_manager import APIKeyManager, get_api_key_manager, create_api_key_manager

__all__ = [
    "Settings",
    "get_settings",
    "validate_config",
    "get_settings_dict",
    "update_settings",
    "APIKeyManager",
    "get_api_key_manager",
    "create_api_key_manager",
]
