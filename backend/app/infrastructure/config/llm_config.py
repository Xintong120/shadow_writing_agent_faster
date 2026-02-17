from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from enum import Enum
import os


class LLMProvider(Enum):
    GROQ = "groq"
    MISTRAL = "mistral"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"


class LLMConfig(BaseModel):
    """统一的 LLM 配置类"""
    id: Optional[int] = None
    provider: LLMProvider
    model: str
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    response_format: Optional[Dict[str, Any]] = None
    api_key_env: str = ""
    enabled: bool = True
    is_default: bool = False

    class Config:
        protected_namespaces = ()


LITELLM_MODEL_MAP = {
    "groq": lambda model: f"groq/{model}",
    "mistral": lambda model: f"mistral/{model}",
    "openai": lambda model: f"openai/{model}",
    "deepseek": lambda model: f"deepseek/{model}",
    "anthropic": lambda model: f"anthropic/{model}",
}


def get_litellm_model(provider: LLMProvider, model: str) -> str:
    mapper = LITELLM_MODEL_MAP.get(provider.value, lambda x: x)
    return mapper(model)
