import pytest
from app.infrastructure.config.llm_config import LLMConfig, LLMProvider, DEFAULT_CONFIGS, get_litellm_model


class TestLLMConfig:
    """测试配置类"""

    def test_default_values(self):
        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model="llama-3.3-70b-versatile"
        )
        assert config.temperature == 0.1
        assert config.max_tokens == 4096
        assert config.top_p == 1.0
        assert config.enabled is True
        assert config.is_default is False

    def test_custom_values(self):
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            temperature=0.5,
            max_tokens=8192
        )
        assert config.temperature == 0.5
        assert config.max_tokens == 8192

    def test_groq_provider(self):
        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY"
        )
        assert config.provider == LLMProvider.GROQ
        assert config.api_key_env == "GROQ_API_KEY"

    def test_mistral_provider(self):
        config = LLMConfig(
            provider=LLMProvider.MISTRAL,
            model="mistral-large-latest",
            api_key_env="MISTRAL_API_KEY"
        )
        assert config.provider == LLMProvider.MISTRAL
        assert config.model == "mistral-large-latest"

    def test_deepseek_provider(self):
        config = LLMConfig(
            provider=LLMProvider.DEEPSEEK,
            model="deepseek-chat",
            api_key_env="DEEPSEEK_API_KEY"
        )
        assert config.provider == LLMProvider.DEEPSEEK


class TestGetLitellmModel:
    """测试 litellm 模型名称映射"""

    def test_groq_mapping(self):
        model = get_litellm_model(LLMProvider.GROQ, "llama-3.3-70b-versatile")
        assert model == "groq/llama-3.3-70b-versatile"

    def test_mistral_mapping(self):
        model = get_litellm_model(LLMProvider.MISTRAL, "mistral-large-latest")
        assert model == "mistral-large-latest"

    def test_openai_mapping(self):
        model = get_litellm_model(LLMProvider.OPENAI, "gpt-4o")
        assert model == "openai/gpt-4o"

    def test_deepseek_mapping(self):
        model = get_litellm_model(LLMProvider.DEEPSEEK, "deepseek-chat")
        assert model == "deepseek/deepseek-chat"


class TestDefaultConfigs:
    """测试预设配置"""

    def test_groq_default_exists(self):
        assert "groq/llama-3.3-70b-versatile" in DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS["groq/llama-3.3-70b-versatile"]
        assert config.provider == LLMProvider.GROQ
        assert config.is_default is True

    def test_mistral_default_exists(self):
        assert "mistral/mistral-large-latest" in DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS["mistral/mistral-large-latest"]
        assert config.provider == LLMProvider.MISTRAL

    def test_openai_default_exists(self):
        assert "openai/gpt-4o" in DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS["openai/gpt-4o"]
        assert config.provider == LLMProvider.OPENAI

    def test_deepseek_default_exists(self):
        assert "deepseek/deepseek-chat" in DEFAULT_CONFIGS
        config = DEFAULT_CONFIGS["deepseek/deepseek-chat"]
        assert config.provider == LLMProvider.DEEPSEEK
