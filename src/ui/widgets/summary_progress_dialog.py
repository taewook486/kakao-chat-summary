"""요약 진행 상황 다이얼로그."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
)
from PySide6.QtCore import Qt, Signal, Slot


class SummaryProgressDialog(QDialog):
    """요약 진행 상황 다이얼로그."""
    cancel_requested = Signal()

    def __init__(self, parent=None, llm_name: str = "LLM", total_dates: int = 0):
        super().__init__(parent)
        self.setWindowTitle("🤖 요약 생성 중...")
        self.setMinimumWidth(500)
        self.setMinimumHeight(200)
        self.setModal(True)
        self._is_cancelled = False

        # 닫기 버튼 비활성화
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 헤더
        header = QLabel(f"🤖 {llm_name}으로 요약 생성 중...")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1976D2;")
        layout.addWidget(header)

        # 현재 처리 중인 날짜
        self.current_label = QLabel("준비 중...")
        self.current_label.setStyleSheet("""
            font-size: 14px;
            padding: 10px;
            background-color: #FFF8E1;
            border-radius: 6px;
            border: 1px solid #FFE082;
        """)
        layout.addWidget(self.current_label)

        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                text-align: center;
                font-size: 12px;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #FEE500;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 상세 정보
        self.detail_label = QLabel(f"📅 총 {total_dates}일 처리 예정")
        self.detail_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self.detail_label)

        # 취소 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("❌ 취소")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                padding: 10px 30px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _on_cancel(self):
        """취소 버튼 클릭."""
        self._is_cancelled = True
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("취소 중...")
        self.current_label.setText("⏳ 현재 작업 완료 후 취소됩니다...")
        self.cancel_requested.emit()

    def is_cancelled(self) -> bool:
        """취소 여부 확인."""
        return self._is_cancelled

    @Slot(int, str)
    def update_progress(self, progress: int, message: str):
        """진행 상황 업데이트."""
        self.progress_bar.setValue(progress)
        self.current_label.setText(f"📅 {message}")

    def set_detail(self, text: str):
        """상세 정보 업데이트."""
        self.detail_label.setText(text)

    def complete(self, success: bool):
        """완료 처리."""
        if success:
            self.current_label.setText("✅ 완료!")
            self.current_label.setStyleSheet("""
                font-size: 14px;
                padding: 10px;
                background-color: #E8F5E9;
                border-radius: 6px;
                border: 1px solid #A5D6A7;
            """)
        else:
            self.current_label.setText("❌ 실패")
            self.current_label.setStyleSheet("""
                font-size: 14px;
                padding: 10px;
                background-color: #FFEBEE;
                border-radius: 6px;
                border: 1px solid #EF9A9A;
            """)

        self.cancel_btn.setText("닫기")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 30px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)
