"""대시보드 카드 위젯."""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


class DashboardCard(QFrame):
    """대시보드 카드 위젯."""

    def __init__(self, title: str, value: str, subtext: str = "", icon: str = "📊"):
        super().__init__()
        self.setProperty("class", "DashboardCard")
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 10px;
                padding: 8px 12px;
            }
            QFrame:hover {
                border-color: #FEE500;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        # 아이콘 + 제목 + 값을 한 줄로
        header = QHBoxLayout()
        header.setSpacing(6)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 14px;")
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 11px; color: #666666;")
        header.addWidget(title_label)
        header.addStretch()

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #3C1E1E;")
        header.addWidget(self.value_label)
        layout.addLayout(header)

        # 서브텍스트
        self.sub_label = QLabel(subtext)
        self.sub_label.setStyleSheet("font-size: 10px; color: #888888;")
        layout.addWidget(self.sub_label)

    def update_card(self, value: str, subtext: str = ""):
        """카드 값과 서브텍스트 업데이트."""
        self.value_label.setText(value)
        if subtext:
            self.sub_label.setText(subtext)
