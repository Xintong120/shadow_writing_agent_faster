from typing import Optional
from app.infrastructure.config.llm_config import LLMConfig, LLMProvider
from app.infrastructure.config.llm_config_db import LLMConfigDB
from app.infrastructure.config.api_key_manager import ProviderKeyManager
import os


def _is_dev_environment() -> bool:
    """判断是否为开发环境（优先使用 .env 配置）"""
    from app.infrastructure.config import get_settings
    settings = get_settings()
    # 如果 .env 中配置了有效的 model_name 或 API key，则为开发环境
    return bool(settings.model_name or settings.groq_api_key or settings.mistral_api_key)


class LLMConfigService:
    """统一的 LLM 配置服务"""

    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._db = LLMConfigDB()
            except Exception:
                cls._db = None
        return cls._instance

    @staticmethod
    def get_supported_providers() -> list:
        """动态获取支持的 Provider 列表"""
        from app.infrastructure.config.llm_model_map import get_llm_model_map
        try:
            model_map = get_llm_model_map()
            providers = set()
            for config in model_map.values():
                if isinstance(config, dict) and "provider" in config:
                    providers.add(config["provider"])
            return list(providers)
        except Exception:
            return ["groq", "mistral", "openai", "deepseek"]

    def get_config(self, provider: str, model: str = "") -> Optional[LLMConfig]:
        """获取配置（开发环境优先使用 .env，生产环境使用 SQLite）"""
        # 开发环境：从环境变量读取
        if _is_dev_environment():
            return self._get_config_from_env(provider, model)
        
        # 生产环境：优先从 SQLite 读取
        if self._db is not None:
            config = self._db.get_config(provider)
            if config is not None:
                return config
        
        # 回退到环境变量
        return self._get_config_from_env(provider, model)

    def _get_config_from_env(self, provider: str, model: str = "") -> Optional[LLMConfig]:
        """从环境变量获取配置"""
        from app.infrastructure.config import get_settings
        from app.infrastructure.config.llm_config import LLMConfig as LLMConfigModel
        
        settings = get_settings()
        
        # 根据 provider 确定使用的 model
        if model:
            model_name = model
        elif provider == "groq":
            model_name = settings.model_name or "llama-3.3-70b-versatile"
        elif provider == "mistral":
            model_name = settings.mistral_model_name or "mistral-large-latest"
        else:
            model_name = "gpt-4o"
        
        return LLMConfigModel(
            provider=LLMProvider(provider),
            model=model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            top_p=settings.top_p,
            frequency_penalty=settings.frequency_penalty,
        )

    def get_api_key(self, provider: str) -> str:
        """获取 API Key（优先从 SQLite 获取，回退到环境变量）"""
        if self._db is not None:
            api_key = self._db.get_api_key(provider)
            if api_key:
                return api_key

        keys = self._get_api_keys_from_env(provider)
        return keys[0] if keys else ""

    def get_api_keys(self, provider: str) -> list:
        """获取多个 API Key（支持轮换）"""
        if self._db is not None:
            keys = self._db.get_api_keys(provider)
            if keys:
                return keys

        return self._get_api_keys_from_env(provider)

    def _get_api_keys_from_env(self, provider: str) -> list:
        """从环境变量获取多个 API Key"""
        keys = []

        if provider == "groq":
            keys_str = os.getenv("GROQ_API_KEYS", "")
            if keys_str:
                import json
                try:
                    keys = json.loads(keys_str)
                except json.JSONDecodeError:
                    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            elif os.getenv("GROQ_API_KEY"):
                keys = [os.getenv("GROQ_API_KEY")]
        elif provider == "mistral":
            for i in range(1, 10):
                key = os.getenv(f"MISTRAL_API_KEY_{i}", "")
                if key:
                    keys.append(key)
                else:
                    break
        else:
            env_key = f"{provider.upper()}_API_KEY"
            key = os.getenv(env_key, "")
            if key:
                keys = [key]

        return keys

    def get_key_manager(self, provider: str):
        """获取指定 Provider 的 Key Manager（支持轮换）"""
        return ProviderKeyManager.get_manager(provider)

    def list_available(self):
        """列出可用的 Provider 和 Model"""
        from app.infrastructure.config import get_settings
        settings = get_settings()

        available = []
        for provider in settings.get_available_api_providers():
            config = self.get_config(provider)
            if config:
                available.append((provider, config.model))
        return available

    def save_config(self, config: LLMConfig, api_key: Optional[str] = None):
        """保存配置"""
        if self._db is not None:
            self._db.save_config(config, api_key or "")
        else:
            raise RuntimeError("Cannot save config in non-production mode")

    def save_api_keys(self, provider: str, keys: list, rotation_enabled: bool = False):
        """保存多个 API Key"""
        if self._db is not None:
            self._db.save_api_keys(provider, keys, rotation_enabled)
            ProviderKeyManager.clear_cache(provider)
        else:
            raise RuntimeError("Cannot save API keys in non-production mode")

    def get_model_for_purpose(self, purpose: str):
        """获取指定用途的模型配置"""
        from app.infrastructure.config.llm_model_map import get_model_for_purpose
        return get_model_for_purpose(purpose)

    def get_model_map(self) -> dict:
        """获取完整的模型映射配置"""
        from app.infrastructure.config.llm_model_map import get_llm_model_map
        if self._db is not None:
            try:
                return self._db.get_model_map()
            except Exception:
                pass
        return get_llm_model_map()
