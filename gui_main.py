import sys
import random
import os
from datetime import date
import requests
from PySide6.QtCharts import QChart, QChartView, QPieSeries, QLineSeries, QValueAxis
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QThread, Signal, QUrl, QPointF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QDesktopServices, QBrush
from PySide6.QtWidgets import (
    QApplication, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QFrame, QFileDialog, QScrollArea, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)

# --- ספריות המולטימדיה להפעלת וידאו מציאותי וחשמלי ברקע ---
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
from PySide6.QtMultimediaWidgets import QVideoWidget

from presenter import FitTrackPresenter, SaveMealWorker

API_BASE_URL = "http://127.0.0.1:8000"

# =====================================================================
# רכיבי UI אינטראקטיביים חכמים 
# =====================================================================

class GlowButton(QPushButton):
    """ כפתור שזוהר במעבר עכבר """
    def __init__(self, text, base_color="#0284C7", hover_color="#0EA5E9", glow_color="#38BDF8", align="center", border_color="transparent"):
        super().__init__(text)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base_color};
                color: #FFFFFF;
                font-weight: bold;
                padding: 14px;
                border: 1px solid {border_color};
                border-radius: 10px;
                font-size: 15px;
                text-align: {align};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid {glow_color};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class HoverCard(QFrame):
    """ כרטיסייה שמאירה במעבר עכבר """
    def __init__(self, bg_color="#0B132B"):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid #1E293B;
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 1px solid #38BDF8;
            }}
        """)

# =====================================================================

def apply_neon_shadow(widget: QWidget, color_hex: str = "#000000", blur: int = 15, y_offset: int = 4):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(color_hex))
    widget.setGraphicsEffect(shadow)

def play_fade_in_animation(widget: QWidget, duration: int = 500):
    opacity_effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(opacity_effect)
    anim = QPropertyAnimation(opacity_effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    widget.fade_anim = anim
    anim.start()

def play_card_fly_animation(widget: QWidget, duration: int = 600):
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    current_pos = widget.pos()
    anim.setStartValue(QPoint(widget.x(), widget.y() + 80))
    anim.setEndValue(current_pos)
    anim.setEasingCurve(QEasingCurve.Type.OutBack)
    widget.fly_anim = anim
    anim.start()

def show_styled_msgbox(parent, title: str, text: str, icon: QMessageBox.Icon):
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(icon)
    msg_box.setStyleSheet("""
        QMessageBox { background-color: #FFFFFF; }
        QLabel { color: #000000; font-size: 14px; font-weight: 500; background-color: transparent; }
        QPushButton { background-color: #38BDF8; color: #000000; padding: 6px 16px; border-radius: 4px; font-weight: bold; border: none; }
        QPushButton:hover { background-color: #0EA5E9; }
    """)
    msg_box.exec()

# --- Workers לניהול תקשורת ברקע ---
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

class VisionWorker(QThread):
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, file_path: str, api_base_url: str):
        super().__init__()
        self.file_path = file_path
        self.api_base_url = api_base_url

    def run(self):
        try:
            with open(self.file_path, "rb") as f:
                files = {"file": (self.file_path, f, "image/jpeg")}
                response = requests.post(f"{self.api_base_url}/ai/analyze-image", files=files, timeout=1200)
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                self.finished_signal.emit(data)
            else:
                self.error_signal.emit(data.get("message", "שגיאת שרת לא ידועה"))
        except requests.exceptions.Timeout:
            self.error_signal.emit("הבקשה לשרת נקטעה בגלל שלקחה יותר מדי זמן (Timeout). אנא נסי שוב.")
        except Exception as e:
            self.error_signal.emit(f"שגיאת התחברות: {str(e)}")

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

class MealDetailsDialog(QMessageBox):
    @staticmethod
    def show_meal(parent, meal_data: dict) -> None:
        dialog = QMessageBox(parent)
        dialog.setWindowTitle("פרטי נתונים — FitTrack")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setStyleSheet("""
            QMessageBox { background-color: #FFFFFF; }
            QLabel { color: #000000; font-size: 14px; font-weight: 500; background-color: transparent; }
            QPushButton { background-color: #38BDF8; color: #000000; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #0EA5E9; }
        """)
        
        meal_name = meal_data.get('meal_name') or meal_data.get('name', 'לא ידוע')
        dialog.setText(
            f"שם: {meal_name}\n"
            f"קלוריות: {meal_data.get('calories', 0)} קק\"ל\n"
            f"חלבון: {meal_data.get('protein_g', meal_data.get('protein', 0))} גרם\n"
            f"תאריך/מקור: {meal_data.get('event_date', meal_data.get('source', 'לא ידוע'))}\n"
        )
        dialog.exec()

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
        
        header = QLabel(" השראת ספורט וכושר יומית")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #38BDF8; border: none;")
        layout.addWidget(header)
        
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
        
        self.btn_refresh = GlowButton(" הגרל משפט נוסף", base_color="#0284C7", hover_color="#0369A1", glow_color="#38BDF8")
        self.btn_refresh.clicked.connect(self.generate_random_quote)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_close = GlowButton("סגור חלונית", base_color="#374151", hover_color="#4B5563", glow_color="#9CA3AF")
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

class DataEntryWindow(QWidget):
    def __init__(self, dashboard_view: "DashboardView") -> None:
        super().__init__()
        self.dashboard_view = dashboard_view
        self.setWindowTitle("FitTrack AI — מרכז הזנת נתונים מרוכז")
        self.resize(550, 750)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #0A0F1D; border: 2px solid #06B6D4; border-radius: 12px;")
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        
        self._build_ui()
        self.scroll.setWidget(self.content_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scroll)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        header = QLabel(" מרכז ניהול והזנת נתונים")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #06B6D4; border: none; padding-bottom: 5px;")
        layout.addWidget(header)

        input_style = """
            QLineEdit {
                padding: 12px; border: 1px solid #1E293B; 
                border-radius: 8px; background-color: #111827; color: #FFFFFF;
                font-size: 14px; text-align: right;
            }
            QLineEdit:focus { border: 2px solid #06B6D4; background-color: #090D16; }
        """
        label_style = "color: #FFFFFF; font-weight: bold; font-size: 14px; text-align: right; border: none;"

        search_group = QGroupBox("חיפוש נתונים במאגר (לפי שם או מאמר)")
        search_group.setStyleSheet("QGroupBox { font-weight: bold; color: #A855F7; border: 1px solid #1E293B; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        search_layout = QVBoxLayout(search_group)
        
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("הזן שם מאכל (לדוג' 'ביצה') או נושא...")
        self.search_input.setStyleSheet(input_style)
        
        self.btn_search = GlowButton("חפש", base_color="#7E22CE", hover_color="#9333EA", glow_color="#D8B4FE")
        self.btn_search.clicked.connect(self.trigger_search)
        
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.btn_search)
        search_layout.addLayout(search_row)
        layout.addWidget(search_group)

        nutrition_group = QGroupBox("הוספת מאכל או ארוחה חדשה")
        nutrition_group.setStyleSheet("QGroupBox { font-weight: bold; color: #10B981; border: 1px solid #1E293B; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        nut_layout = QVBoxLayout(nutrition_group)
        nut_layout.setSpacing(10)

        self.btn_camera_ai = GlowButton(" העלה תמונה לניתוח AI", base_color="#0F172A", hover_color="#1E293B", glow_color="#38BDF8", border_color="#06B6D4")
        self.btn_camera_ai.clicked.connect(self.simulate_camera_ai_analysis)
        nut_layout.addWidget(self.btn_camera_ai)
        
        self.btn_open_calculator = GlowButton(" פתח מחשבון קלוריות מתקדם (Ziv Zafrani)", base_color="#F59E0B", hover_color="#D97706", glow_color="#FDE68A")
        self.btn_open_calculator.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://zivzafrani.co.il/calorie-calculator/")))
        nut_layout.addWidget(self.btn_open_calculator)

        nut_layout.addWidget(QLabel("שם המאכל / ארוחה:", styleSheet=label_style))
        self.meal_name_input = QLineEdit()
        self.meal_name_input.setPlaceholderText("הזן שם מאכל (לדוגמה: חזה עוף ואורז)...")
        self.meal_name_input.setStyleSheet(input_style)
        nut_layout.addWidget(self.meal_name_input)

        row_macros = QHBoxLayout()
        v_cal = QVBoxLayout()
        v_cal.addWidget(QLabel("קלוריות (קק\"ל):", styleSheet=label_style))
        self.meal_calories_input = QLineEdit()
        self.meal_calories_input.setPlaceholderText("0")
        self.meal_calories_input.setStyleSheet(input_style)
        v_cal.addWidget(self.meal_calories_input)
        row_macros.addLayout(v_cal)

        v_pro = QVBoxLayout()
        v_pro.addWidget(QLabel("חלבון (גרם):", styleSheet=label_style))
        self.meal_protein_input = QLineEdit()
        self.meal_protein_input.setPlaceholderText("0")
        self.meal_protein_input.setStyleSheet(input_style)
        v_pro.addWidget(self.meal_protein_input)
        row_macros.addLayout(v_pro)
        nut_layout.addLayout(row_macros)

        self.btn_save_meal = GlowButton(" שמור ליומן (Save to Diary)", base_color="#059669", hover_color="#10B981", glow_color="#6EE7B7")
        self.btn_save_meal.clicked.connect(self.trigger_meal_save)
        nut_layout.addWidget(self.btn_save_meal)

        layout.addWidget(nutrition_group)

        weight_group = QGroupBox("עדכון מדדי משקל גוף")
        weight_group.setStyleSheet("QGroupBox { font-weight: bold; color: #38BDF8; border: 1px solid #1E293B; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        w_layout = QVBoxLayout(weight_group)
        w_layout.setSpacing(10)

        w_layout.addWidget(QLabel("משקל נוכחי (ק\"ג):", styleSheet=label_style))
        self.weight_value_input = QLineEdit()
        self.weight_value_input.setPlaceholderText("הזן משקל...")
        self.weight_value_input.setStyleSheet(input_style)
        w_layout.addWidget(self.weight_value_input)

        w_layout.addWidget(QLabel("תאריך רישום:", styleSheet=label_style))
        self.weight_date_input = QLineEdit()
        self.weight_date_input.setText(date.today().isoformat())
        self.weight_date_input.setStyleSheet(input_style)
        w_layout.addWidget(self.weight_date_input)

        self.btn_save_weight = GlowButton(" עדכן מדד משקל", base_color="#2563EB", hover_color="#3B82F6", glow_color="#93C5FD")
        self.btn_save_weight.clicked.connect(self.trigger_weight_save)
        w_layout.addWidget(self.btn_save_weight)

        layout.addWidget(weight_group)

        self.btn_close = GlowButton("סגור חלון הזנה", base_color="#374151", hover_color="#4B5563", glow_color="#D1D5DB")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def trigger_search(self) -> None:
        query = self.search_input.text().strip()
        if len(query) < 2:
            show_styled_msgbox(self, "שגיאה", "אנא הזן לפחות 2 תווים לחיפוש.", QMessageBox.Icon.Warning)
            return
            
        self.btn_search.setText("מחפש...")
        self.btn_search.setEnabled(False)
        QApplication.processEvents()
        
        result = self.dashboard_view.presenter.search_data(query)
        
        self.btn_search.setText("חפש")
        self.btn_search.setEnabled(True)
        
        if result:
            if result.get("type") == "food":
                text = f"שם המאכל: {result['name']}\nקלוריות: {result['calories']} קק\"ל\nחלבון: {result['protein']} גרם"
                show_styled_msgbox(self, "תוצאת חיפוש - ערכים תזונתיים", text, QMessageBox.Icon.Information)
                self.meal_name_input.setText(result['name'])
                self.meal_calories_input.setText(str(result['calories']))
                self.meal_protein_input.setText(str(result['protein']))
            elif result.get("type") == "article":
                text = f"כותרת: {result['title']}\nקטגוריה: {result['category']}\n\nתקציר:\n{result['summary']}"
                show_styled_msgbox(self, "תוצאת חיפוש - מאמר", text, QMessageBox.Icon.Information)
        else:
            show_styled_msgbox(self, "חיפוש נכשל", "לא נמצאו תוצאות במאגר המקומי.", QMessageBox.Icon.Warning)

    def simulate_camera_ai_analysis(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "בחר תמונת ארוחה לניתוח", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return

        self.btn_camera_ai.setText("מנתח תמונה... ⏳")
        self.btn_camera_ai.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        api_url = getattr(
            self.dashboard_view.app_controller.ai_view, "api_base_url", API_BASE_URL
        )
        self.vision_worker = VisionWorker(file_path, api_url)
        self.vision_worker.finished_signal.connect(self.on_vision_success)
        self.vision_worker.error_signal.connect(self.on_vision_error)
        self.vision_worker.start()

    def on_vision_success(self, data: dict) -> None:
        QApplication.restoreOverrideCursor()
        self.btn_camera_ai.setText(" העלה תמונה לניתוח AI")
        self.btn_camera_ai.setEnabled(True)

        self.meal_name_input.setText(str(data.get("name", "לא זוהה")))
        self.meal_calories_input.setText(str(data.get("calories", "0")))
        self.meal_protein_input.setText(str(data.get("protein", "0")))

        show_styled_msgbox(
            self,
            "זיהוי הושלם",
            "הזיהוי הושלם. אלו הערכות בלבד — אנא ערכ/י ואמת/י לפני השמירה.",
            QMessageBox.Icon.Information
        )

    def on_vision_error(self, error_message: str) -> None:
        QApplication.restoreOverrideCursor()
        self.btn_camera_ai.setText(" העלה תמונה לניתוח AI")
        self.btn_camera_ai.setEnabled(True)
        show_styled_msgbox(
            self,
            "שגיאת זיהוי",
            f"ה-AI לא הצליח לנתח את התמונה:\n{error_message}",
            QMessageBox.Icon.Warning
        )

    def trigger_meal_save(self) -> None:
        meal_name = self.meal_name_input.text().strip()
        calories_text = self.meal_calories_input.text().strip() or "0"
        protein_text = self.meal_protein_input.text().strip() or "0"

        if not meal_name:
            show_styled_msgbox(self, "שגיאה", "שם המאכל הוא שדה חובה.", QMessageBox.Icon.Warning)
            return

        try:
            calories = int(calories_text)
            protein_g = int(protein_text)
        except ValueError:
            show_styled_msgbox(self, "שגיאה", "קלוריות וחלבון חייבים להיות מספרים שלמים.", QMessageBox.Icon.Warning)
            return

        presenter = self.dashboard_view.presenter
        if not presenter.active_user:
            show_styled_msgbox(self, "שגיאה", "אין משתמש מחובר.", QMessageBox.Icon.Warning)
            return

        self.btn_save_meal.setEnabled(False)
        self.btn_save_meal.setText("שומר... ⏳")

        self.save_meal_worker = SaveMealWorker(
            presenter.active_user, meal_name, calories, protein_g
        )
        self.save_meal_worker.success_signal.connect(self.on_meal_save_success)
        self.save_meal_worker.error_signal.connect(self.on_meal_save_error)
        self.save_meal_worker.start()

    def on_meal_save_success(self) -> None:
        self.btn_save_meal.setEnabled(True)
        self.btn_save_meal.setText(" שמור ליומן (Save to Diary)")
        self.meal_name_input.clear()
        self.meal_calories_input.clear()
        self.meal_protein_input.clear()
        self.dashboard_view.refresh_data()
        show_styled_msgbox(self, "הצלחה", "הארוחה נשמרה ב-Event Store.", QMessageBox.Icon.Information)

    def on_meal_save_error(self, error_message: str) -> None:
        self.btn_save_meal.setEnabled(True)
        self.btn_save_meal.setText(" שמור ליומן (Save to Diary)")
        show_styled_msgbox(self, "שגיאה", f"שמירת הארוחה נכשלה:\n{error_message}", QMessageBox.Icon.Critical)

    def trigger_weight_save(self) -> None:
        weight_text = self.weight_value_input.text().strip()
        weight_date = self.weight_date_input.text().strip()

        if not weight_text or not weight_date:
            show_styled_msgbox(self, "שגיאה", "יש למלא משקל ותאריך.", QMessageBox.Icon.Warning)
            return

        try:
            weight = float(weight_text)
        except ValueError:
            show_styled_msgbox(self, "שגיאה", "משקל חייב להיות מספר.", QMessageBox.Icon.Warning)
            return

        success = self.dashboard_view.execute_remote_weight_save(weight, weight_date)
        if success:
            self.weight_value_input.clear()
            self.weight_date_input.setText(date.today().isoformat())


class TrendsAndWorkoutsWindow(QWidget):
    def __init__(self, dashboard_view: "DashboardView") -> None:
        super().__init__()
        self.dashboard_view = dashboard_view
        self.setWindowTitle("FitTrack AI — מגמות ואנליטיקת אימונים מורחבת")
        self.resize(600, 650)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #0A0F1D; border: 2px solid #06B6D4; border-radius: 12px;")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(16)

        header = QLabel(" מגמות, אנליטיקה ויומן אימונים")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #06B6D4; border: none; padding-bottom: 5px;")
        layout.addWidget(header)

        self.trends_box = QGroupBox("מצב תזונתי וניתוח מגמות משקל חכם")
        self.trends_box.setStyleSheet("QGroupBox { font-weight: bold; color: #38BDF8; border: 1px solid #1E293B; border-radius: 8px; padding-top: 15px; }")
        tb_layout = QVBoxLayout(self.trends_box)
        
        self.lbl_analysis_text = QLabel("טוען מדדי מגמות ומשקל מסונכרנים מהשרת...")
        self.lbl_analysis_text.setWordWrap(True)
        self.lbl_analysis_text.setStyleSheet("font-size: 14px; color: #FFFFFF; line-height: 22px; border: none; background: transparent; padding: 5px;")
        tb_layout.addWidget(self.lbl_analysis_text)
        layout.addWidget(self.trends_box)

        workout_group = QGroupBox("רישום והזנת אימון גופני חדש")
        workout_group.setStyleSheet("QGroupBox { font-weight: bold; color: #F43F5E; border: 1px solid #1E293B; border-radius: 8px; padding-top: 15px; }")
        w_layout = QVBoxLayout(workout_group)
        w_layout.setSpacing(10)

        input_style = "QLineEdit { padding: 11px; border: 1px solid #1E293B; border-radius: 8px; background-color: #111827; color: #FFFFFF; font-size: 14px; text-align: right; }"
        label_style = "color: #FFFFFF; font-weight: bold; font-size: 13px; text-align: right; border: none;"

        w_layout.addWidget(QLabel("סוג הפעילות / אימון:", styleSheet=label_style))
        self.workout_type_input = QLineEdit()
        self.workout_type_input.setPlaceholderText("לדוגמה: ריצה, שחייה, אימון כוח...")
        self.workout_type_input.setStyleSheet(input_style)
        w_layout.addWidget(self.workout_type_input)

        w_layout.addWidget(QLabel("משך הפעילות (בדקות):", styleSheet=label_style))
        self.workout_duration_input = QLineEdit()
        self.workout_duration_input.setPlaceholderText("לדוגמה: 45")
        self.workout_duration_input.setStyleSheet(input_style)
        w_layout.addWidget(self.workout_duration_input)

        self.btn_save_workout = GlowButton(" שמור אימון וסנכרן שריפת קלוריות", base_color="#E11D48", hover_color="#F43F5E", glow_color="#FDA4AF")
        self.btn_save_workout.clicked.connect(self.trigger_workout_save)
        w_layout.addWidget(self.btn_save_workout)
        layout.addWidget(workout_group)

        self.btn_close = GlowButton("סגור חלון מדדים", base_color="#374151", hover_color="#4B5563", glow_color="#D1D5DB")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def trigger_workout_save(self) -> None:
        w_type = self.workout_type_input.text().strip()
        duration_text = self.workout_duration_input.text().strip()

        if not w_type or not duration_text:
            show_styled_msgbox(self, "שגיאה", "יש למלא את סוג האימון ומשך הזמן.", QMessageBox.Icon.Warning)
            return

        duration = int(duration_text) if duration_text.isdigit() else 0
        if duration <= 0:
            show_styled_msgbox(self, "שגיאה", "משך האימון חייב להיות מספר דקות חיובי.", QMessageBox.Icon.Warning)
            return

        success = self.dashboard_view.execute_remote_workout_save(w_type, duration)
        if success:
            self.workout_type_input.clear()
            self.workout_duration_input.clear()

    def update_trends_text(self, text: str) -> None:
        self.lbl_analysis_text.setText(text)

# =====================================================================
# מסך התחברות עם וידאו רקע
# =====================================================================
class LoginView(QWidget):
    def __init__(self, app_controller: "FitTrackApplication", presenter: FitTrackPresenter) -> None:
        super().__init__()
        self.app_controller = app_controller
        self.presenter = presenter
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.video_widget = QVideoWidget(self)
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.0) 
        self.media_player.setAudioOutput(self.audio_output)
        
        self.video_sink = QVideoSink(self)
        self.media_player.setVideoOutput(self.video_sink)
        self.video_sink.videoFrameChanged.connect(self.on_frame_changed)
        self.current_frame = None

        current_dir = os.path.dirname(os.path.abspath(__file__))
        video_path = os.path.join(current_dir, "runner.mp4")
        if not os.path.exists(video_path):
            video_path = r"C:\Users\05879\Downloads\runner.mp4"

        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.media_player.setLoops(-1) 
        self.media_player.play()

        self._build_ui()

    def on_frame_changed(self, frame):
        self.current_frame = frame
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        if self.current_frame and self.current_frame.isValid():
            img = self.current_frame.toImage()
            if not img.isNull():
                painter.drawImage(self.rect(), img)
            else:
                painter.fillRect(self.rect(), QColor("#020617"))
        else:
            painter.fillRect(self.rect(), QColor("#020617"))

        painter.fillRect(self.rect(), QColor(2, 6, 23, 130))

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame()
        self.card.setMinimumSize(460, 520)
        self.card.setMaximumSize(500, 580)
        self.card.setStyleSheet("""
            QFrame { 
                background-color: rgba(15, 23, 42, 170); 
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 20px; 
            }
        """)
        apply_neon_shadow(self.card, "#0EA5E9", blur=80, y_offset=0)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(45, 45, 45, 45)
        card_layout.setSpacing(25)

        title_label = QLabel("FitTrack AI")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 46px; 
            font-weight: 900; 
            color: #FFFFFF; 
            background: transparent; 
            border: none; 
            font-family: 'Segoe UI';
            letter-spacing: 3px;
        """)
        card_layout.addWidget(title_label)

        subtitle_label = QLabel("מערכת כושר ותזונה חכמה — המרכז האקדמי לב")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 15px; color: #7DD3FC; background: transparent; border: none; font-weight: bold;")
        card_layout.addWidget(subtitle_label)

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent; border: none;")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(20)

        base_input_style = """
            padding: 16px; 
            background-color: rgba(255, 255, 255, 0.05); 
            color: #FFFFFF !important; 
            border: 1px solid rgba(125, 211, 252, 0.3); 
            border-radius: 12px; 
            font-size: 16px; 
            font-weight: bold;
        """
        focus_style = """
            border: 2px solid #38BDF8; 
            background-color: rgba(255, 255, 255, 0.1); 
        """
        label_style = "color: #BAE6FD; font-size: 15px; font-weight: bold; text-align: right; padding-bottom: 2px;"

        form_layout.addWidget(QLabel("שם משתמש", styleSheet=label_style))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("הזן/י שם משתמש...")
        self.username_input.setStyleSheet(f"QLineEdit {{ {base_input_style} text-align: right; }} QLineEdit:focus {{ {focus_style} }}")
        form_layout.addWidget(self.username_input)

        form_layout.addWidget(QLabel("סיסמה", styleSheet=label_style))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("הזן/י סיסמה...")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.password_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.password_input.setStyleSheet(f"QLineEdit {{ {base_input_style} text-align: left; }} QLineEdit:focus {{ {focus_style} }}")
        form_layout.addWidget(self.password_input)

        card_layout.addWidget(form_widget)

        self.login_button = GlowButton("התחברות למערכת", base_color="#0284C7", hover_color="#0EA5E9", glow_color="#7DD3FC")
        self.login_button.clicked.connect(self.handle_login)
        card_layout.addWidget(self.login_button)

        main_layout.addWidget(self.card)

    def showEvent(self, event):
        super().showEvent(event)
        play_card_fly_animation(self.card, 900)

    def handle_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            show_styled_msgbox(self, "שגיאה", "יש להזין שם משתמש וסיסמה.", QMessageBox.Icon.Warning)
            return

        self.login_button.setText("מתחבר לשרת... ⏳")
        self.login_button.setEnabled(False)
        self.presenter.login(username, password)

    def on_login_success(self) -> None:
        self.password_input.clear()
        self.login_button.setText("התחברות למערכת")
        self.login_button.setEnabled(True)
        if hasattr(self, 'media_player'):
            self.media_player.pause()
        self.app_controller.show_dashboard_view()

    def on_login_error(self, message: str) -> None:
        self.login_button.setText("התחברות למערכת")
        self.login_button.setEnabled(True)
        show_styled_msgbox(self, "פרטים שגויים", message, QMessageBox.Icon.Warning)

    def reset_fields(self) -> None:
        self.username_input.clear()
        self.password_input.clear()
        if hasattr(self, 'media_player'):
            self.media_player.play()
# =====================================================================

# =====================================================================
# מסך Dashboard מעוצב - יציב במאה אחוז (בלי באגים של שקיפות)
# =====================================================================
class DashboardView(QWidget):
    def __init__(self, app_controller: "FitTrackApplication", presenter: FitTrackPresenter) -> None:
        super().__init__()
        self.app_controller = app_controller
        self.presenter = presenter
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # כופים צבע רקע יציב וכהה כדי שכרטיס המסך לא יקרוס ויציג לבן
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #020617; color: #F8FAFC;")
        
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # סיידבר
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #0B132B; border-left: 1px solid #1E293B;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(14)

        sidebar_title = QLabel("תפריט FitTrack")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        sidebar_title.setStyleSheet("color: #38BDF8; font-size: 22px; font-weight: bold; background: transparent; border: none;")
        sidebar_layout.addWidget(sidebar_title)

        self.btn_nav_data_entry = GlowButton(" מרכז ניהול והזנה", base_color="#0284C7", hover_color="#0EA5E9", glow_color="#7DD3FC", align="right", border_color="#0369A1")
        self.btn_nav_data_entry.clicked.connect(self.app_controller.open_data_entry_window)
        sidebar_layout.addWidget(self.btn_nav_data_entry)

        self.btn_nav_trends = GlowButton(" מגמות ומדדי אימון", base_color="#9333EA", hover_color="#A855F7", glow_color="#D8B4FE", align="right", border_color="#7E22CE")
        self.btn_nav_trends.clicked.connect(self.app_controller.open_trends_window)
        sidebar_layout.addWidget(self.btn_nav_trends)

        ai_button = GlowButton(" התייעצות עם AI", base_color="#1F2937", hover_color="#374151", glow_color="#9CA3AF", align="right", border_color="#111827")
        ai_button.clicked.connect(self.app_controller.show_ai_view)
        sidebar_layout.addWidget(ai_button)

        self.btn_open_motivation = GlowButton(" השראת ספורט יומית", base_color="#312E81", hover_color="#4338CA", glow_color="#A5B4FC", align="right", border_color="#1E1B4B")
        self.btn_open_motivation.clicked.connect(self.app_controller.open_motivation_window)
        sidebar_layout.addWidget(self.btn_open_motivation)

        sidebar_layout.addStretch()

        logout_button = GlowButton(" התנתק", base_color="#991B1B", hover_color="#DC2626", glow_color="#FCA5A5", align="center")
        logout_button.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_button)

        # אזור התוכן הראשי
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        content_container = QWidget()
        content_container.setStyleSheet("background-color: #020617;") # רקע קשיח שחור-כחול שמונע הלבנה!
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)

        self.welcome_label = QLabel("ברוכ/ה הבא/ה!")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.welcome_label.setStyleSheet("""
            font-size: 32px; 
            font-weight: 900; 
            color: #E0F2FE; 
            background: transparent;
            padding: 5px;
        """)
        content_layout.addWidget(self.welcome_label)

        self.cards_frame = QWidget()
        cards_layout = QHBoxLayout(self.cards_frame)
        cards_layout.setSpacing(20)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        # כרטיסיית קלוריות 
        self.card_cal = HoverCard(bg_color="#0B132B")
        cal_layout = QVBoxLayout(self.card_cal)
        cal_layout.setContentsMargins(20, 20, 20, 20)
        cal_title = QLabel(" קלוריות שנצרכו היום")
        cal_title.setStyleSheet("color: #94A3B8; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        cal_layout.addWidget(cal_title, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.lbl_cal_val = QLabel("0 קק\"ל")
        self.lbl_cal_val.setStyleSheet("font-size: 28px; font-weight: bold; color: #34D399; background: transparent; border: none;")
        cal_layout.addWidget(self.lbl_cal_val, alignment=Qt.AlignmentFlag.AlignLeft)
        cards_layout.addWidget(self.card_cal)

        # כרטיסיית חלבון
        self.card_pro = HoverCard(bg_color="#0B132B")
        pro_layout = QVBoxLayout(self.card_pro)
        pro_layout.setContentsMargins(20, 20, 20, 20)
        pro_title = QLabel(" חלבון יומי שנאכל")
        pro_title.setStyleSheet("color: #94A3B8; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        pro_layout.addWidget(pro_title, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.lbl_pro_val = QLabel("0 גרם")
        self.lbl_pro_val.setStyleSheet("font-size: 28px; font-weight: bold; color: #38BDF8; background: transparent; border: none;")
        pro_layout.addWidget(self.lbl_pro_val, alignment=Qt.AlignmentFlag.AlignLeft)
        cards_layout.addWidget(self.card_pro)

        content_layout.addWidget(self.cards_frame)

        # אזור גרפים משולב בכרטיסייה מרחפת!
        self.charts_card = HoverCard(bg_color="#0B132B")
        charts_main_layout = QVBoxLayout(self.charts_card)
        
        charts_title = QLabel("מרכז ניתוח חזותי ואנליטיקה מרובה (Queries)")
        charts_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        charts_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8; background: transparent; border: none;")
        charts_main_layout.addWidget(charts_title)
        
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        self.chart_view_macro = QChartView()
        self.chart_view_macro.setMinimumHeight(280)
        charts_layout.addWidget(self.chart_view_macro, stretch=1)

        self.chart_view_calories = QChartView()
        self.chart_view_calories.setMinimumHeight(280)
        charts_layout.addWidget(self.chart_view_calories, stretch=1)

        self.chart_view_weight = QChartView()
        self.chart_view_weight.setMinimumHeight(280)
        charts_layout.addWidget(self.chart_view_weight, stretch=1)

        charts_main_layout.addLayout(charts_layout)
        content_layout.addWidget(self.charts_card)

        # טבלת אירועים בתוך כרטיסייה
        self.table_card = HoverCard(bg_color="#0B132B")
        table_layout = QVBoxLayout(self.table_card)
        
        table_title = QLabel(" יומן ארוחות וסנכרון Event Store")
        table_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        table_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #94A3B8; background: transparent; border: none;")
        table_layout.addWidget(table_title)

        self.meals_table = QTableWidget()
        self.meals_table.setColumnCount(3)
        self.meals_table.setHorizontalHeaderLabels(["שם המאכל", "קלוריות", "חלבון"])
        self.meals_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.meals_table.setAlternatingRowColors(True)
        self.meals_table.setStyleSheet("""
            QTableWidget { background-color: transparent; color: white; border: none; gridline-color: #1E293B; font-size: 14px; }
            QHeaderView::section { background-color: #111827; color: #06B6D4; font-weight: bold; padding: 12px; border: none; font-size: 15px; }
            QTableWidget::item { padding: 12px; text-align: right; }
            QTableWidget::item:alternate { background-color: rgba(30, 41, 59, 100); }
        """)
        self.meals_table.cellDoubleClicked.connect(self.on_meal_row_double_clicked)
        self.meals_data: list = []
        table_layout.addWidget(self.meals_table)
        content_layout.addWidget(self.table_card)

        scroll_area.setWidget(content_container)
        root_layout.addWidget(sidebar, stretch=1)
        root_layout.addWidget(scroll_area, stretch=4)

    def execute_remote_meal_save(self, meal_name: str, calories: int, protein_g: int) -> bool:
        return self.presenter.log_meal(meal_name, calories, protein_g)

    def execute_remote_weight_save(self, weight: float, weight_date: str) -> bool:
        return self.presenter.log_weight(weight, weight_date)

    def execute_remote_workout_save(self, workout_type: str, duration_minutes: int) -> bool:
        return self.presenter.log_workout(workout_type, duration_minutes)

    def on_meal_row_double_clicked(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self.meals_data):
            return
        meal = self.meals_data[row]
        event_id = meal.get("id")
        if event_id:
            details = self.presenter.fetch_meal_details(event_id)
            if details:
                MealDetailsDialog.show_meal(self, details)
                return
        MealDetailsDialog.show_meal(self, meal)

    def show_error(self, message: str) -> None:
        show_styled_msgbox(self, "שגיאה", message, QMessageBox.Icon.Critical)

    def update_multiple_charts(self, protein_g: int, carbs_g: int, fat_g: int, current_calories: int, target_calories: int) -> None:
        if not self.chart_view_macro or not self.chart_view_calories:
            return

        pie_macro = QPieSeries()
        pie_macro.append(f"חלבון: {protein_g}ג'", float(protein_g))
        pie_macro.append(f"פחמימות: {carbs_g}ג'", float(carbs_g))
        pie_macro.append(f"שומן: {fat_g}ג'", float(fat_g))
        
        if len(pie_macro.slices()) > 0:
            pie_macro.slices()[0].setExploded(True)
            pie_macro.slices()[0].setLabelVisible(True)
            pie_macro.slices()[0].setBrush(QColor("#06B6D4"))

        chart1 = QChart()
        chart1.addSeries(pie_macro)
        chart1.setTitle("הרכב מאקרו תזונתי יומי")
        chart1.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart1.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart1.legend().setLabelColor(QColor("#94A3B8"))
        
        # צובעים את הרקע של הגרף בכחול-כהה יוקרתי כדי להעלים את הלבן המכוער
        chart1.setBackgroundVisible(True)
        chart1.setBackgroundBrush(QBrush(QColor("#0B132B")))
        chart1.setTitleBrush(QBrush(QColor("#FFFFFF")))
        
        self.chart_view_macro.setChart(chart1)

        pie_cal = QPieSeries()
        cal_consumed_normalized = max(current_calories, 0)
        cal_remaining_normalized = max(target_calories - current_calories, 0)
        
        pie_cal.append(f"נצרך: {current_calories} קק\"ל", float(cal_consumed_normalized))
        pie_cal.append(f"נותר: {cal_remaining_normalized} קק\"ל", float(cal_remaining_normalized))
        
        if len(pie_cal.slices()) > 0:
            pie_cal.slices()[0].setBrush(QColor("#10B981")) 
            if len(pie_cal.slices()) > 1:
                pie_cal.slices()[1].setBrush(QColor("#1F2937")) 

        chart2 = QChart()
        chart2.addSeries(pie_cal)
        chart2.setTitle(f"עמידה ביעד הקלוריות (מטרה: {target_calories})")
        chart2.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart2.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart2.legend().setLabelColor(QColor("#94A3B8"))
        
        # צובעים את הרקע של הגרף בכחול-כהה
        chart2.setBackgroundVisible(True)
        chart2.setBackgroundBrush(QBrush(QColor("#0B132B")))
        chart2.setTitleBrush(QBrush(QColor("#FFFFFF")))
        
        self.chart_view_calories.setChart(chart2)

    def update_weight_chart(self, weight_history: list) -> None:
        if not self.chart_view_weight:
            return

        series = QLineSeries()
        series.setName("משקל (ק\"ג)")
        
        pen = QPen(QColor("#F43F5E"))
        pen.setWidth(3)
        series.setPen(pen)

        min_w = 200.0
        max_w = 0.0

        if weight_history:
            sorted_history = sorted(weight_history, key=lambda x: x["date"])
            for i, entry in enumerate(sorted_history):
                w = float(entry.get("weight", 0))
                series.append(QPointF(i + 1, w))
                if w < min_w: min_w = w
                if w > max_w: max_w = w
        else:
            series.append(QPointF(1, 0))
            min_w, max_w = 0, 10

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("גרף מעקב משקל")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor("#94A3B8"))

        # צובעים את הרקע של הגרף בכחול-כהה
        chart.setBackgroundVisible(True)
        chart.setBackgroundBrush(QBrush(QColor("#0B132B")))
        chart.setTitleBrush(QBrush(QColor("#FFFFFF")))

        axis_x = QValueAxis()
        axis_x.setLabelFormat("%d")
        axis_x.setTitleText("מספר שקילה")
        axis_x.setLabelsColor(QColor("#94A3B8"))
        axis_x.setGridLineColor(QColor("#1E293B"))
        
        if weight_history and len(weight_history) > 1:
            axis_x.setRange(1, len(weight_history))
            axis_x.setTickCount(min(len(weight_history), 5))
        else:
            axis_x.setRange(1, 5)
            axis_x.setTickCount(5)

        axis_y = QValueAxis()
        axis_y.setRange(max(0, min_w - 5), max_w + 5)
        axis_y.setLabelFormat("%.1f")
        axis_y.setTitleText("משקל (ק\"ג)")
        axis_y.setLabelsColor(QColor("#94A3B8"))
        axis_y.setGridLineColor(QColor("#1E293B"))

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        series.setPointsVisible(True)

        self.chart_view_weight.setChart(chart)

    def refresh_data(self) -> None:
        if not self.presenter.active_user:
            return
            
        if self.welcome_label:
            self.welcome_label.setText(f"👋 שלום {self.presenter.active_user.upper()}! ברוכה הבאה למרכז הבקרה שלך")

        data = self.presenter.fetch_dashboard_data()
        if not data:
            return

        meals = data.get("meals", [])
        self.meals_data = meals
        self.meals_table.setRowCount(len(meals))
        for row_index, meal in enumerate(meals):
            self.meals_table.setItem(row_index, 0, QTableWidgetItem(str(meal.get("meal_name", ""))))
            self.meals_table.setItem(row_index, 1, QTableWidgetItem(f"{meal.get('calories', 0)} קק\"ל"))
            self.meals_table.setItem(row_index, 2, QTableWidgetItem(f"{meal.get('protein_g', 0)} גרם"))

        c_cal = data.get("current_calories", 0)
        c_pro = data.get("protein_g", 0)
        if hasattr(self, 'lbl_cal_val') and self.lbl_cal_val:
            self.lbl_cal_val.setText(f"{c_cal} קק\"ל")
        if hasattr(self, 'lbl_pro_val') and self.lbl_pro_val:
            self.lbl_pro_val.setText(f"{c_pro} גרם")

        analysis_text = data.get("weight_analysis", "אין ניתוח מגמות זמין כרגע.")
        if self.app_controller.trends_window:
            self.app_controller.trends_window.update_trends_text(analysis_text)

        self.update_multiple_charts(
            protein_g=c_pro,
            carbs_g=data.get("carbs_g", 180),
            fat_g=data.get("fat_g", 60),
            current_calories=c_cal,
            target_calories=data.get("target_calories", 2000),
        )
        self.update_weight_chart(data.get("weight_history", []))

    def handle_logout(self) -> None:
        self.presenter.logout()
        self.app_controller.login_view.reset_fields()
        self.app_controller.show_login_view()

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

class FitTrackApplication(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.presenter = FitTrackPresenter() 
        
        self.setWindowTitle("FitTrack AI - Lev Academic Center")
        self.resize(1150, 800) 
        self.setMinimumSize(1024, 740)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_view = LoginView(self, self.presenter)
        self.dashboard_view = DashboardView(self, self.presenter)
        self.ai_view = AIAgentView(self)

        self.presenter.set_views(self.login_view, self.dashboard_view)

        self.stacked_widget.addWidget(self.login_view)
        self.stacked_widget.addWidget(self.dashboard_view)
        self.stacked_widget.addWidget(self.ai_view)

        self.motivation_window = None
        self.data_entry_window = None
        self.trends_window = None

        self.show_login_view()

    def show_login_view(self) -> None:
        self.stacked_widget.setCurrentIndex(0)
        play_fade_in_animation(self.login_view, 500)

    def show_dashboard_view(self) -> None:
        self.stacked_widget.setCurrentIndex(1)
        self.dashboard_view.refresh_data()
        play_fade_in_animation(self.dashboard_view, 500)

    def show_ai_view(self) -> None:
        self.stacked_widget.setCurrentIndex(2)
        play_fade_in_animation(self.ai_view, 500)

    def open_motivation_window(self) -> None:
        if self.motivation_window is None:
            self.motivation_window = MotivationWindow()
        self.motivation_window.generate_random_quote()
        self.motivation_window.show()
        self.motivation_window.raise_()
        self.motivation_window.activateWindow()

    def open_data_entry_window(self) -> None:
        if self.data_entry_window is None:
            self.data_entry_window = DataEntryWindow(self.dashboard_view)
        self.data_entry_window.show()
        self.data_entry_window.raise_()
        self.data_entry_window.activateWindow()

    def open_trends_window(self) -> None:
        if self.trends_window is None:
            self.trends_window = TrendsAndWorkoutsWindow(self.dashboard_view)
        self.dashboard_view.refresh_data()
        self.trends_window.show()
        self.trends_window.raise_()
        self.trends_window.activateWindow()

def main() -> None:
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    app.setFont(QFont("Segoe UI", 10))
    window = FitTrackApplication()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()