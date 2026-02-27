"""Configuration manager for application settings."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock
from dotenv import load_dotenv

from ..exceptions import ConfigurationException


class ConfigManager:
    """
    Thread-safe singleton configuration manager.

    Manages application configuration including LLM provider settings,
    API keys, and other runtime configuration. Implements singleton
    pattern with thread-safe initialization.
    """

    _instance: Optional['ConfigManager'] = None
    _lock: Lock = Lock()
    _initialized: bool = False

    # LLM provider configurations (Updated 2026-02-27)
    LLM_PROVIDERS: Dict[str, Dict[str, Any]] = {
        "glm": {
            "name": "Zhipu GLM",
            "env_key": "ZAI_API_KEY",
            "base_url": "https://api.z.ai/api/coding/paas/v4/chat/completions",
            "model": "glm-5",  # Latest flagship (February 2026)
        },
        "chatgpt": {
            "name": "OpenAI GPT",
            "env_key": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4o",  # Stable production model
        },
        "minimax": {
            "name": "MiniMax",
            "env_key": "MINIMAX_API_KEY",
            "base_url": "https://api.minimax.chat/v1/text/chatcompletion_v2",
            "model": "MiniMax-M2.5",  # Latest flagship (2026)
        },
        "perplexity": {
            "name": "Perplexity",
            "env_key": "PERPLEXITY_API_KEY",
            "base_url": "https://api.perplexity.ai/chat/completions",
            "model": "sonar",  # Online search model
        },
    }

    def __new__(cls):
        """Ensure only one instance exists (thread-safe singleton)."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize configuration manager (only runs once)."""
        if not ConfigManager._initialized:
            with ConfigManager._lock:
                if not ConfigManager._initialized:
                    self._config: Dict[str, Any] = {}
                    self._load_env_file()
                    ConfigManager._initialized = True

    def _load_env_file(self) -> None:
        """Load environment variables from .env.local file."""
        # Try multiple possible locations
        env_files = [
            Path.cwd() / ".env.local",
            Path.cwd() / ".env",
            Path(__file__).parent.parent.parent / ".env.local",
        ]

        for env_file in env_files:
            if env_file.exists():
                load_dotenv(env_file)
                break

    def get_api_key(self, provider: str) -> str:
        """
        Get API key for specified LLM provider.

        Args:
            provider: LLM provider name (glm, chatgpt, minimax, perplexity).

        Returns:
            API key string.

        Raises:
            ConfigurationException: If provider is invalid or API key not found.
        """
        if provider not in self.LLM_PROVIDERS:
            raise ConfigurationException(
                message=f"Unknown LLM provider: {provider}",
                config_key="llm_provider",
            )

        provider_config = self.LLM_PROVIDERS[provider]
        env_key = provider_config["env_key"]
        api_key = os.getenv(env_key)

        if not api_key:
            raise ConfigurationException(
                message=f"API key not found for {provider_config['name']}",
                config_key=env_key,
            )

        return api_key

    def set_api_key(self, api_key: str, provider: str) -> None:
        """
        Set API key for specified LLM provider.

        Note: This only updates runtime configuration, not .env file.

        Args:
            api_key: API key string.
            provider: LLM provider name.

        Raises:
            ConfigurationException: If provider is invalid.
        """
        if provider not in self.LLM_PROVIDERS:
            raise ConfigurationException(
                message=f"Unknown LLM provider: {provider}",
                config_key="llm_provider",
            )

        provider_config = self.LLM_PROVIDERS[provider]
        env_key = provider_config["env_key"]
        os.environ[env_key] = api_key

    def get_llm_config(self, provider: str) -> Dict[str, str]:
        """
        Get complete configuration for LLM provider.

        Args:
            provider: LLM provider name.

        Returns:
            Dictionary with provider configuration including:
                - name: Provider display name
                - base_url: API endpoint URL
                - model: Model name
                - api_key: API key

        Raises:
            ConfigurationException: If provider is invalid or API key not found.
        """
        if provider not in self.LLM_PROVIDERS:
            raise ConfigurationException(
                message=f"Unknown LLM provider: {provider}",
                config_key="llm_provider",
            )

        provider_config = self.LLM_PROVIDERS[provider]
        api_key = self.get_api_key(provider)

        return {
            "name": provider_config["name"],
            "base_url": provider_config["base_url"],
            "model": provider_config["model"],
            "api_key": api_key,
        }

    def get_default_provider(self) -> str:
        """
        Get default LLM provider.

        Returns:
            Default provider name (currently 'glm').

        Note: In future, this could be made configurable.
        """
        return "glm"

    def get_database_path(self) -> str:
        """
        Get path to SQLite database file.

        Returns:
            Absolute path to chat_history.db.
        """
        db_dir = Path.cwd() / "data" / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "chat_history.db")

    def get_data_directory(self) -> Path:
        """
        Get path to data directory.

        Returns:
            Path to data directory.
        """
        data_dir = Path.cwd() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_upload_directory(self) -> Path:
        """
        Get path to upload directory.

        Returns:
            Path to upload directory.
        """
        upload_dir = Path.cwd() / "upload"
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    def get_log_directory(self) -> Path:
        """
        Get path to log directory.

        Returns:
            Path to logs directory.
        """
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key.
            value: Configuration value.
        """
        self._config[key] = value
