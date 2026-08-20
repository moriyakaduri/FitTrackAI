"""AI advisor feature view and its background HTTP workers."""

import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QScrollArea,
    QVBoxLayout, QWidget,
)

from features.ui_components import GlowButton

API_BASE_URL = "http://127.0.0.1:8000"

class AIWorker(QThread):
    finished_signal = Signal(str)

    def __init__(self, user_message: str, username: str, api_base_url: str):
        super().__init__()
        self.user_message = user_message
        self.username = username
        self.api_base_url = api_base_url

    def run(self):
        try:
            response = requests.post(
                f"{self.api_base_url}/ai/analyze-food",
                json={"message": self.user_message, "username": self.username},
                timeout=1200
            )
            response.raise_for_status()
            ai_response = response.json().get("response", "לא התקבלה תשובה.")
        except requests.exceptions.Timeout:
            ai_response = "שגיאה: לשרת ה-AI לקח יותר מדי זמן לענות (Timeout)."
        except Exception as error:
            ai_response = f"שגיאה בקבלת תשובה משרת ה-AI: {error}"

        self.finished_signal.emit(ai_response)

class ChatVisionWorker(QThread):
    finished_signal = Signal(str)

    def __init__(self, file_path: str, api_base_url: str):
        super().__init__()
        self.file_path = file_path
        self.api_base_url = api_base_url

    def run(self):
        try:
            with open(self.file_path, "rb") as f:
                files = {"file": (self.file_path, f, "image/jpeg")}
                response = requests.post(f"{self.api_base_url}/ai/chat-image", files=files, timeout=1200)
            response.raise_for_status()
            ai_response = response.json().get("response", "לא התקבלה תשובה מהשרת.")
        except requests.exceptions.Timeout:
            ai_response = "שגיאה: לשרת ה-AI לקח יותר מדי זמן לענות (Timeout)."
        except Exception as e:
            ai_response = f"שגיאת התחברות לראייה הממוחשבת: {str(e)}"
        self.finished_signal.emit(ai_response)

class AIAgentView(QWidget):
    def __init__(self, app_controller) -> None:
        super().__init__()
        self.app_controller = app_controller
        self.api_base_url = API_BASE_URL

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #0A0F1D;")
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        back_button = GlowButton(" חזרה למרכז הבקרה", base_color="#1F2937", hover_color="#374151", glow_color="#9CA3AF")
        back_button.clicked.connect(self.app_controller.show_dashboard_view)
        back_button.setFixedWidth(200)
        main_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignRight)

        header = QLabel(" Ollama RAG Container — סוכן ייעוץ תזונה וכושר חכם")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 22px; font-weight: bold; color: #FFFFFF;
            background-color: #111827; padding: 15px;
            border: 2px solid #38BDF8; border-radius: 10px;
        """)
        main_layout.addWidget(header)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("""
            QScrollArea { border: 1px solid #1E293B; border-radius: 10px; background-color: #030712; }
            QScrollBar:vertical { width: 10px; background: #0B132B; }
            QScrollBar::handle:vertical { background: #38BDF8; border-radius: 5px; }
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(15)
        self.chat_scroll.setWidget(self.chat_container)

        main_layout.addWidget(self.chat_scroll)

        self.add_ai_bubble("שלום! מערכת ה-RAG עלתה בהצלחה. אני FitTrack AI. את יכולה לשאול אותי שאלות רגילות, או ללחוץ על '📷 תמונה' כדי שאזהה עבורך מנות וארוחות!")

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.btn_upload = GlowButton("📷 תמונה", base_color="#4F46E5", hover_color="#4338CA", glow_color="#818CF8")
        self.btn_upload.clicked.connect(self.upload_chat_image)
        input_layout.addWidget(self.btn_upload)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("הקלד/י שאלה ליועץ ה-AI כאן...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                padding: 15px; border: 1px solid #1E293B; border-radius: 10px;
                background-color: #111827; color: #FFFFFF; font-size: 15px; text-align: right;
            }
            QLineEdit:focus { border: 2px solid #06B6D4; }
        """)
        self.chat_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.chat_input)

        self.btn_send = GlowButton("שאל את הסוכן", base_color="#0284C7", hover_color="#0369A1", glow_color="#7DD3FC")
        self.btn_send.clicked.connect(self.send_message)
        input_layout.addWidget(self.btn_send)

        main_layout.addLayout(input_layout)

    def add_user_bubble(self, text: str):
        bubble_layout = QHBoxLayout()
        bubble_layout.setDirection(QHBoxLayout.Direction.RightToLeft)

        lbl = QLabel(f" את/ה:\n{text}")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("""
            background-color: #1E293B; color: #E2E8F0; font-size: 14px;
            padding: 12px; border-radius: 12px; border-bottom-right-radius: 0px;
            max-width: 500px;
        """)

        bubble_layout.addStretch()
        bubble_layout.addWidget(lbl)
        self.chat_layout.addLayout(bubble_layout)
        self._scroll_to_bottom()

    def add_ai_bubble(self, text: str):
        bubble_layout = QHBoxLayout()
        bubble_layout.setDirection(QHBoxLayout.Direction.RightToLeft)

        formatted_text = f"<div dir='rtl' style='text-align: right;'><b> FitTrack AI:</b><br>{text}</div>"

        lbl = QLabel(formatted_text)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        lbl.setOpenExternalLinks(True)
        lbl.setStyleSheet("""
            background-color: #064E3B; color: #D1FAE5; font-size: 14px;
            padding: 12px; border: 1px solid #10B981; border-radius: 12px; border-bottom-left-radius: 0px;
            max-width: 500px; line-height: 1.4;
        """)

        bubble_layout.addWidget(lbl)
        bubble_layout.addStretch()
        self.chat_layout.addLayout(bubble_layout)
        self._scroll_to_bottom()

    def send_message(self):
        user_text = self.chat_input.text().strip()
        if not user_text:
            return

        self.add_user_bubble(user_text)
        self.chat_input.clear()

        self.btn_send.setEnabled(False)
        self.btn_upload.setEnabled(False)
        self.btn_send.setText("הסוכן חושב...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        username = getattr(self.app_controller.presenter, 'active_user', 'Guest')
        self.worker = AIWorker(user_text, username, self.api_base_url)
        self.worker.finished_signal.connect(self.on_ai_response_received)
        self.worker.start()

    def upload_chat_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "בחר תמונת ארוחה", "", "Images (*.png *.jpg *.jpeg)")
        if not file_path:
            return

        file_name = file_path.split("/")[-1]
        self.add_user_bubble(f"📸 שלחתי תמונה לבדיקה: {file_name}")

        self.btn_send.setEnabled(False)
        self.btn_upload.setEnabled(False)
        self.btn_send.setText("מנתח תמונה...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self.chat_vision_worker = ChatVisionWorker(file_path, self.api_base_url)
        self.chat_vision_worker.finished_signal.connect(self.on_ai_response_received)
        self.chat_vision_worker.start()

    def on_ai_response_received(self, response_text: str):
        QApplication.restoreOverrideCursor()
        self.btn_send.setEnabled(True)
        self.btn_upload.setEnabled(True)
        self.btn_send.setText("שאל את הסוכן")
        self.add_ai_bubble(response_text)

    def _scroll_to_bottom(self):
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )
