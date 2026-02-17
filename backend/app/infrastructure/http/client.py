# infrastructure/http/client.py
"""
HTTP 客户端管理器

职责：
- 管理共享的 HTTP 客户端实例
- 实现连接池复用
- 优雅关闭
"""

import asyncio
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """
    同步 HTTP 客户端管理器

    Attributes:
        _client: HTTP 客户端实例
        _lock: 异步锁
    """

    def __init__(self):
        self._client: Optional[httpx.Client] = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> httpx.Client:
        """
        获取或创建共享的 HTTP 客户端

        Returns:
            httpx.Client: 配置好的 HTTP 客户端实例
        """
        async with self._lock:
            if self._client is None:
                self._client = httpx.Client(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(
                        max_keepalive_connections=10,
                        max_connections=20,
                        keepalive_expiry=30.0
                    ),
                    verify=True,
                    follow_redirects=True,
                    transport=httpx.HTTPTransport(retries=0)
                )
                logger.info("HTTP client pool initialized")
            return self._client

    async def close(self) -> None:
        """关闭客户端连接"""
        async with self._lock:
            if self._client:
                self._client.close()
                self._client = None
                logger.info("HTTP client pool closed")


class AsyncHTTPClientManager:
    """异步 HTTP 客户端管理器"""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> httpx.AsyncClient:
        """获取异步 HTTP 客户端"""
        async with self._lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                    limits=httpx.Limits(
                        max_keepalive_connections=10,
                        max_connections=20,
                        keepalive_expiry=30.0
                    ),
                    verify=True,
                    follow_redirects=True
                )
                logger.info("Async HTTP client initialized")
            return self._client

    async def close(self) -> None:
        """关闭客户端"""
        async with self._lock:
            if self._client:
                await self._client.aclose()
                self._client = None
                logger.info("Async HTTP client closed")


# 全局实例
_sync_http_manager = HTTPClientManager()
_async_http_manager = AsyncHTTPClientManager()


async def get_sync_http_client() -> httpx.Client:
    """获取同步 HTTP 客户端"""
    return await _sync_http_manager.get_client()


async def get_async_http_client() -> httpx.AsyncClient:
    """获取异步 HTTP 客户端"""
    return await _async_http_manager.get_client()


async def close_http_clients() -> None:
    """关闭所有 HTTP 客户端"""
    await _sync_http_manager.close()
    await _async_http_manager.close()
