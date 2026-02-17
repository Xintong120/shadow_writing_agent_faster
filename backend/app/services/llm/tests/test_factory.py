import pytest
from unittest.mock import patch, MagicMock
from app.infrastructure.config.llm_config import LLMConfig, LLMProvider
from app.services.llm.llm_factory import LLMFactory


class TestLLMFactory:
    """测试工厂类"""

    @patch('litellm.completion')
    def test_create_groq(self, mock_completion):
        mock_completion.return_value = {"choices": [{"message": {"content": "test"}}]}

        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model="llama-3.3-70b-versatile"
        )
        call_fn = LLMFactory.create(config)

        result = call_fn([{"role": "user", "content": "hello"}])
        assert result["choices"][0]["message"]["content"] == "test"

    @patch('mistralai.Mistral')
    def test_create_mistral(self, mock_mistral):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test"))]
        mock_client.chat.complete.return_value = mock_response
        mock_mistral.return_value = mock_client

        config = LLMConfig(
            provider=LLMProvider.MISTRAL,
            model="mistral-large-latest"
        )
        call_fn = LLMFactory.create(config)

        result = call_fn([{"role": "user", "content": "hello"}])
        assert result.choices[0].message.content == "test"

    @patch('openai.OpenAI')
    def test_create_openai(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o"
        )
        call_fn = LLMFactory.create(config)

        result = call_fn([{"role": "user", "content": "hello"}])
        assert result.choices[0].message.content == "test"

    @patch('openai.OpenAI')
    def test_create_deepseek(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        config = LLMConfig(
            provider=LLMProvider.DEEPSEEK,
            model="deepseek-chat"
        )
        call_fn = LLMFactory.create(config)

        result = call_fn([{"role": "user", "content": "hello"}])
        assert result.choices[0].message.content == "test"

    def test_unsupported_provider(self):
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-opus"
        )
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMFactory.create(config)
