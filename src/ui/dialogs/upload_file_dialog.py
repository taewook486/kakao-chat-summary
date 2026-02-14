"""Upload file dialog for selecting chat files."""
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFileDialog
)


class UploadFileDialog(QDialog):
    """Dialog for uploading chat files.

    Attributes:
        room_name: The chat room name.
        file_path: The selected file path (set after file selection).
    """

    def __init__(self, room_name: str, parent=None):
        """Initialize the upload file dialog.

        Args:
            room_name: Name of the chat room.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Upload File")
        self.setMinimumWidth(450)
        self.room_name = room_name
        self.file_path = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Room info
        room_label = QLabel(f"Chat Room: <b>{room_name}</b>")
        room_label.setStyleSheet(
            "font-size: 14px; padding: 10px; "
            "background-color: #FEE500; border-radius: 8px;"
        )
        layout.addWidget(room_label)

        # File selection
        file_group = QGroupBox("KakaoTalk Chat File")
        file_layout = QVBoxLayout(file_group)

        file_row = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #888888;")
        file_row.addWidget(self.file_label, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_file)
        browse_btn.setStyleSheet("padding: 8px 15px;")
        file_row.addWidget(browse_btn)
        file_layout.addLayout(file_row)

        hint_label = QLabel(
            "Select a .txt file exported from KakaoTalk's 'Export Chat' feature.\n"
            "Multiple uploads will merge with existing data."
        )
        hint_label.setStyleSheet("color: #888888; font-size: 11px;")
        hint_label.setWordWrap(True)
        file_layout.addWidget(hint_label)

        layout.addWidget(file_group)

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

        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self.accept)
        self.upload_btn.setStyleSheet("padding: 10px 25px;")
        button_layout.addWidget(self.upload_btn)

        layout.addLayout(button_layout)

    def _browse_file(self) -> None:
        """Open file browser to select a chat file."""
        # Default directory: upload/
        upload_dir = Path(__file__).parent.parent.parent.parent / "upload"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select KakaoTalk Chat File",
            str(upload_dir),
            "Text Files (*.txt)"
        )

        if file_path:
            self.file_path = file_path
            filename = Path(file_path).name
            self.file_label.setText(f"Selected: {filename}")
            self.file_label.setStyleSheet("color: #333333;")
            self.upload_btn.setEnabled(True)

    def get_file_path(self) -> str:
        """Get the selected file path.

        Returns:
            The file path, or empty string if not selected.
        """
        return self.file_path
