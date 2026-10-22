"""Summary options dialog for configuring LLM summary generation."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QComboBox, QCheckBox,
    QRadioButton, QButtonGroup, QFrame, QMessageBox
)


class SummaryOptionsDialog(QDialog):
    """Dialog for configuring summary generation options.

    Attributes:
        summary_type: Type of summary ('pending', 'today', 'yesterday', '2days', 'all').
        skip_existing: Whether to skip already summarized dates.
        selected_llm: Selected LLM provider.
    """

    def __init__(
        self,
        parent=None,
        summarized_count: int = 0,
        total_count: int = 0,
        needs_update_count: int = 0,
        new_count: int = 0,
        current_llm: str = "glm"
    ):
        """Initialize the summary options dialog.

        Args:
            parent: Optional parent widget.
            summarized_count: Number of already summarized days.
            total_count: Total number of days.
            needs_update_count: Number of days needing update.
            new_count: Number of new days.
            current_llm: Currently selected LLM provider.
        """
        super().__init__(parent)
        self.setWindowTitle("LLM Summary Generation")
        self.setMinimumWidth(480)
        self.summary_type = "daily"
        self.skip_existing = True
        self.selected_llm = current_llm

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Status summary
        status_label = QLabel(
            f"Total: {total_count} days | "
            f"Complete: {summarized_count} | "
            f"New: {new_count} | "
            f"Needs Update: {needs_update_count}"
        )
        status_label.setStyleSheet("""
            font-size: 11px;
            color: #666;
            padding: 10px;
            background-color: #F8F8F8;
            border-radius: 6px;
        """)
        layout.addWidget(status_label)

        # LLM selection
        llm_group = QGroupBox("LLM Selection")
        llm_layout = QHBoxLayout(llm_group)

        self.llm_combo = QComboBox()
        self.llm_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                font-size: 13px;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
            }
            QComboBox:focus {
                border-color: #FEE500;
            }
        """)

        # LLM options
        llm_items = [
            ("glm", "Zhipu GLM-5 (Default)"),
            ("chatgpt", "OpenAI GPT-4o"),
            ("minimax", "MiniMax M2.5"),
            ("perplexity", "Perplexity Sonar"),
        ]

        current_idx = 0
        for idx, (key, label) in enumerate(llm_items):
            self.llm_combo.addItem(label, key)
            if key == current_llm:
                current_idx = idx

        self.llm_combo.setCurrentIndex(current_idx)
        llm_layout.addWidget(self.llm_combo, 1)

        # API key status
        self.api_status = QLabel()
        self.api_status.setStyleSheet("font-size: 11px;")
        self._update_api_status()
        llm_layout.addWidget(self.api_status)

        self.llm_combo.currentIndexChanged.connect(self._update_api_status)

        layout.addWidget(llm_group)

        # Summary type selection
        type_group = QGroupBox("Summary Range")
        type_layout = QVBoxLayout(type_group)

        self.type_button_group = QButtonGroup(self)

        pending_total = new_count + needs_update_count
        self.radio_pending = QRadioButton(
            f"Only pending dates ({pending_total} days: "
            f"new {new_count} + update {needs_update_count})"
        )
        self.radio_pending.setChecked(True)
        self.radio_pending.setStyleSheet("font-weight: bold; color: #1976D2;")

        self.radio_today = QRadioButton("Today only")
        self.radio_yesterday = QRadioButton("Yesterday to Today")
        self.radio_2days = QRadioButton("Last 3 days")
        self.radio_all = QRadioButton(f"All dates ({total_count} days)")

        self.type_button_group.addButton(self.radio_pending, 0)
        self.type_button_group.addButton(self.radio_today, 1)
        self.type_button_group.addButton(self.radio_yesterday, 2)
        self.type_button_group.addButton(self.radio_2days, 3)
        self.type_button_group.addButton(self.radio_all, 4)

        type_layout.addWidget(self.radio_pending)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #E0E0E0;")
        type_layout.addWidget(separator)

        type_layout.addWidget(self.radio_today)
        type_layout.addWidget(self.radio_yesterday)
        type_layout.addWidget(self.radio_2days)
        type_layout.addWidget(self.radio_all)

        layout.addWidget(type_group)

        # Options
        option_group = QGroupBox("Options")
        option_layout = QVBoxLayout(option_group)

        self.skip_checkbox = QCheckBox("Skip already summarized dates")
        self.skip_checkbox.setChecked(True)
        self.skip_checkbox.setStyleSheet("font-size: 12px;")
        self.skip_checkbox.setToolTip(
            "Automatically applied when 'Only pending dates' is selected."
        )
        option_layout.addWidget(self.skip_checkbox)

        # Option interaction
        self.radio_pending.toggled.connect(
            lambda checked: self.skip_checkbox.setEnabled(not checked)
        )

        layout.addWidget(option_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        generate_btn = QPushButton("Generate Summary")
        generate_btn.clicked.connect(self._on_generate)
        button_layout.addWidget(generate_btn)

        layout.addLayout(button_layout)

    def _update_api_status(self) -> None:
        """Update API key status display."""
        from full_config import config

        llm_key = self.llm_combo.currentData()
        api_key = config.get_api_key(llm_key)

        if api_key:
            self.api_status.setText("API Key Set")
            self.api_status.setStyleSheet("font-size: 11px; color: #4CAF50;")
        else:
            self.api_status.setText("API Key Required")
            self.api_status.setStyleSheet("font-size: 11px; color: #FF9800;")

    def _on_generate(self) -> None:
        """Handle generate button click."""
        from full_config import config

        # Get LLM selection
        self.selected_llm = self.llm_combo.currentData()

        # Check API key
        if not config.get_api_key(self.selected_llm):
            QMessageBox.warning(
                self,
                "API Key Required",
                f"The selected LLM ({self.llm_combo.currentText()}) "
                f"requires an API key.\n\n"
                f"Please set the environment variable or add to .env file."
            )
            return

        # Get summary type
        selected = self.type_button_group.checkedId()
        type_mapping = {
            0: ("pending", True),
            1: ("today", self.skip_checkbox.isChecked()),
            2: ("yesterday", self.skip_checkbox.isChecked()),
            3: ("2days", self.skip_checkbox.isChecked()),
            4: ("all", self.skip_checkbox.isChecked()),
        }

        self.summary_type, self.skip_existing = type_mapping.get(selected, ("pending", True))

        self.accept()

    def get_options(self) -> dict:
        """Get the selected options.

        Returns:
            Dict with 'summary_type', 'skip_existing', 'selected_llm'.
        """
        return {
            'summary_type': self.summary_type,
            'skip_existing': self.skip_existing,
            'selected_llm': self.selected_llm,
        }
