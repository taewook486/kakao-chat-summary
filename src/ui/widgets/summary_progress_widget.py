"""상태바 내장 요약 프로그레스 위젯."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtCore import Signal, Slot


class SummaryProgressWidget(QWidget):
    """상태바 내장 요약 프로그레스 위젯 (비모달)."""
    cancel_requested = Signal()

    def __init__(self, parent=None, llm_name: str = "LLM", room_name: str = ""):
        super().__init__(parent)
        self.room_name = room_name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self.icon_label = QLabel("🤖")
        self.icon_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.icon_label)

        self.message_label = QLabel(f"[{room_name}] {llm_name} 요약 중...")
        self.message_label.setStyleSheet("font-size: 12px; color: #191919;")
        layout.addWidget(self.message_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setObjectName("summaryProgressBar")
        layout.addWidget(self.progress_bar)

        self.cancel_btn = QPushButton("❌")
        self.cancel_btn.setToolTip("요약 취소")
        self.cancel_btn.setFixedSize(24, 24)
        self.cancel_btn.setObjectName("summaryProgressCancelBtn")
        self.cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_btn)

        self.setObjectName("summaryProgressWidget")

    def _on_cancel(self):
        """취소 버튼 클릭."""
        self.cancel_btn.setEnabled(False)
        self.message_label.setText(f"[{self.room_name}] 취소 중...")
        self.cancel_requested.emit()

    @Slot(int, str)
    def update_progress(self, progress: int, message: str):
        """진행 상황 업데이트."""
        self.progress_bar.setValue(progress)
        self.message_label.setText(f"[{self.room_name}] {message}")

    def set_completed(self, success: bool, message: str):
        """완료 상태 표시."""
        self.progress_bar.setValue(100)
        self.cancel_btn.setVisible(False)
        icon = "✅" if success else "❌"
        self.icon_label.setText(icon)
        self.message_label.setText(message)
