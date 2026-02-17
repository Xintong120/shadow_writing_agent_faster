# settings.py
# 设置相关的API路由
# 功能：
#   - 获取当前设置
#   - 更新设置
#   - 测试API连接
#   - API Keys 加密存储（支持多 Key + 轮换）

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import httpx
import asyncio
import json
import os
from ..config import settings, get_settings_dict, update_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# ============ Pydantic Models ============

class APIConfigUpdate(BaseModel):
    """API 配置更新请求（新格式）"""
    provider: Optional[str] = None
    api_keys: Optional[List[str]] = None
    model: Optional[str] = None
    rotation_enabled: Optional[bool] = None


class APIConfigResponse(BaseModel):
    """API 配置响应"""
    provider: str
    model: str
    api_keys_count: int
    rotation_enabled: bool


class SettingsUpdateRequest(BaseModel):
    """设置更新请求模型（兼容旧格式 + 新格式）"""
    # API配置（旧格式）
    backend_api_url: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_api_keys: Optional[List[str]] = None
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    api_rotation_enabled: Optional[bool] = None
    current_api_provider: Optional[str] = None

    # API配置（新格式 - SQLite 存储）
    new_api_config: Optional[APIConfigUpdate] = None

    # 外观设置
    theme_mode: Optional[str] = None
    font_size: Optional[str] = None

    # 学习偏好
    auto_save_progress: Optional[bool] = None
    show_learning_stats: Optional[bool] = None
    enable_keyboard_shortcuts: Optional[bool] = None

    # LLM配置
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None


class ApiKeyTestRequest(BaseModel):
    """API密钥测试请求模型"""
    provider: str
    api_key: str


class ApiKeyTestResponse(BaseModel):
    """API密钥测试响应模型"""
    success: bool
    message: str
    provider: str
    response_time: Optional[float] = None


# ============ Database Helper ============

def _get_db_path() -> str:
    """获取 SQLite 数据库路径"""
    return os.path.join(
        os.path.dirname(__file__), "../../../data/llm_config.db"
    )


def _get_encryption():
    """获取加密服务"""
    from ..infrastructure.config.encryption import EncryptionService
    return EncryptionService()


# ============ API Routes ============

@router.get("/")
async def get_settings():
    """获取当前设置（兼容旧格式）"""
    try:
        data = get_settings_dict()

        # 尝试从 SQLite 读取新格式配置
        db_path = _get_db_path()
        if os.path.exists(db_path):
            try:
                from ..infrastructure.config.llm_config_db import LLMConfigDB
                db = LLMConfigDB(db_path)
                keys = db.get_api_keys(settings.current_api_provider or "groq")
                if keys:
                    data["api_keys"] = keys
                    data["api_keys_count"] = len(keys)
                    data["api_rotation_enabled"] = db.is_rotation_enabled(settings.current_api_provider or "groq")
            except Exception:
                pass

        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设置失败: {str(e)}")


@router.put("/")
async def update_settings_endpoint(request: SettingsUpdateRequest):
    """更新设置"""
    try:
        # 过滤出非None的值
        settings_dict = {}
        for key, value in request.dict(exclude_unset=True).items():
            if value is not None and key != "new_api_config":
                settings_dict[key] = value

        # 处理新格式 API 配置
        if request.new_api_config:
            from ..infrastructure.config.llm_config_db import LLMConfigDB

            db_path = _get_db_path()
            db = LLMConfigDB(db_path)

            provider = str(request.new_api_config.provider or settings.current_api_provider or "groq")
            api_keys = request.new_api_config.api_keys or []
            rotation_enabled = request.new_api_config.rotation_enabled if request.new_api_config.rotation_enabled is not None else settings.api_rotation_enabled

            if api_keys:
                db.save_api_keys(provider, api_keys, rotation_enabled or False)
                settings_dict["current_api_provider"] = provider
                settings_dict["api_rotation_enabled"] = rotation_enabled

        update_settings(settings_dict)

        return {
            "success": True,
            "message": "设置更新成功",
            "data": get_settings_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新设置失败: {str(e)}")


@router.post("/api-config", response_model=dict)
async def save_api_config(config: APIConfigUpdate):
    """
    保存 API 配置（新格式 - 加密存储到 SQLite）

    Body:
        {
            "provider": "groq",
            "api_keys": ["key1", "key2"],
            "model": "llama-3.3-70b-versatile",
            "rotation_enabled": true
        }
    """
    try:
        from ..infrastructure.config.llm_config_db import LLMConfigDB

        if not config.api_keys:
            raise ValueError("At least one API key is required")

        if not config.provider:
            raise ValueError("Provider is required")

        db = LLMConfigDB(_get_db_path())
        db.save_api_keys(config.provider, config.api_keys, config.rotation_enabled or False)

        # 更新兼容字段
        update_settings({
            "current_api_provider": config.provider,
            "api_rotation_enabled": config.rotation_enabled or False
        })

        return {
            "success": True,
            "message": "API 配置已保存",
            "data": {
                "provider": config.provider,
                "api_keys_count": len(config.api_keys),
                "rotation_enabled": config.rotation_enabled or False
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存 API 配置失败: {str(e)}")


@router.get("/api-config/{provider}", response_model=dict)
async def get_api_config(provider: str):
    """
    获取指定 Provider 的 API 配置

    Returns:
        {
            "provider": "groq",
            "api_keys_count": 3,
            "rotation_enabled": true
        }
    """
    try:
        from ..infrastructure.config.llm_config_db import LLMConfigDB

        db = LLMConfigDB(_get_db_path())
        keys = db.get_api_keys(provider)
        rotation_enabled = db.is_rotation_enabled(provider)

        return {
            "success": True,
            "data": {
                "provider": provider,
                "api_keys_count": len(keys) if keys else 0,
                "rotation_enabled": rotation_enabled
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 API 配置失败: {str(e)}")


@router.post("/test-api-key")
async def test_api_key(request: ApiKeyTestRequest):
    """测试API密钥连接"""
    try:
        import time
        start_time = time.time()

        if request.provider == "openai":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="OpenAI API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"OpenAI API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()

        elif request.provider == "deepseek":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="DeepSeek API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"DeepSeek API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()

        elif request.provider == "groq":
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="Groq API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"Groq API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()

        elif request.provider == "mistral":
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.mistral.ai/v1/models",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="Mistral API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"Mistral API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()

        elif request.provider == "tavily":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "query": "test",
                        "api_key": request.api_key
                    },
                    timeout=10.0
                )
                response_time = time.time() - start_time

                if response.status_code == 200:
                    return ApiKeyTestResponse(
                        success=True,
                        message="Tavily API连接成功",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
                else:
                    return ApiKeyTestResponse(
                        success=False,
                        message=f"Tavily API连接失败: {response.status_code}",
                        provider=request.provider,
                        response_time=response_time
                    ).dict()
        else:
            raise HTTPException(status_code=400, detail=f"不支持的API提供商: {request.provider}")

    except asyncio.TimeoutError:
        return ApiKeyTestResponse(
            success=False,
            message="API连接超时",
            provider=request.provider
        ).dict()
    except Exception as e:
        return ApiKeyTestResponse(
            success=False,
            message=f"API连接测试失败: {str(e)}",
            provider=request.provider
        ).dict()


@router.post("/rotate-api-key")
async def rotate_api_key(provider: str = "groq"):
    """轮换到指定 Provider 的下一个可用 API Key"""
    try:
        from ..infrastructure.config.api_key_manager import ProviderKeyManager
        ProviderKeyManager.rotate_key(provider)

        return {
            "success": True,
            "message": f"{provider} API密钥轮换成功",
            "current_provider": provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API密钥轮换失败: {str(e)}")


@router.get("/api-providers")
async def get_api_providers():
    """获取可用的API提供商列表（仅已配置 Key 的）"""
    try:
        from ..infrastructure.config.api_key_manager import ProviderKeyManager

        available = ProviderKeyManager.available_providers()

        return {
            "success": True,
            "data": {
                "available_providers": available,
                "current_provider": settings.current_api_provider,
                "rotation_enabled": settings.api_rotation_enabled
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取API提供商列表失败: {str(e)}")


def _beautify_provider_label(value: str) -> str:
    """美化 Provider 标签"""
    KNOWN_LABELS = {
        "openai": "OpenAI",
        "groq": "GROQ",
        "anthropic": "Anthropic",
        "deepseek": "DeepSeek",
        "mistral": "Mistral",
        "azure": "Azure",
        "bedrock": "Amazon Bedrock",
        "vertex_ai": "Google Vertex AI",
        "google_vertex_ai": "Google Vertex AI",
        "huggingface": "Hugging Face",
        "together_ai": "Together AI",
        "openrouter": "OpenRouter",
        "cohere": "Cohere",
        "replicate": "Replicate",
        "ollama": "Ollama",
        "xai": "xAI",
    }
    return KNOWN_LABELS.get(value, value.replace("_", " ").title())


@router.get("/providers")
async def get_supported_providers():
    """
    获取所有支持的 Provider 列表（从 litellm 动态获取）

    Returns:
        {
            "success": true,
            "providers": [
                {"value": "openai", "label": "OpenAI"},
                {"value": "groq", "label": "GROQ"},
                ...
            ]
        }
    """
    try:
        import litellm
        from enum import Enum

        provider_list = []
        seen = set()

        for provider in litellm.provider_list:
            if isinstance(provider, Enum):
                value = provider.value
            else:
                value = str(provider)

            if value in seen:
                continue
            seen.add(value)

            label = _beautify_provider_label(value)
            provider_list.append({"value": value, "label": label})

        return {
            "success": True,
            "providers": provider_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Provider 列表失败: {str(e)}")


@router.get("/tavily-config")
async def get_tavily_config():
    """获取 Tavily 配置"""
    try:
        tavily_key = settings.tavily_api_key or ""

        return {
            "success": True,
            "data": {
                "api_key": tavily_key,
                "enabled": bool(tavily_key)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Tavily 配置失败: {str(e)}")


@router.put("/tavily-config")
async def update_tavily_config(request: dict):
    """更新 Tavily 配置"""
    try:
        api_key = request.get("api_key", "")
        enabled = request.get("enabled", bool(api_key))

        update_settings({
            "tavily_api_key": api_key,
            "tavily_enabled": enabled
        })

        return {
            "success": True,
            "message": "Tavily 配置已更新",
            "data": {
                "api_key": api_key,
                "enabled": enabled
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新 Tavily 配置失败: {str(e)}")
