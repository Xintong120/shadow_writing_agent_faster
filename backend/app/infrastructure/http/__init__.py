# infrastructure/http/__init__.py
"""
HTTP 客户端模块

提供：
- HTTPClientManager: 同步 HTTP 客户端管理器
- AsyncHTTPClientManager: 异步 HTTP 客户端管理器
- get_sync_http_client(): 获取同步客户端
- get_async_http_client(): 获取异步客户端
- close_http_clients(): 关闭所有客户端

Usage:
    from app.infrastructure.http import get_sync_http_client, close_http_clients

    client = await get_sync_http_client()
    response = client.get("https://api.example.com")
"""

from .client import (
    HTTPClientManager,
    AsyncHTTPClientManager,
    get_sync_http_client,
    get_async_http_client,
    close_http_clients
)

__all__ = [
    "HTTPClientManager",
    "AsyncHTTPClientManager",
    "get_sync_http_client",
    "get_async_http_client",
    "close_http_clients",
]
