"""Create room dialog for creating new chat rooms."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox
)


class CreateRoomDialog(QDialog):
    """Dialog for creating a new chat room.

    Attributes:
        room_name: The name entered by the user (set after accept).
    """

    def __init__(self, parent=None):
        """Initialize the create room dialog.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Create Chat Room")
        self.setMinimumWidth(400)
        self.room_name = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Info message
        info_label = QLabel(
            "Create a new chat room.\n"
            "You can upload a KakaoTalk chat file later."
        )
        info_label.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(info_label)

        # Room name input
        name_group = QGroupBox("Room Name")
        name_layout = QVBoxLayout(name_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Development Team, Club Meeting...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                font-size: 14px;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
            }
            QLineEdit:focus {
                border-color: #FEE500;
            }
        """)
        name_layout.addWidget(self.name_input)
        layout.addWidget(name_group)

        # Buttons
        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #333333;
                padding: 10px 25px;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.create_btn = QPushButton("Create")
        self.create_btn.setEnabled(False)
        self.create_btn.clicked.connect(self._on_create)
        self.create_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 25px;
            }
        """)
        button_layout.addWidget(self.create_btn)

        layout.addLayout(button_layout)

        # Connect signals
        self.name_input.textChanged.connect(self._check_input)
        self.name_input.returnPressed.connect(self._on_create)
        self.create_btn.setDefault(True)

    def _check_input(self) -> None:
        """Check input and enable/disable create button."""
        has_name = bool(self.name_input.text().strip())
        self.create_btn.setEnabled(has_name)

    def _on_create(self) -> None:
        """Handle create button click."""
        name = self.name_input.text().strip()
        if not name:
            return
        self.room_name = name
        self.accept()

    def get_room_name(self) -> str:
        """Get the entered room name.

        Returns:
            The room name, or empty string if not accepted.
        """
        return self.room_name
