import sys
import random
from datetime import date
import requests
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QThread, Signal, QUrl
from PySide6.QtGui import QFont, QColor, QLinearGradient, QBrush, QPainter, QPen, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QFrame, QFileDialog, QScrollArea
)
from presenter import FitTrackPresenter

API_BASE_URL = "http://127.0.0.1:8000"

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

def play_card_fly_animation(widget: QWidget, duration: int = 500):
    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    current_pos = widget.pos()
    anim.setStartValue(QPoint(widget.x(), widget.y() + 60))
    anim.setEndValue(current_pos)
    anim.setEasingCurve(QEasingCurve.Type.OutBack)
    widget.fly_anim = anim
    anim.start()

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
                timeout=1000
            )
            response.raise_for_status()
            ai_response = response.json().get("response", "לא התקבלה תשובה.")
        except requests.exceptions.Timeout:
            ai_response = "שגיאה: לשרת ה-AI לקח יותר מדי זמן לענות (Timeout)."
        except Exception as error:
            ai_response = f"שגיאה בקבלת תשובה משרת ה-AI: {error}"
            
        self.finished_signal.emit(ai_response)

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
        
        self.btn_refresh = QPushButton(" הגרל משפט נוסף")
        self.btn_refresh.setStyleSheet("""
            QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: 1px solid #38BDF8; }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.generate_random_quote)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_close = QPushButton("סגור חלונית")
        self.btn_close.setStyleSheet("""
            QPushButton { background-color: #374151; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }
            QPushButton:hover { background-color: #4B5563; }
        """)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        self.quotes = [
            " 'ההבדל בין הבלתי אפשרי לאפשרי שוכן בנחישות של האדם.' — קריסטופר ריב",
            " 'אל תספרו את הימים, גרמו לימים נספרים.' — מוחמד עלי"
        ]
        self.generate_random_quote()

    def generate_random_quote(self) -> None:
        self.lbl_quote.setText(random.choice(self.quotes))
        play_fade_in_animation(self.lbl_quote, 400)

class DataEntryWindow(QWidget):
    def __init__(self, dashboard_view: "DashboardView") -> None:
        super().__init__()
        self.dashboard_view = dashboard_view
        self.setWindowTitle("FitTrack AI — מרכז הזנת נתונים מרוכז")
        self.resize(550, 680)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #0A0F1D; border: 2px solid #06B6D4; border-radius: 12px;")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
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

        nutrition_group = QGroupBox("הוספת מאכל או ארוחה חדשה")
        nutrition_group.setStyleSheet("QGroupBox { font-weight: bold; color: #10B981; border: 1px solid #1E293B; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        nut_layout = QVBoxLayout(nutrition_group)
        nut_layout.setSpacing(10)

        self.btn_camera_ai = QPushButton(" צלם / העלה תמונת ארוחה לניתוח AI אוטומטי")
        self.btn_camera_ai.setStyleSheet("""
            QPushButton { background-color: #0F172A; color: #38BDF8; font-weight: bold; padding: 12px; border: 1px solid #06B6D4; border-radius: 8px; }
            QPushButton:hover { background-color: #1E293B; }
        """)
        self.btn_camera_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_camera_ai.clicked.connect(self.simulate_camera_ai_analysis)
        nut_layout.addWidget(self.btn_camera_ai)
        
        self.btn_open_calculator = QPushButton(" פתח מחשבון קלוריות מתקדם (Ziv Zafrani)")
        self.btn_open_calculator.setStyleSheet("""
            QPushButton { background-color: #F59E0B; color: #FFFFFF; font-weight: bold; padding: 12px; border: none; border-radius: 8px; font-size: 14px; }
            QPushButton:hover { background-color: #D97706; }
        """)
        self.btn_open_calculator.setCursor(Qt.CursorShape.PointingHandCursor)
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

        self.btn_save_meal = QPushButton(" שמור ארוחה זו ביומן")
        self.btn_save_meal.setStyleSheet("""
            QPushButton { background-color: #059669; color: #FFFFFF; font-weight: bold; padding: 12px; border: none; border-radius: 8px; font-size: 14px; }
            QPushButton:hover { background-color: #10B981; }
        """)
        self.btn_save_meal.setCursor(Qt.CursorShape.PointingHandCursor)
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

        self.btn_save_weight = QPushButton(" עדכן מדד משקל")
        self.btn_save_weight.setStyleSheet("""
            QPushButton { background-color: #2563EB; color: #FFFFFF; font-weight: bold; padding: 12px; border: none; border-radius: 8px; font-size: 14px; }
            QPushButton:hover { background-color: #3B82F6; }
        """)
        self.btn_save_weight.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_weight.clicked.connect(self.trigger_weight_save)
        w_layout.addWidget(self.btn_save_weight)

        layout.addWidget(weight_group)

        self.btn_close = QPushButton("סגור חלון הזנה")
        self.btn_close.setStyleSheet("QPushButton { background-color: #374151; color: #FFFFFF; font-weight: bold; padding: 10px; border-radius: 8px; border: none; } QPushButton:hover { background-color: #4B5563; }")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def simulate_camera_ai_analysis(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "בחר תמונת ארוחה לצילום", "", "Images (*.png *.jpg *.jpeg)")
        if not file_path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QTimer.singleShot(1200, self._apply_simulated_ai_data)

    def _apply_simulated_ai_data(self) -> None:
        QApplication.restoreOverrideCursor()
        simulated_meals = [
            {"name": "סלמון בתנור עם פירה", "cal": "580", "pro": "42"},
            {"name": "שקשוקה עם 2 ביצים ולחם מלא", "cal": "450", "pro": "24"}
        ]
        chosen = random.choice(simulated_meals)
        self.meal_name_input.setText(chosen["name"])
        self.meal_calories_input.setText(chosen["cal"])
        self.meal_protein_input.setText(chosen["pro"])
        QMessageBox.information(self, "AI זיהוי", f"ה-AI זיהה בתמונה: '{chosen['name']}'!\nהערכים עודכנו בשדות.")

    def trigger_meal_save(self) -> None:
        meal_name = self.meal_name_input.text().strip()
        calories_text = self.meal_calories_input.text().strip() or "0"
        protein_text = self.meal_protein_input.text().strip() or "0"

        if not meal_name:
            QMessageBox.warning(self, "שגיאה", "שם המאכל הוא שדה חובה.")
            return

        calories = int(calories_text) if calories_text.isdigit() else 0
        protein_g = int(protein_text) if protein_text.isdigit() else 0

        success = self.dashboard_view.execute_remote_meal_save(meal_name, calories, protein_g)
        if success:
            self.meal_name_input.clear()
            self.meal_calories_input.clear()
            self.meal_protein_input.clear()

    def trigger_weight_save(self) -> None:
        weight_text = self.weight_value_input.text().strip()
        weight_date = self.weight_date_input.text().strip()

        if not weight_text or not weight_date:
            QMessageBox.warning(self, "שגיאה", "יש למלא משקל ותאריך.")
            return

        try:
            weight = float(weight_text)
        except ValueError:
            QMessageBox.warning(self, "שגיאה", "משקל חייב להיות מספר.")
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

        self.btn_save_workout = QPushButton(" שמור אימון וסנכרן שריפת קלוריות")
        self.btn_save_workout.setStyleSheet("""
            QPushButton { background-color: #E11D48; color: #FFFFFF; font-weight: bold; padding: 12px; border: none; border-radius: 8px; font-size: 14px; }
            QPushButton:hover { background-color: #F43F5E; }
        """)
        self.btn_save_workout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_workout.clicked.connect(self.trigger_workout_save)
        w_layout.addWidget(self.btn_save_workout)
        layout.addWidget(workout_group)

        self.btn_close = QPushButton("סגור חלון מדדים")
        self.btn_close.setStyleSheet("QPushButton { background-color: #374151; color: #FFFFFF; font-weight: bold; padding: 10px; border-radius: 8px; border: none; } QPushButton:hover { background-color: #4B5563; }")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def trigger_workout_save(self) -> None:
        w_type = self.workout_type_input.text().strip()
        duration_text = self.workout_duration_input.text().strip()

        if not w_type or not duration_text:
            QMessageBox.warning(self, "שגיאה", "יש למלא את סוג האימון ומשך הזמן.")
            return

        duration = int(duration_text) if duration_text.isdigit() else 0
        if duration <= 0:
            QMessageBox.warning(self, "שגיאה", "משך האימון חייב להיות מספר דקות חיובי.")
            return

        success = self.dashboard_view.execute_remote_workout_save(w_type, duration)
        if success:
            self.workout_type_input.clear()
            self.workout_duration_input.clear()

    def update_trends_text(self, text: str) -> None:
        self.lbl_analysis_text.setText(text)


class LoginView(QWidget):
    def __init__(self, app_controller: "FitTrackApplication", presenter: FitTrackPresenter) -> None:
        super().__init__()
        self.app_controller = app_controller
        self.presenter = presenter
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._build_ui()
        
        self.bg_timer = QTimer(self)
        self.bg_timer.timeout.connect(self.update)
        self.bg_timer.start(50)
        self.pulse_val = 0.0
        self.pulse_direction = 1

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#030712"))  
        gradient.setColorAt(0.5, QColor("#0B132B"))  
        gradient.setColorAt(1.0, QColor("#010206"))  
        painter.fillRect(self.rect(), gradient)

        self.pulse_val += 0.02 * self.pulse_direction
        if self.pulse_val > 1.0 or self.pulse_val < 0.0:
            self.pulse_direction *= -1

        center_x = self.width() / 2
        center_y = self.height() / 2
        
        pen1 = QPen(QColor(6, 182, 212, int(40 + (self.pulse_val * 40))))
        pen1.setWidth(2)
        painter.setPen(pen1)
        radius1 = 180 + (self.pulse_val * 30)
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(radius1), int(radius1))

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame()
        self.card.setMinimumSize(480, 520)
        self.card.setMaximumSize(520, 580)
        self.card.setStyleSheet("QFrame { background-color: rgba(11, 19, 43, 245); border: 2px solid #06B6D4; border-radius: 16px; }")
        apply_neon_shadow(self.card, "#06B6D4", blur=40, y_offset=0)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(45, 45, 45, 45)
        card_layout.setSpacing(20)

        title_label = QLabel("FitTrack AI")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 40px; font-weight: bold; color: #38BDF8; background: transparent; border: none; font-family: 'Segoe UI';")
        card_layout.addWidget(title_label)

        subtitle_label = QLabel("מערכת כושר ותזונה מבוזרת — המרכז האקדמי לב")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 13px; color: #94A3B8; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent; border: none;")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(12)

        input_style = """
            QLineEdit { padding: 14px; background-color: #070A14; color: #FFFFFF; border: 1px solid #1E293B; border-radius: 8px; font-size: 15px; text-align: right; }
            QLineEdit:focus { border: 2px solid #06B6D4; background-color: #0B132B; }
        """
        label_style = "color: #FFFFFF; font-size: 14px; font-weight: bold; text-align: right;"

        form_layout.addWidget(QLabel("שם משתמש:", styleSheet=label_style))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("הזן שם משתמש...")
        self.username_input.setStyleSheet(input_style)
        form_layout.addWidget(self.username_input)

        form_layout.addWidget(QLabel("סיסמה:", styleSheet=label_style))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("הזן סיסמה...")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(input_style)
        form_layout.addWidget(self.password_input)

        card_layout.addWidget(form_widget)

        self.login_button = QPushButton("התחברות למערכת")
        self.login_button.setStyleSheet("""
            QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 15px; border: 1px solid #38BDF8; border-radius: 8px; font-size: 16px; }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self.handle_login)
        card_layout.addWidget(self.login_button)

        main_layout.addWidget(self.card)

    def showEvent(self, event):
        super().showEvent(event)
        play_card_fly_animation(self.card, 500)

    def handle_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "שגיאה", "יש להזין שם משתמש וסיסמה.")
            return

        self.presenter.login(username, password)

    def on_login_success(self) -> None:
        self.password_input.clear()
        self.app_controller.show_dashboard_view()

    def on_login_error(self, message: str) -> None:
        QMessageBox.warning(self, "פרטים שגויים", message)

    def reset_fields(self) -> None:
        self.username_input.clear()
        self.password_input.clear()


class DashboardView(QWidget):
    def __init__(self, app_controller: "FitTrackApplication", presenter: FitTrackPresenter) -> None:
        super().__init__()
        self.app_controller = app_controller
        self.presenter = presenter
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #030712; color: #F8FAFC;")
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #0B132B; border-left: 1px solid #1E293B;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(14)

        sidebar_title = QLabel("תפריט FitTrack")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        sidebar_title.setStyleSheet("color: #06B6D4; font-size: 20px; font-weight: bold;")
        sidebar_layout.addWidget(sidebar_title)

        self.btn_nav_data_entry = QPushButton(" מרכז ניהול והזנה")
        self.btn_nav_data_entry.setStyleSheet("""
            QPushButton { background-color: #0284C7; color: white; padding: 14px; border: 1px solid #38BDF8; border-radius: 8px; font-weight: bold; text-align: right; font-size: 14px; }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.btn_nav_data_entry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nav_data_entry.clicked.connect(self.app_controller.open_data_entry_window)
        sidebar_layout.addWidget(self.btn_nav_data_entry)

        self.btn_nav_trends = QPushButton(" מגמות ומדדי אימון")
        self.btn_nav_trends.setStyleSheet("""
            QPushButton { background-color: #A855F7; color: white; padding: 14px; border: 1px solid #C084FC; border-radius: 8px; font-weight: bold; text-align: right; font-size: 14px; }
            QPushButton:hover { background-color: #7E22CE; }
        """)
        self.btn_nav_trends.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nav_trends.clicked.connect(self.app_controller.open_trends_window)
        sidebar_layout.addWidget(self.btn_nav_trends)

        ai_button = QPushButton(" התייעצות עם AI")
        ai_button.setStyleSheet("""
            QPushButton { background-color: #1F2937; color: white; padding: 12px; border: 1px solid #374151; border-radius: 8px; font-weight: bold; text-align: right; }
            QPushButton:hover { background-color: #374151; }
        """)
        ai_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ai_button.clicked.connect(self.app_controller.show_ai_view)
        sidebar_layout.addWidget(ai_button)

        self.btn_open_motivation = QPushButton(" השראת ספורט יומית")
        self.btn_open_motivation.setStyleSheet("""
            QPushButton { background-color: #1E1B4B; color: #E9D5FF; padding: 12px; border: 1px solid #A855F7; border-radius: 8px; font-weight: bold; text-align: right; }
            QPushButton:hover { background-color: #2E1065; }
        """)
        self.btn_open_motivation.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_motivation.clicked.connect(self.app_controller.open_motivation_window)
        sidebar_layout.addWidget(self.btn_open_motivation)

        sidebar_layout.addStretch()

        logout_button = QPushButton(" התנתק")
        logout_button.setStyleSheet("QPushButton { background-color: #991B1B; color: white; padding: 12px; border: none; border-radius: 8px; font-weight: bold; } QPushButton:hover { background-color: #DC2626; }")
        logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_button.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_button)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        content_container = QWidget()
        content_container.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)

        self.welcome_label = QLabel("ברוכ/ה הבא/ה!")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.welcome_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #FFFFFF;")
        content_layout.addWidget(self.welcome_label)

        self.cards_frame = QWidget()
        cards_layout = QHBoxLayout(self.cards_frame)
        cards_layout.setSpacing(16)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        card_css = "QWidget { background-color: #0B132B; border: 1px solid #1E293B; border-radius: 12px; } QLabel { background: transparent; border: none; color: #94A3B8; font-size: 13px; }"

        self.card_cal = QWidget()
        self.card_cal.setStyleSheet(card_css)
        cal_layout = QVBoxLayout(self.card_cal)
        cal_layout.setContentsMargins(14, 14, 14, 14)
        cal_layout.addWidget(QLabel(" קלוריות שנצרכו היום"), alignment=Qt.AlignmentFlag.AlignRight)
        self.lbl_cal_val = QLabel("0 קק\"ל")
        self.lbl_cal_val.setStyleSheet("font-size: 24px; font-weight: bold; color: #10B981; background: transparent;")
        cal_layout.addWidget(self.lbl_cal_val, alignment=Qt.AlignmentFlag.AlignLeft)
        cards_layout.addWidget(self.card_cal)

        self.card_pro = QWidget()
        self.card_pro.setStyleSheet(card_css)
        pro_layout = QVBoxLayout(self.card_pro)
        pro_layout.setContentsMargins(14, 14, 14, 14)
        pro_layout.addWidget(QLabel(" חלבון יומי שנאכל"), alignment=Qt.AlignmentFlag.AlignRight)
        self.lbl_pro_val = QLabel("0 גרם")
        self.lbl_pro_val.setStyleSheet("font-size: 24px; font-weight: bold; color: #06B6D4; background: transparent;")
        pro_layout.addWidget(self.lbl_pro_val, alignment=Qt.AlignmentFlag.AlignLeft)
        cards_layout.addWidget(self.card_pro)

        content_layout.addWidget(self.cards_frame)

        charts_box = QGroupBox("מרכז ניתוח חזותי ואנליטיקה מרובה (Queries)")
        charts_box.setStyleSheet("QGroupBox { font-weight: bold; color: #06B6D4; border: 1px solid #1E293B; border-radius: 12px; margin-top: 5px; padding-top: 16px; background-color: #0B132B; font-size: 14px; }")
        apply_neon_shadow(charts_box, "#000000", blur=15, y_offset=4)
        charts_layout = QHBoxLayout(charts_box)
        charts_layout.setSpacing(16)

        self.chart_view_macro = QChartView()
        self.chart_view_macro.setMinimumHeight(280)
        self.chart_view_macro.setStyleSheet("background-color: transparent;")
        charts_layout.addWidget(self.chart_view_macro, stretch=1)

        self.chart_view_calories = QChartView()
        self.chart_view_calories.setMinimumHeight(280)
        self.chart_view_calories.setStyleSheet("background-color: transparent;")
        charts_layout.addWidget(self.chart_view_calories, stretch=1)

        content_layout.addWidget(charts_box)

        table_container = QVBoxLayout()
        table_title = QLabel(" יומן ארוחות וסנכרון Event Store")
        table_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        table_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #94A3B8;")
        table_container.addWidget(table_title)

        self.meals_table = QTableWidget()
        self.meals_table.setColumnCount(3)
        self.meals_table.setHorizontalHeaderLabels(["שם המאכל", "קלוריות", "חלבון"])
        self.meals_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.meals_table.setAlternatingRowColors(True)
        self.meals_table.setStyleSheet("""
            QTableWidget { background-color: #0B132B; color: white; border: 1px solid #1E293B; gridline-color: #1E293B; border-radius: 8px; padding: 5px; font-size: 14px; }
            QHeaderView::section { background-color: #111827; color: #06B6D4; font-weight: bold; padding: 10px; border: none; font-size: 14px; }
            QTableWidget::item { padding: 12px; text-align: right; }
        """)
        table_container.addWidget(self.meals_table)
        content_layout.addLayout(table_container)

        scroll_area.setWidget(content_container)
        root_layout.addWidget(sidebar, stretch=1)
        root_layout.addWidget(scroll_area, stretch=4)

    def execute_remote_meal_save(self, meal_name: str, calories: int, protein_g: int) -> bool:
        return self.presenter.log_meal(meal_name, calories, protein_g)

    def execute_remote_weight_save(self, weight: float, weight_date: str) -> bool:
        return self.presenter.log_weight(weight, weight_date)

    def execute_remote_workout_save(self, workout_type: str, duration_minutes: int) -> bool:
        return self.presenter.log_workout(workout_type, duration_minutes)

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "שגיאה", message)

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
        chart1.setBackgroundVisible(False)
        chart1.setTitleBrush(QBrush(QColor("#FFFFFF")))
        chart1.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart1.legend().setLabelColor(QColor("#94A3B8"))
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
        chart2.setBackgroundVisible(False)
        chart2.setTitleBrush(QBrush(QColor("#FFFFFF")))
        chart2.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart2.legend().setLabelColor(QColor("#94A3B8"))
        self.chart_view_calories.setChart(chart2)

    def refresh_data(self) -> None:
        if not self.presenter.active_user:
            return
            
        if self.welcome_label:
            self.welcome_label.setText(f"שלום, {self.presenter.active_user}! מרכז הבקרה התזונתי שלך")

        data = self.presenter.fetch_dashboard_data()
        if not data:
            return

        meals = data.get("meals", [])
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
            target_calories=data.get("target_calories", 2000)
        )

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

        back_button = QPushButton(" חזרה למרכז הבקרה")
        back_button.setStyleSheet("QPushButton { background-color: #1F2937; color: white; padding: 10px 16px; border: 1px solid #374151; border-radius: 6px; font-weight: bold; } QPushButton:hover { background-color: #374151; }")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
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

        self.add_ai_bubble("שלום! מערכת ה-RAG עלתה בהצלחה ממיכל ה-Docker. אני FitTrack AI, סוכן מותאם אישית. שאלי אותי כל שאלה לגבי תפריטים, חלבונים או יעדי משקל.")

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

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

        self.btn_send = QPushButton("שאל את הסוכן")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #0284C7; color: white; font-weight: bold; font-size: 15px;
                padding: 15px 25px; border: 1px solid #38BDF8; border-radius: 10px;
            }
            QPushButton:hover { background-color: #0369A1; }
            QPushButton:disabled { background-color: #374151; color: #9CA3AF; border: none; }
        """)
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
        self.btn_send.setText("הסוכן חושב...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        username = getattr(self.app_controller.presenter, 'active_user', 'Guest')
        self.worker = AIWorker(user_text, username, self.api_base_url)
        self.worker.finished_signal.connect(self.on_ai_response_received)
        self.worker.start()

    def on_ai_response_received(self, response_text: str):
        QApplication.restoreOverrideCursor()
        self.btn_send.setEnabled(True)
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