"""Motivation feature window."""

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from features.ui_components import GlowButton, make_page_header

class MotivationWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FitTrack AI — רגע של מוטיבציה")
        self.resize(500, 320)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #0B111E; border: 2px solid #06B6D4; border-radius: 12px;")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 30, 25, 25)
        layout.setSpacing(20)

        layout.addWidget(make_page_header(
            "מוטיבציה",
            "משפט קצר להמשך היום.",
        ))

        self.card = QFrame()
        self.card.setStyleSheet("background-color: #111827; border: 1px solid #1E293B; border-radius: 8px;")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(15, 15, 15, 15)

        self.lbl_quote = QLabel()
        self.lbl_quote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_quote.setWordWrap(True)
        self.lbl_quote.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC; font-style: italic; border: none; line-height: 24px;")
        card_layout.addWidget(self.lbl_quote)
        layout.addWidget(self.card)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_refresh = GlowButton("משפט נוסף", base_color="#0284C7", hover_color="#0369A1", glow_color="#38BDF8")
        self.btn_refresh.clicked.connect(self.generate_random_quote)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_close = GlowButton("סגור", base_color="#374151", hover_color="#4B5563", glow_color="#9CA3AF")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)
        self.quotes = [
            " 'ההבדל בין הבלתי אפשרי לאפשרי שוכן בנחישות של האדם.' — קריסטופר ריב",
            " 'אל תספרו את הימים, גרמו לימים נספרים.' — מוחמד עלי",
            " 'הכאב שאתה מרגיש היום, יהפוך לכוח שתרגיש מחר.'",
            " 'התעמלות היא לחגוג את מה שהגוף שלך מסוגל לעשות.'"
        ]
        self.generate_random_quote()

    def generate_random_quote(self) -> None:
        self.lbl_quote.setText(random.choice(self.quotes))
