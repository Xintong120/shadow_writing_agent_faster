from typing import Callable, Any, Optional
from app.infrastructure.config.llm_config import LLMConfig
from app.infrastructure.config.api_key_manager import ProviderKeyManager
import json_repair
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
        APIError,  # 通用 API 错误也可能需要重试
    )
    
    return isinstance(error, retryable_exceptions)


class LLMFactory:
    @staticmethod
    def create(config: LLMConfig) -> Callable:
        """创建 LLM 调用函数（通用方案，支持 100+ provider）"""
        from litellm import completion

        model = f"{config.provider.value}/{config.model}"
        provider = config.provider.value

        def call_fn(messages, **kwargs) -> Any:
            last_error = None
            current_key = ""
            
            while True:
                try:
                    current_key = ProviderKeyManager.get_key(provider)

                    params = {
                        "model": model,
                        "messages": messages,
                        "api_key": current_key,
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                    }

                    # Fallback 机制：处理不同 provider 的 response_format 差异
                    if config.response_format:
                        try:
                            params["response_format"] = config.response_format
                            response = completion(**params)
                        except Exception:
                            params["response_format"] = {"type": "json_object"}
                            response = completion(**params)
                    else:
                        response = completion(**params)

                    # 解析 JSON
                    content = response.choices[0].message.content
                    if content is None:
                        raise ValueError("LLM returned empty response")
                    result = json_repair.loads(str(content))

                    # 标准化结果格式
                    if isinstance(result, list):
                        if len(result) > 0 and isinstance(result[0], dict):
                            result = result[0]
                        else:
                            result = {"raw": content}
                    
                    if not isinstance(result, dict):
                        result = {"raw": content}

                    return result

                except Exception as e:
                    last_error = e
                    if _is_retryable_error(e):
                        logger.warning(f"[LLMFactory] Retryable error: {str(e)[:100]}")
                        ProviderKeyManager.mark_failure(provider, current_key, str(e))
                        continue  # 继续重试，使用下一个 key
                    else:
                        # 非重试错误直接抛出
                        raise

            # 理论上不会到达这里，但为了完整性
            raise last_error if last_error else Exception("LLM call failed after all retries")

        return call_fn

    @staticmethod
    def create_langchain_llm(provider: str, model: str, streaming: bool = False, temperature: float = 0.1):
        """创建 LangChain LLM 对象（用于 LangServe），支持所有 litellm provider"""
        from langchain_litellm import ChatLiteLLM
        from langchain_core.runnables import RunnableLambda
        from app.infrastructure.config.api_key_manager import ProviderKeyManager
        
        base_llm = ChatLiteLLM(
            model=f"{provider}/{model}",
            temperature=temperature,
            streaming=streaming,
            api_key=ProviderKeyManager.get_key(provider),
        )

        if streaming:
            # 流式输出不需要重试包装，保持原样
            return base_llm

        # 非流式：添加重试包装
        def invoke_with_retry(input_data, config=None):
            last_error = None
            current_key = ""
            
            while True:
                try:
                    # 每次调用都获取最新的 key
                    current_key = ProviderKeyManager.get_key(provider)
                    
                    # 重新创建 LLM 以使用新 key
                    llm = ChatLiteLLM(
                        model=f"{provider}/{model}",
                        temperature=temperature,
                        streaming=False,
                        api_key=current_key,
                    )
                    
                    if config:
                        return llm.invoke(input_data, config)
                    return llm.invoke(input_data)
                    
                except Exception as e:
                    last_error = e
                    if _is_retryable_error(e):
                        logger.warning(f"[LLMFactory] LangChain retryable error: {str(e)[:100]}")
                        ProviderKeyManager.mark_failure(provider, current_key, str(e))
                        continue
                    raise

            raise last_error if last_error else Exception("LLM invoke failed after all retries")

        return RunnableLambda(invoke_with_retry)
