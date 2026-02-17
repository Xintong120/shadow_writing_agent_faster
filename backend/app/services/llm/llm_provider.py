from typing import Any, Dict, List, Optional, Generator, Union
from app.infrastructure.config.llm_config import LLMConfig, LLMProvider, get_litellm_model
from app.services.llm.llm_factory import LLMFactory
from app.infrastructure.config.llm_config_service import LLMConfigService
from app.infrastructure.config.api_key_manager import ProviderKeyManager
import logging

logger = logging.getLogger(__name__)


def _is_retryable_error(error: Exception) -> bool:
    """检测错误是否是可重试的（使用 litellm 内置异常类型）"""
    from litellm import RateLimitError, APIError, APIConnectionError, Timeout, ServiceUnavailableError
    
    retryable_exceptions = (
        RateLimitError,
        APIConnectionError,
        Timeout,
        ServiceUnavailableError,
        APIError,
    )
    
    return isinstance(error, retryable_exceptions)


class UnifiedLLMProvider:
    """统一的 LLM Provider"""

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        初始化 Provider

        Args:
            config: LLMConfig 对象
            provider: Provider 名称（与 config 二选一）
            model: 模型名称（可选）
        """
        if config is not None:
            self.config = config
        elif provider is not None:
            service = LLMConfigService()
            cfg = service.get_config(provider, model or "")
            if cfg is None:
                raise ValueError(f"No config found for provider: {provider}")
            self.config = cfg
        else:
            raise ValueError("Either config or provider must be provided")

        self._call_fn = LLMFactory.create(self.config)

    @staticmethod
    def create_for_purpose(purpose: str) -> "UnifiedLLMProvider":
        """
        根据用途创建 LLM

        Args:
            purpose: 用途名称，如 "debate", "shadow_writing", "validation" 等

        Returns:
            UnifiedLLMProvider 实例
        """
        from app.infrastructure.config.llm_model_map import get_model_for_purpose

        prov, mod = get_model_for_purpose(purpose)
        cfg = LLMConfig(provider=prov, model=mod)
        return UnifiedLLMProvider(config=cfg)

    def call(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """同步调用 LLM"""
        return self._call_fn(messages, **kwargs)

    def __call__(self, prompt: str, output_format: Optional[Dict] = None, **kwargs) -> Any:
        """
        使对象可调用，兼容旧代码调用方式

        Args:
            prompt: 提示词
            output_format: 输出格式（兼容旧接口）
            **kwargs: 其他参数

        Returns:
            LLM 响应
        """
        messages = [{"role": "user", "content": prompt}]
        if output_format is not None:
            kwargs["response_format"] = output_format
        return self.call(messages, **kwargs)

    def stream_call(self, messages: List[Dict[str, str]], **kwargs) -> Generator:
        """流式调用 LLM（支持自动重试和轮换）"""
        from litellm import completion
        
        provider = self.config.provider.value
        current_key = ""
        
        while True:
            try:
                current_key = ProviderKeyManager.get_key(provider)
                
                response = completion(
                    model=self._get_model_identifier(),
                    messages=messages,
                    stream=True,
                    api_key=current_key,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    **kwargs
                )

                for chunk in response:
                    yield chunk
                return  # 成功完成
                
            except Exception as e:
                if _is_retryable_error(e):
                    logger.warning(f"[UnifiedLLMProvider] Stream retryable error: {str(e)[:100]}")
                    ProviderKeyManager.mark_failure(provider, current_key, str(e))
                    # 继续重试，使用下一个 key
                    continue
                else:
                    # 非重试错误直接抛出
                    raise

    def _get_model_identifier(self) -> str:
        """获取模型标识符"""
        return get_litellm_model(self.config.provider, self.config.model)

    def _get_api_key(self) -> str:
        """获取 API Key"""
        service = LLMConfigService()
        return service.get_api_key(self.config.provider.value)

    @property
    def available(self) -> bool:
        """检查是否可用"""
        return bool(self._get_api_key())

    def get_usage(self) -> Dict:
        """获取使用统计"""
        return {}
