import pytest
from unittest.mock import patch, MagicMock
from app.infrastructure.config.llm_config import LLMConfig, LLMProvider
from app.services.llm.llm_provider import UnifiedLLMProvider


class TestUnifiedLLMProvider:
    """测试统一 Provider"""

    def test_init_from_config(self):
        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        provider = UnifiedLLMProvider(config=config)
        assert provider.config.temperature == 0.1
        assert provider.config.provider == LLMProvider.GROQ

    def test_init_from_provider_name(self):
        provider = UnifiedLLMProvider(provider="groq", model="llama-3.3-70b-versatile")
        assert provider.config.provider == LLMProvider.GROQ

    def test_init_without_params_raises(self):
        with pytest.raises(ValueError, match="Either config or provider must be provided"):
            UnifiedLLMProvider()

    @patch('litellm.completion')
    def test_call(self, mock_completion):
        mock_completion.return_value = {"choices": [{"message": {"content": "hello"}}]}

        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model="llama-3.3-70b-versatile"
        )
        provider = UnifiedLLMProvider(config=config)

        result = provider.call([{"role": "user", "content": "hi"}])
        assert "choices" in result

    def test_available_with_api_key(self):
        with patch('app.services.llm.llm_provider.LLMConfigService.get_api_key', return_value="test-api-key"):
            config = LLMConfig(
                provider=LLMProvider.GROQ,
                model="llama-3.3-70b-versatile"
            )
            provider = UnifiedLLMProvider(config=config)
            assert provider.available is True

    def test_not_available_without_api_key(self):
        with patch('os.getenv', return_value=None):
            config = LLMConfig(
                provider=LLMProvider.GROQ,
                model="llama-3.3-70b-versatile"
            )
            provider = UnifiedLLMProvider(config=config)
            assert provider.available is False

    @patch('litellm.completion')
    def test_callable(self, mock_completion):
        """测试 __call__ 方法使对象可调用"""
        mock_completion.return_value = {"choices": [{"message": {"content": "hello"}}]}

        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model="llama-3.3-70b-versatile"
        )
        provider = UnifiedLLMProvider(config=config)

        # 测试 __call__ 方法
        result = provider("test prompt", {"type": "json_object"})
        assert "choices" in result
