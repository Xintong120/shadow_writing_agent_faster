# services/llm/factory.py
"""
LLM 服务工厂
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.config.api_key_manager import APIKeyManager


class LLMService:
    """LLM 服务"""

    def __init__(self, key_manager: Optional["APIKeyManager"] = None):
        self._key_manager = key_manager

    def _get_key_manager(self) -> Optional["APIKeyManager"]:
        if self._key_manager is not None:
            return self._key_manager

        from app.infrastructure.config import get_settings
        from app.infrastructure.config.api_key_manager import APIKeyManager
        
        settings = get_settings()
        
        # 收集所有可用的 keys
        all_keys = []
        if settings.groq_api_key:
            all_keys.extend(settings.groq_api_keys or [settings.groq_api_key])
        if settings.mistral_api_key:
            all_keys.extend(settings.mistral_api_keys or [settings.mistral_api_key])
        if settings.openai_api_key:
            all_keys.append(settings.openai_api_key)
        if settings.deepseek_api_key:
            all_keys.append(settings.deepseek_api_key)

        if all_keys:
            self._key_manager = APIKeyManager(keys=all_keys)
        
        return self._key_manager

    def create_shadow_writing_llm(self):
        """创建 Shadow Writing 专用 LLM（配置驱动）"""
        from app.services.llm.llm_provider import UnifiedLLMProvider
        return UnifiedLLMProvider.create_for_purpose("shadow_writing")

    def create_validation_llm(self):
        """创建验证专用 LLM（配置驱动）"""
        from app.services.llm.llm_provider import UnifiedLLMProvider
        return UnifiedLLMProvider.create_for_purpose("validation")

    def create_quality_llm(self):
        """创建质量检查专用 LLM（配置驱动）"""
        from app.services.llm.llm_provider import UnifiedLLMProvider
        return UnifiedLLMProvider.create_for_purpose("quality_check")

    def create_correction_llm(self):
        """创建修正专用 LLM（配置驱动）"""
        from app.services.llm.llm_provider import UnifiedLLMProvider
        return UnifiedLLMProvider.create_for_purpose("correction")

    def create_finalize_llm(self):
        """创建最终处理专用 LLM（配置驱动）"""
        from app.services.llm.llm_provider import UnifiedLLMProvider
        return UnifiedLLMProvider.create_for_purpose("default")

    @property
    def available_providers(self) -> list:
        """获取可用的 Provider 名称"""
        providers = []
        try:
            if self._get_key_manager():
                if self._key_manager.available_key_count > 0:
                    providers.append("groq")
        except:
            pass
        return providers


_llm_service: Optional[LLMService] = None


def get_llm_service() -> Optional["LLMService"]:
    """获取全局 LLM 服务实例（启动时预初始化）"""
    global _llm_service
    if _llm_service is None:
        try:
            _llm_service = LLMService()
            # 尝试初始化 key_manager
            _llm_service._get_key_manager()
        except ValueError:
            # 没有可用的 API keys，返回 None
            return None
    return _llm_service
