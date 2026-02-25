"""
Unit tests for LLMClient class methods.

Tests cover:
- LLM API calling with retry logic
- Error handling for various failure scenarios
- Response parsing and validation
- Rate limiting for ChatGPT
- Edge cases and boundary conditions
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.llm_client import LLMClient, CHATGPT_RATE_LIMIT_DELAY


class TestLLMClientInitialization:
    """Test LLMClient initialization."""

    @patch('src.llm_client.config')
    def test_init_with_default_provider(self, mock_config):
        """Test initialization with default provider."""
        mock_config.get_provider_info.return_value = Mock(name="test", env_key="TEST_KEY", api_url="https://test.com", model="test-model")
        mock_config.get_api_key.return_value = "test_key"
        mock_config.logger = Mock()

        client = LLMClient()
        assert client.provider_info is not None
        assert client.api_key == "test_key"

    @patch('src.llm_client.config')
    def test_init_with_custom_provider(self, mock_config):
        """Test initialization with custom provider."""
        mock_config.set_provider.return_value = None
        mock_provider_info = MagicMock()
        mock_provider_info.name = "custom"
        mock_provider_info.env_key = "CUSTOM_KEY"
        mock_provider_info.api_url = "https://test.com"
        mock_provider_info.model = "test-model"
        mock_config.get_provider_info.return_value = mock_provider_info
        mock_config.get_api_key.return_value = "custom_key"
        mock_config.logger = Mock()

        client = LLMClient(provider="custom")
        assert client.provider_info.name == "custom"


class TestLLMClientSummarize:
    """Test LLMClient summarize method."""

    @patch('src.llm_client.config')
    @patch('src.llm_client.requests.post')
    def test_summarize_success(self, mock_post, mock_config):
        """Test successful summarize call."""
        # Setup config mock
        mock_config.current_provider = "test"
        mock_config.get_provider_info.return_value = Mock(
            name="test",
            env_key="TEST_KEY",
            api_url="https://api.test.com/v1/chat/completions",
            model="test-model"
        )
        mock_config.get_api_key.return_value = "test_key"
        mock_config.PROMPT_TEMPLATE.format.return_value = "formatted prompt"
        mock_config.logger = Mock()

        # Setup response mock - content must be >= 100 chars, contain "요약", and have >= 2 "###" headers
        long_content = """### 3줄 요약

이것은 테스트 요약 내용입니다. 충분한 길이의 텍스트가 필요합니다. 더 많은 텍스트를 추가합니다.

### 주요 내용

- 내용 1: 첫 번째 주요 내용에 대한 설명입니다.
- 내용 2: 두 번째 주요 내용에 대한 설명입니다.

### 결론

테스트 요약이 여기에 포함됩니다.
"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({
            "choices": [{
                "message": {"content": long_content},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 100}
        }).encode('utf-8')
        mock_post.return_value = mock_response

        client = LLMClient()
        result = client.summarize("Test text")

        assert result["success"] is True
        assert long_content in result["content"]
        assert "usage" in result

    @patch('src.llm_client.config')
    @patch('src.llm_client.requests.post')
    def test_summarize_missing_api_key(self, mock_post, mock_config):
        """Test summarize with missing API key."""
        mock_config.current_provider = "test"
        mock_config.get_provider_info.return_value = Mock(name="test", env_key="TEST_KEY")
        mock_config.get_api_key.return_value = None
        mock_config.logger = Mock()

        client = LLMClient()
        result = client.summarize("Test text")

        assert result["success"] is False
        assert "API Key is missing" in result["error"]
        mock_post.assert_not_called()

    @patch('src.llm_client.config')
    @patch('src.llm_client.requests.post')
    def test_summarize_4xx_error(self, mock_post, mock_config):
        """Test summarize with 4xx client error."""
        mock_config.current_provider = "test"
        mock_config.get_provider_info.return_value = Mock(
            name="test",
            env_key="TEST_KEY",
            api_url="https://api.test.com/v1/chat/completions",
            model="test-model"
        )
        mock_config.get_api_key.return_value = "test_key"
        mock_config.PROMPT_TEMPLATE.format.return_value = "prompt"
        mock_config.logger = Mock()

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        client = LLMClient()
        result = client.summarize("Test text")

        assert result["success"] is False
        assert "401" in result["error"]

    @patch('src.llm_client.config')
    @patch('src.llm_client.requests.post')
    def test_summarize_5xx_retry(self, mock_post, mock_config):
        """Test summarize with 5xx server error and retry."""
        mock_config.current_provider = "test"
        mock_config.get_provider_info.return_value = Mock(
            name="test",
            env_key="TEST_KEY",
            api_url="https://api.test.com/v1/chat/completions",
            model="test-model"
        )
        mock_config.get_api_key.return_value = "test_key"
        mock_config.PROMPT_TEMPLATE.format.return_value = "prompt"
        mock_config.logger = Mock()

        # First call fails with 500, second succeeds
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_response_error.text = "Internal Server Error"

        # Content must be >= 100 chars, contain "요약", and have >= 2 "###" headers
        valid_content = """### 3줄 요약

이것은 테스트 요약 내용입니다. 충분한 길이의 텍스트가 필요합니다. 더 많은 텍스트를 추가합니다.

### 주요 내용

- 내용 1: 첫 번째 주요 내용에 대한 설명입니다.
- 내용 2: 두 번째 주요 내용에 대한 설명입니다.
"""
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.content = json.dumps({
            "choices": [{
                "message": {"content": valid_content},
                "finish_reason": "stop"
            }]
        }).encode('utf-8')

        mock_post.side_effect = [mock_response_error, mock_response_success]

        client = LLMClient()
        result = client.summarize("Test text")

        assert result["success"] is True
        assert mock_post.call_count == 2

    @patch('src.llm_client.config')
    @patch('src.llm_client.requests.post')
    def test_summarize_timeout_error(self, mock_post, mock_config):
        """Test summarize with timeout error."""
        mock_config.current_provider = "test"
        mock_config.get_provider_info.return_value = Mock(
            name="test",
            env_key="TEST_KEY",
            api_url="https://api.test.com/v1/chat/completions",
            model="test-model"
        )
        mock_config.get_api_key.return_value = "test_key"
        mock_config.PROMPT_TEMPLATE.format.return_value = "prompt"
        mock_config.logger = Mock()

        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        client = LLMClient()
        result = client.summarize("Test text")

        assert result["success"] is False
        assert "Failed after" in result["error"]

    @patch('src.llm_client.config')
    @patch('src.llm_client.requests.post')
    def test_summarize_connection_error(self, mock_post, mock_config):
        """Test summarize with connection error."""
        mock_config.current_provider = "test"
        mock_config.get_provider_info.return_value = Mock(
            name="test",
            env_key="TEST_KEY",
            api_url="https://api.test.com/v1/chat/completions",
            model="test-model"
        )
        mock_config.get_api_key.return_value = "test_key"
        mock_config.PROMPT_TEMPLATE.format.return_value = "prompt"
        mock_config.logger = Mock()

        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        client = LLMClient()
        result = client.summarize("Test text")

        assert result["success"] is False
        assert "Failed after" in result["error"]

    @patch('src.llm_client.config')
    @patch('src.llm_client.requests.post')
    def test_summarize_max_retries_exceeded(self, mock_post, mock_config):
        """Test summarize when max retries exceeded."""
        mock_config.current_provider = "test"
        mock_config.get_provider_info.return_value = Mock(
            name="test",
            env_key="TEST_KEY",
            api_url="https://api.test.com/v1/chat/completions",
            model="test-model"
        )
        mock_config.get_api_key.return_value = "test_key"
        mock_config.PROMPT_TEMPLATE.format.return_value = "prompt"
        mock_config.logger = Mock()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        client = LLMClient()
        result = client.summarize("Test text")

        assert result["success"] is False
        assert "Failed after 3 retries" in result["error"]
        assert mock_post.call_count == 3


class TestResponseParsing:
    """Test response parsing methods."""

    def test_parse_response_success(self):
        """Test successful response parsing."""
        client = LLMClient()
        client.logger = Mock()

        # Content must be >= 100 chars, contain "요약", and have >= 2 "###" headers
        valid_content = """### 3줄 요약

이것은 테스트 요약 내용입니다. 충분한 길이의 텍스트가 필요합니다. 더 많은 텍스트를 추가합니다.

### 주요 내용

- 내용 1: 첫 번째 주요 내용에 대한 설명입니다.
- 내용 2: 두 번째 주요 내용에 대한 설명입니다.
"""
        data = {
            "choices": [{
                "message": {"content": valid_content},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 100}
        }

        result = client._parse_response(data)
        assert result["success"] is True
        assert result["content"] == valid_content
        assert result["usage"]["total_tokens"] == 100

    def test_parse_response_missing_content(self):
        """Test parsing response with missing content."""
        client = LLMClient()
        client.logger = Mock()

        data = {
            "choices": [{
                "message": {"content": "Short"},
                "finish_reason": "stop"
            }]
        }

        result = client._parse_response(data)
        assert result["success"] is False
        assert "too short" in result["error"]

    def test_parse_response_truncated(self):
        """Test parsing truncated response."""
        client = LLMClient()
        client.logger = Mock()

        data = {
            "choices": [{
                "message": {"content": "Valid content with enough length to pass validation"},
                "finish_reason": "length"
            }]
        }

        result = client._parse_response(data)
        assert result["success"] is False
        assert "truncated" in result["error"]

    def test_parse_response_missing_key(self):
        """Test parsing response with missing key."""
        client = LLMClient()
        client.logger = Mock()

        data = {
            "choices": [{}]
        }

        result = client._parse_response(data)
        assert result["success"] is False
        assert "parsing failed" in result["error"]

    def test_parse_response_minimax_error(self):
        """Test parsing MiniMax error response."""
        client = LLMClient()
        client.logger = Mock()

        data = {
            "base_resp": {
                "status_code": 1,
                "status_msg": "Invalid request"
            },
            "choices": [{
                "message": {"content": "Content"},
                "finish_reason": "stop"
            }]
        }

        result = client._parse_response(data)
        assert result["success"] is False
        assert "Invalid request" in result["error"]


class TestResponseValidation:
    """Test response content validation."""

    def test_validate_response_content_valid(self):
        """Test validation of valid content."""
        client = LLMClient()
        # Content must be >= 100 chars, contain "요약", and have >= 2 "###" headers
        content = """### 3줄 요약

이것은 테스트 요약 내용입니다. 충분한 길이의 텍스트가 필요합니다. 더 많은 텍스트를 추가합니다.

### 주요 내용

- 내용 1: 첫 번째 주요 내용에 대한 설명입니다.
- 내용 2: 두 번째 주요 내용에 대한 설명입니다.
"""

        result = client._validate_response_content(content)
        assert result["valid"] is True
        assert result["reason"] == ""

    def test_validate_response_content_too_short(self):
        """Test validation of too short content."""
        client = LLMClient()
        content = "Short"

        result = client._validate_response_content(content)
        assert result["valid"] is False
        assert "too short" in result["reason"]

    def test_validate_response_content_missing_sections(self):
        """Test validation of content missing required sections."""
        client = LLMClient()
        content = "x" * 200  # Long enough but no required sections

        result = client._validate_response_content(content)
        assert result["valid"] is False
        assert "missing required sections" in result["reason"]

    def test_validate_response_content_incomplete(self):
        """Test validation of incomplete content."""
        client = LLMClient()
        # Content >= 100 chars, has "요약", but ends with "..." and has < 2 "###" headers
        # This triggers 2 incomplete patterns: ends with "..." and count("###") < 2
        content = "### 3줄 요약\n\n이것은 테스트 요약 내용입니다. 충분한 길이의 텍스트가 필요합니다. xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx. 내용이 중간에 끊..."

        result = client._validate_response_content(content)
        assert result["valid"] is False
        assert "incomplete" in result["reason"]


class TestResponseTextParsing:
    """Test response text parsing."""

    def test_parse_response_text_success(self):
        """Test parsing valid JSON response text."""
        client = LLMClient()
        client.logger = Mock()

        # Content must be >= 100 chars, contain "요약", and have >= 2 "###" headers
        valid_content = """### 3줄 요약

이것은 테스트 요약 내용입니다. 충분한 길이의 텍스트가 필요합니다. 더 많은 텍스트를 추가합니다.

### 주요 내용

- 내용 1: 첫 번째 주요 내용에 대한 설명입니다.
- 내용 2: 두 번째 주요 내용에 대한 설명입니다.
"""
        text = json.dumps({
            "choices": [{
                "message": {"content": valid_content},
                "finish_reason": "stop"
            }]
        })

        result = client._parse_response_text(text)
        assert result["success"] is True

    def test_parse_response_text_invalid_json(self):
        """Test parsing invalid JSON response text."""
        client = LLMClient()
        client.logger = Mock()

        text = "Not valid JSON"

        result = client._parse_response_text(text)
        assert result["success"] is False
        assert "JSON parsing failed" in result["error"]


class TestRateLimiting:
    """Test ChatGPT rate limiting."""

    @patch('src.llm_client.config')
    @patch('src.llm_client.time.sleep')
    @patch('src.llm_client.time.time')
    def test_wait_for_rate_limit_chatgpt(self, mock_time, mock_sleep, mock_config):
        """Test rate limit wait for ChatGPT."""
        mock_config.current_provider = "chatgpt"
        mock_config.logger = Mock()

        # Simulate recent request
        mock_time.return_value = 100

        client = LLMClient()
        LLMClient._last_chatgpt_request_time = 99  # 1 second ago

        client._wait_for_rate_limit()

        # Should sleep because not enough time passed
        mock_sleep.assert_called_once()

    @patch('src.llm_client.config')
    @patch('src.llm_client.time.sleep')
    def test_wait_for_rate_limit_non_chatgpt(self, mock_sleep, mock_config):
        """Test no rate limit wait for non-ChatGPT providers."""
        mock_config.current_provider = "glm"
        mock_config.logger = Mock()

        client = LLMClient()
        client._wait_for_rate_limit()

        # Should not sleep
        mock_sleep.assert_not_called()

    @patch('src.llm_client.config')
    @patch('src.llm_client.time.sleep')
    @patch('src.llm_client.time.time')
    def test_wait_for_rate_limit_first_request(self, mock_time, mock_sleep, mock_config):
        """Test no wait on first ChatGPT request."""
        mock_config.current_provider = "chatgpt"
        mock_config.logger = Mock()
        mock_time.return_value = 100

        client = LLMClient()
        LLMClient._last_chatgpt_request_time = 0  # No previous request

        client._wait_for_rate_limit()

        # Should not sleep on first request
        mock_sleep.assert_not_called()


class TestLLMClientLegacyAlias:
    """Test legacy alias for backward compatibility."""

    @patch('src.llm_client.LLMClient')
    def test_glm_client_alias(self, mock_llm):
        """Test that GLMClient is an alias for LLMClient."""
        from src.llm_client import GLMClient

        assert GLMClient is LLMClient
