import json
import os
from typing import Dict, Tuple, Optional, Any
from app.infrastructure.config.llm_config import LLMProvider


def get_llm_model_map() -> Dict[str, Dict[str, Any]]:
    """获取 LLM 模型映射配置（优先从环境变量读取）"""
    env_value = os.getenv("LLM_MODEL_MAP")
    if env_value:
        try:
            return json.loads(env_value)
        except json.JSONDecodeError:
            pass
    
    # 回退：从 LLMConfigService 读取
    try:
        from app.infrastructure.config.llm_config_service import LLMConfigService
        service = LLMConfigService()
        
        # 获取当前配置
        available = service.list_available()
        if available:
            model_map = {}
            for provider, model in available:
                model_map[provider] = {
                    "provider": provider,
                    "model": model,
                    "temperature": 0.1,
                }
            return model_map
    except Exception:
        pass
    
    # 最终回退：使用开发环境默认配置
    return {
        "default": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.1,
        },
    }


def get_model_for_purpose(purpose: str) -> Tuple[LLMProvider, str]:
    """获取指定用途的模型配置"""
    model_map = get_llm_model_map()
    config = model_map.get(purpose) or model_map.get("default") or {}
    if not config:
        # 回退到 settings 中的配置
        from app.infrastructure.config import get_settings
        settings = get_settings()
        return LLMProvider.GROQ, settings.model_name or "llama-3.3-70b-versatile"
    provider = LLMProvider(config["provider"])
    model = config["model"]
    return provider, model


def get_llm_config_for_purpose(purpose: str) -> Dict[str, Any]:
    """获取指定用途的完整配置（包含 temperature 等）"""
    model_map = get_llm_model_map()
    config = model_map.get(purpose) or model_map.get("default")
    if not config:
        from app.infrastructure.config import get_settings
        settings = get_settings()
        return {
            "provider": "groq",
            "model": settings.model_name or "llama-3.3-70b-versatile",
            "temperature": settings.temperature,
        }
    return config


def create_llm_for_purpose(purpose: str, streaming: bool = False, **override_kwargs):
    """
    根据用途创建 LLM（推荐方式）

    Args:
        purpose: 用途名称，如 "debate", "shadow_writing"
        streaming: 是否支持流式
        **override_kwargs: 覆盖配置的参数（如 temperature）

    Returns:
        LangChain LLM 对象
    """
    from app.services.llm.llm_factory import LLMFactory

    config = get_llm_config_for_purpose(purpose)

    # 合并配置，override_kwargs 优先级更高
    final_config = {**config, **override_kwargs}

    provider = final_config.get("provider", "groq")
    model = final_config.get("model", "llama-3.3-70b-versatile")
    temperature = final_config.get("temperature", 0.1)

    return LLMFactory.create_langchain_llm(
        provider=provider,
        model=model,
        streaming=streaming,
        temperature=temperature,
    )
