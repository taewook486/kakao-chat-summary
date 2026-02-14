"""Tests for ConfigManager."""
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.config.config_manager import ConfigManager
from src.exceptions import ConfigurationException


class TestConfigManagerSingleton:
    """Test ConfigManager singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Multiple instantiations return the same instance."""
        # Reset singleton state for testing
        ConfigManager._instance = None
        ConfigManager._initialized = False

        instance1 = ConfigManager()
        instance2 = ConfigManager()

        assert instance1 is instance2

    def test_singleton_thread_safety(self):
        """Singleton is thread-safe."""
        import threading

        # Reset singleton state
        ConfigManager._instance = None
        ConfigManager._initialized = False

        instances = []

        def create_instance():
            instances.append(ConfigManager())

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)


class TestConfigManagerProviders:
    """Test LLM provider configurations."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ConfigManager._instance = None
        ConfigManager._initialized = False
        yield

    def test_llm_providers_defined(self):
        """LLM providers are defined."""
        config = ConfigManager()

        assert "glm" in config.LLM_PROVIDERS
        assert "chatgpt" in config.LLM_PROVIDERS
        assert "minimax" in config.LLM_PROVIDERS
        assert "perplexity" in config.LLM_PROVIDERS

    def test_llm_provider_has_required_fields(self):
        """Each LLM provider has required configuration fields."""
        config = ConfigManager()
        required_fields = ["name", "env_key", "base_url", "model"]

        for provider, provider_config in config.LLM_PROVIDERS.items():
            for field in required_fields:
                assert field in provider_config, f"{provider} missing {field}"

    def test_get_default_provider(self):
        """get_default_provider returns 'glm'."""
        config = ConfigManager()

        assert config.get_default_provider() == "glm"


class TestConfigManagerAPIKey:
    """Test API key management."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ConfigManager._instance = None
        ConfigManager._initialized = False
        yield

    def test_get_api_key_success(self):
        """get_api_key returns key when set."""
        config = ConfigManager()

        with patch.dict(os.environ, {"ZAI_API_KEY": "test-key"}):
            key = config.get_api_key("glm")

        assert key == "test-key"

    def test_get_api_key_invalid_provider(self):
        """get_api_key raises exception for invalid provider."""
        config = ConfigManager()

        with pytest.raises(ConfigurationException) as exc_info:
            config.get_api_key("invalid_provider")

        assert "Unknown LLM provider" in str(exc_info.value.message)

    def test_get_api_key_missing_key(self):
        """get_api_key raises exception when key not set."""
        config = ConfigManager()

        # Ensure the key is not set
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing key
            os.environ.pop("ZAI_API_KEY", None)
            with pytest.raises(ConfigurationException) as exc_info:
                config.get_api_key("glm")

        assert "API key not found" in str(exc_info.value.message)

    def test_set_api_key(self):
        """set_api_key sets environment variable."""
        config = ConfigManager()

        config.set_api_key("new-key", "glm")

        assert os.environ.get("ZAI_API_KEY") == "new-key"

    def test_set_api_key_invalid_provider(self):
        """set_api_key raises exception for invalid provider."""
        config = ConfigManager()

        with pytest.raises(ConfigurationException):
            config.set_api_key("key", "invalid")


class TestConfigManagerLLMConfig:
    """Test LLM configuration retrieval."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ConfigManager._instance = None
        ConfigManager._initialized = False
        yield

    def test_get_llm_config_success(self):
        """get_llm_config returns complete configuration."""
        config = ConfigManager()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key"}):
            llm_config = config.get_llm_config("chatgpt")

        assert llm_config["name"] == "OpenAI GPT-4o-mini"
        assert llm_config["api_key"] == "test-openai-key"
        assert "base_url" in llm_config
        assert "model" in llm_config

    def test_get_llm_config_invalid_provider(self):
        """get_llm_config raises exception for invalid provider."""
        config = ConfigManager()

        with pytest.raises(ConfigurationException):
            config.get_llm_config("nonexistent")


class TestConfigManagerPaths:
    """Test path management."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self, temp_dir, monkeypatch):
        """Reset singleton and change to temp directory."""
        ConfigManager._instance = None
        ConfigManager._initialized = False
        monkeypatch.chdir(temp_dir)
        yield

    def test_get_database_path(self):
        """get_database_path returns correct path."""
        config = ConfigManager()

        db_path = config.get_database_path()

        assert "data" in db_path
        assert "db" in db_path
        assert db_path.endswith("chat_history.db")

    def test_get_database_path_creates_directory(self, temp_dir):
        """get_database_path creates directory if needed."""
        config = ConfigManager()

        db_path = config.get_database_path()

        assert Path(db_path).parent.exists()

    def test_get_data_directory(self):
        """get_data_directory returns correct path."""
        config = ConfigManager()

        data_dir = config.get_data_directory()

        assert data_dir.name == "data"

    def test_get_upload_directory(self):
        """get_upload_directory returns correct path."""
        config = ConfigManager()

        upload_dir = config.get_upload_directory()

        assert upload_dir.name == "upload"

    def test_get_log_directory(self):
        """get_log_directory returns correct path."""
        config = ConfigManager()

        log_dir = config.get_log_directory()

        assert log_dir.name == "logs"


class TestConfigManagerGetSet:
    """Test generic get/set configuration."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ConfigManager._instance = None
        ConfigManager._initialized = False
        yield

    def test_set_and_get(self):
        """set stores value and get retrieves it."""
        config = ConfigManager()

        config.set("test_key", "test_value")

        assert config.get("test_key") == "test_value"

    def test_get_with_default(self):
        """get returns default for missing keys."""
        config = ConfigManager()

        value = config.get("nonexistent", "default_value")

        assert value == "default_value"

    def test_get_default_none(self):
        """get returns None for missing keys without default."""
        config = ConfigManager()

        value = config.get("nonexistent")

        assert value is None

    def test_set_overwrites(self):
        """set overwrites existing value."""
        config = ConfigManager()

        config.set("key", "value1")
        config.set("key", "value2")

        assert config.get("key") == "value2"

    def test_set_various_types(self):
        """set handles various value types."""
        config = ConfigManager()

        config.set("string", "text")
        config.set("int", 42)
        config.set("float", 3.14)
        config.set("bool", True)
        config.set("list", [1, 2, 3])
        config.set("dict", {"nested": "value"})

        assert config.get("string") == "text"
        assert config.get("int") == 42
        assert config.get("float") == 3.14
        assert config.get("bool") is True
        assert config.get("list") == [1, 2, 3]
        assert config.get("dict") == {"nested": "value"}
