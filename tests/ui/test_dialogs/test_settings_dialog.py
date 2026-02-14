"""Tests for SettingsDialog."""
import pytest

from src.ui.dialogs.settings_dialog import SettingsDialog


class TestSettingsDialog:
    """Test SettingsDialog functionality."""

    def test_dialog_initialization(self, qapp):
        """Dialog initializes with correct default values."""
        dialog = SettingsDialog()

        assert dialog.sync_interval.value() == 30
        assert dialog.auto_summary.currentIndex() == 0
        assert dialog.llm_provider.currentIndex() == 0

    def test_sync_interval_range(self, qapp):
        """Sync interval has correct range."""
        dialog = SettingsDialog()

        assert dialog.sync_interval.minimum() == 5
        assert dialog.sync_interval.maximum() == 120

    def test_get_settings(self, qapp):
        """get_settings returns current settings."""
        dialog = SettingsDialog()
        dialog.sync_interval.setValue(60)
        dialog.auto_summary.setCurrentIndex(2)
        dialog.llm_provider.setCurrentIndex(1)

        settings = dialog.get_settings()

        assert settings['sync_interval'] == 60
        assert settings['auto_summary'] == 2
        assert settings['llm_provider'] == 1

    def test_set_settings(self, qapp):
        """set_settings updates dialog values."""
        dialog = SettingsDialog()

        dialog.set_settings({
            'sync_interval': 45,
            'auto_summary': 1,
            'llm_provider': 3
        })

        assert dialog.sync_interval.value() == 45
        assert dialog.auto_summary.currentIndex() == 1
        assert dialog.llm_provider.currentIndex() == 3

    def test_set_settings_partial(self, qapp):
        """set_settings handles partial settings dict."""
        dialog = SettingsDialog()
        dialog.sync_interval.setValue(50)

        dialog.set_settings({'sync_interval': 15})

        assert dialog.sync_interval.value() == 15
        # Other values should remain at defaults
        assert dialog.auto_summary.currentIndex() == 0

    def test_auto_summary_options(self, qapp):
        """Auto summary has correct options."""
        dialog = SettingsDialog()

        assert dialog.auto_summary.count() == 4
        assert dialog.auto_summary.itemText(0) == "Disabled"
        assert dialog.auto_summary.itemText(1) == "Daily"
        assert dialog.auto_summary.itemText(2) == "Every 2 days"
        assert dialog.auto_summary.itemText(3) == "Weekly"

    def test_llm_provider_options(self, qapp):
        """LLM provider has correct options."""
        dialog = SettingsDialog()

        assert dialog.llm_provider.count() == 4
        assert "GLM" in dialog.llm_provider.itemText(0)
        assert "OpenAI" in dialog.llm_provider.itemText(1)
