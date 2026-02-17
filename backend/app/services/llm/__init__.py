# services/llm/__init__.py
"""
LLM 服务层

提供：
- LLMService: LLM 服务
- get_llm_service(): 获取全局实例

Usage:
    from app.services.llm import get_llm_service

    llm_service = get_llm_service()
    llm = llm_service.create_shadow_writing_llm()
    result = llm(prompt, output_format)
"""

from .factory import LLMService, get_llm_service

__all__ = [
    "LLMService",
    "get_llm_service",
]
