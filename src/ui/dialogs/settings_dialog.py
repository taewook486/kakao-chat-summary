"""Settings dialog for application configuration."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout,
    QSpinBox, QComboBox, QDialogButtonBox
)


class SettingsDialog(QDialog):
    """Dialog for application settings.

    Attributes:
        sync_interval: Sync interval in minutes.
        auto_summary: Auto summary frequency setting.
        llm_provider: Selected LLM provider.
    """

    def __init__(self, parent=None):
        """Initialize the settings dialog.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Sync settings
        sync_group = QGroupBox("Auto Sync")
        sync_layout = QFormLayout(sync_group)

        self.sync_interval = QSpinBox()
        self.sync_interval.setRange(5, 120)
        self.sync_interval.setValue(30)
        self.sync_interval.setSuffix(" min")
        sync_layout.addRow("Sync Interval:", self.sync_interval)

        self.auto_summary = QComboBox()
        self.auto_summary.addItems([
            "Disabled",
            "Daily",
            "Every 2 days",
            "Weekly"
        ])
        sync_layout.addRow("Auto Summary:", self.auto_summary)

        layout.addWidget(sync_group)

        # LLM settings
        llm_group = QGroupBox("LLM Settings")
        llm_layout = QFormLayout(llm_group)

        self.llm_provider = QComboBox()
        self.llm_provider.addItems([
            "Z.AI GLM",
            "OpenAI GPT",
            "Anthropic Claude",
            "Google Gemini"
        ])
        llm_layout.addRow("LLM Provider:", self.llm_provider)

        layout.addWidget(llm_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self) -> dict:
        """Get the current settings.

        Returns:
            Dict with 'sync_interval', 'auto_summary', 'llm_provider'.
        """
        return {
            'sync_interval': self.sync_interval.value(),
            'auto_summary': self.auto_summary.currentIndex(),
            'llm_provider': self.llm_provider.currentIndex(),
        }

    def set_settings(self, settings: dict) -> None:
        """Set the current settings.

        Args:
            settings: Dict with 'sync_interval', 'auto_summary', 'llm_provider'.
        """
        if 'sync_interval' in settings:
            self.sync_interval.setValue(settings['sync_interval'])
        if 'auto_summary' in settings:
            self.auto_summary.setCurrentIndex(settings['auto_summary'])
        if 'llm_provider' in settings:
            self.llm_provider.setCurrentIndex(settings['llm_provider'])
