# routers/config.py
# 系统配置管理路由

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import os
import httpx

from app.config import settings
from app.utils import initialize_key_manager, api_key_manager

LITELLM_MODEL_COST_MAP_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

_litellm_model_cache: Optional[Dict[str, Any]] = None
_model_cache_timestamp: float = 0
_MODEL_CACHE_DURATION = 3600

_litellm_providers: Optional[List[str]] = None

def _get_litellm_providers(model_map: Dict[str, Any]) -> List[str]:
    """从模型映射中动态提取所有 provider 名称"""
    global _litellm_providers
    if _litellm_providers is not None:
        return _litellm_providers

    providers = set()
    for model_info in model_map.values():
        if isinstance(model_info, dict):
            provider = model_info.get('litellm_provider')
            if provider:
                providers.add(provider)
    _litellm_providers = sorted(list(providers))
    return _litellm_providers

def _build_provider_aliases() -> Dict[str, str]:
    """动态构建 provider 别名映射表"""
    return {
        # 标准名称
        'openai': 'openai',
        'anthropic': 'anthropic',
        'groq': 'groq',
        'deepseek': 'deepseek',
        'mistral': 'mistral',
        'cohere': 'cohere',
        'togetherai': 'together_ai',
        'together_ai': 'together_ai',
        'openrouter': 'openrouter',
        'ollama': 'ollama',
        'azure': 'azure',
        'vertex_ai': 'vertex_ai',
        'gemini': 'gemini',
        'bedrock': 'bedrock',
        'huggingface': 'huggingface',
        'replicate': 'replicate',
        'perplexity': 'perplexity',
        'xai': 'xai',
        'cloudflare': 'cloudflare',
        'fireworks_ai': 'fireworks_ai',
        'novita': 'novita',
        'sambanova': 'sambanova',
        'deepinfra': 'deepinfra',
        'ai21': 'ai21',
        'nvidia_nim': 'nvidia_nim',
        'cerebras': 'cerebras',
        'vllm': 'vllm',
        'databricks': 'databricks',
        'watsonx': 'watsonx',
        'nebius': 'nebius',
        'xinference': 'xinference',
        'lambda_ai': 'lambda_ai',
        'predibase': 'predibase',
        'triton': 'triton',
        'galadriel': 'galadriel',
        'friendliai': 'friendliai',
        'litellm_proxy': 'litellm_proxy',
        'vercel_ai_gateway': 'vercel_ai_gateway',
    }

router = APIRouter(prefix="/api/config", tags=["config"])

async def _fetch_litellm_model_map(force_refresh: bool = False) -> Dict[str, Any]:
    """从 litellm GitHub 获取模型成本映射表"""
    global _litellm_model_cache, _model_cache_timestamp, _litellm_providers
    import time

    current_time = time.time()
    if not force_refresh and _litellm_model_cache and (current_time - _model_cache_timestamp) < _MODEL_CACHE_DURATION:
        return _litellm_model_cache

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(LITELLM_MODEL_COST_MAP_URL)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    _litellm_model_cache = data
                    _model_cache_timestamp = current_time
                    _litellm_providers = None
                    return _litellm_model_cache
    except Exception as e:
        print(f"[Config] 获取 litellm 模型映射表失败: {e}")

    return {}

def get_models_by_provider(provider: str, model_map: Dict[str, Any]) -> List[Dict[str, str]]:
    """根据提供商从 litellm 模型映射中动态获取模型列表"""
    if not model_map:
        return []

    providers = _get_litellm_providers(model_map)
    aliases = _build_provider_aliases()

    litellm_provider = aliases.get(provider.lower(), provider.lower())

    if litellm_provider not in providers:
        return []

    models = []
    for model_id, model_info in model_map.items():
        if isinstance(model_info, dict):
            model_provider = model_info.get('litellm_provider', '')
            if model_provider == litellm_provider:
                mode = model_info.get('mode', '')
                if mode in ['chat', 'completion']:
                    model_name = model_id.replace('/', ' ').replace('-', ' ').replace('_', ' ').title()
                    models.append({
                        'id': model_id,
                        'name': model_name,
                        'description': f"{model_provider.title()} {mode} model"
                    })

    return models

class ConfigSettings(BaseModel):
    """配置设置"""
    groq_api_keys: List[str] = Field(default_factory=list, description="Groq API Keys列表")
    tavily_api_key: Optional[str] = Field(default="", description="Tavily API Key")
    model_name: str = Field(default="llama-3.3-70b-versatile", description="模型名称")
    temperature: float = Field(default=0.1, description="温度参数")
    enable_key_rotation: bool = Field(default=True, description="是否启用Key轮换")

class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    groq_api_keys: Optional[List[str]] = None
    tavily_api_key: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    enable_key_rotation: Optional[bool] = None

class KeyRotationStatus(BaseModel):
    """Key轮换状态"""
    enabled: bool
    total_keys: int
    active_key: Optional[str]
    cooling_keys: int
    total_calls: int
    total_switches: int

@router.get("/", response_model=ConfigSettings)
async def get_config():
    """获取当前配置"""
    return ConfigSettings(
        groq_api_keys=settings.groq_api_keys,
        tavily_api_key=settings.tavily_api_key,
        model_name=settings.model_name,
        temperature=settings.temperature,
        enable_key_rotation=api_key_manager is not None
    )

@router.put("/")
async def update_config(request: ConfigUpdateRequest):
    """更新配置"""
    try:
        updated = False

        # 更新Groq API Keys
        if request.groq_api_keys is not None:
            valid_keys = [k.strip() for k in request.groq_api_keys if k.strip()]
            if valid_keys:
                settings.groq_api_keys = valid_keys
                settings.groq_api_key = valid_keys[0]

                # 根据Key数量和轮换设置决定是否初始化管理器
                if len(valid_keys) > 1 and request.enable_key_rotation:
                    initialize_key_manager(cooldown_seconds=60)
                elif len(valid_keys) == 1:
                    # 只有一个Key，禁用轮换
                    global api_key_manager
                    api_key_manager = None
                updated = True

        # 更新其他配置
        if request.tavily_api_key is not None:
            settings.tavily_api_key = request.tavily_api_key
            updated = True

        if request.model_name is not None:
            settings.model_name = request.model_name
            updated = True

        if request.temperature is not None:
            settings.temperature = request.temperature
            updated = True

        # 处理Key轮换开关
        if request.enable_key_rotation is not None and len(settings.groq_api_keys) > 1:
            if request.enable_key_rotation:
                initialize_key_manager(cooldown_seconds=60)
            else:
                api_key_manager = None
            updated = True

        if not updated:
            return {"success": False, "message": "没有配置需要更新"}

        # 保存到环境变量文件
        await save_config_to_env_file(request)

        return {
            "success": True,
            "message": "配置已更新",
            "config": ConfigSettings(
                groq_api_keys=settings.groq_api_keys,
                tavily_api_key=settings.tavily_api_key,
                model_name=settings.model_name,
                temperature=settings.temperature,
                enable_key_rotation=api_key_manager is not None
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")

@router.get("/key-rotation", response_model=KeyRotationStatus)
async def get_key_rotation_status():
    """获取Key轮换状态"""
    if api_key_manager:
        stats = api_key_manager.get_stats()
        return KeyRotationStatus(
            enabled=True,
            total_keys=len(api_key_manager.keys),
            active_key=stats.get('active_key'),
            cooling_keys=sum(1 for k in api_key_manager.keys if api_key_manager.key_cooldown.get(k, 0) > 0),
            total_calls=stats.get('total_calls', 0),
            total_switches=stats.get('total_switches', 0)
        )
    else:
        return KeyRotationStatus(
            enabled=False,
            total_keys=len(settings.groq_api_keys),
            active_key=settings.groq_api_keys[0] if settings.groq_api_keys else None,
            cooling_keys=0,
            total_calls=0,
            total_switches=0
        )

@router.post("/key-rotation/toggle")
async def toggle_key_rotation(enable: bool):
    """开启/关闭Key轮换"""
    try:
        if len(settings.groq_api_keys) <= 1:
            return {
                "success": False,
                "message": "只有一个API Key，无法启用轮换功能"
            }

        if enable:
            initialize_key_manager(cooldown_seconds=60)
            message = "Key轮换已启用"
        else:
            global api_key_manager
            api_key_manager = None
            message = "Key轮换已禁用"

        return {
            "success": True,
            "message": message,
            "enabled": enable
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")

@router.post("/key-rotation/reset")
async def reset_key_rotation():
    """重置Key轮换状态（清除冷却时间等）"""
    try:
        if api_key_manager:
            api_key_manager.key_cooldown.clear()
            api_key_manager.key_failures.clear()
            api_key_manager.total_calls = 0
            api_key_manager.total_switches = 0
            return {"success": True, "message": "Key轮换状态已重置"}
        else:
            return {"success": False, "message": "Key轮换未启用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

@router.get("/models")
async def get_available_models():
    """获取可用模型列表（向后兼容）"""
    return {
        "models": [
            {
                "id": "llama-3.3-70b-versatile",
                "name": "Llama 3.3 70B (推荐)",
                "description": "最强大的推理模型，适合复杂任务"
            },
            {
                "id": "llama-3.1-8b-instant",
                "name": "Llama 3.1 8B",
                "description": "快速响应模型，适合简单任务"
            }
        ]
    }

@router.get("/models/{provider}")
async def get_provider_models(provider: str, api_key: Optional[str] = None):
    """获取指定提供商的可用模型列表（动态从 litellm 获取）"""
    try:
        if provider == "tavily":
            return _get_tavily_models()

        model_map = await _fetch_litellm_model_map()
        models = get_models_by_provider(provider, model_map)

        if models:
            return {
                "success": True,
                "message": f"成功获取 {provider} 模型列表",
                "data": {
                    "provider": provider,
                    "models": models
                }
            }
        else:
            return {
                "success": False,
                "message": f"未找到 {provider} 的模型列表",
                "data": {
                    "provider": provider,
                    "models": []
                }
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取 {provider} 模型列表失败: {str(e)}",
            "data": {
                "provider": provider,
                "models": []
            }
        }

def _get_tavily_models():
    """获取Tavily模型列表（固定）"""
    return {
        "success": True,
        "message": "Tavily搜索服务",
        "data": {
            "provider": "tavily",
            "models": [
                {
                    "id": "search",
                    "name": "Search API",
                    "description": "Tavily搜索服务"
                }
            ]
        }
    }

async def save_config_to_env_file(request: ConfigUpdateRequest):
    """保存配置到.env文件"""
    env_path = Path(__file__).parent.parent.parent / ".env"

    # 读取现有配置
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    # 更新配置
    if request.groq_api_keys:
        env_vars['GROQ_API_KEYS'] = ','.join(request.groq_api_keys)

    if request.tavily_api_key is not None:
        env_vars['TAVILY_API_KEY'] = request.tavily_api_key

    if request.model_name:
        env_vars['MODEL_NAME'] = request.model_name

    if request.temperature is not None:
        env_vars['TEMPERATURE'] = str(request.temperature)

    # 写回文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("# Shadow Writing Agent Configuration\n")
        f.write("# Auto-generated by config API\n\n")
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
