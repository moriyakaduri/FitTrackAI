import sys
from datetime import date
import requests
from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QLinearGradient, QBrush, QPalette
from PySide6.QtWidgets import (
    QApplication, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QFrame
)

API_BASE_URL = "http://127.0.0.1:8000"

# פונקציית עזר להחלת צל יוקרתי על רכיבים
def apply_neon_shadow(widget: QWidget, color_hex: str = "#000000", blur: int = 15, y_offset: int = 4):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(color_hex))
    widget.setGraphicsEffect(shadow)

# פונקציית עזר להפעלת אנימציית Fade-In חלקה בעת כניסה למסך
def play_fade_in_animation(widget: QWidget, duration: int = 500):
    opacity_effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(opacity_effect)
    
    anim = QPropertyAnimation(opacity_effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
    
    # שמירת רפרנס לאנימציה כדי שלא תימחק מהזיכרון
    widget.fade_anim = anim
    anim.start()

# ==============================================================================
# View 1: מסך התחברות יוקרתי בסגנון דיגיטלי הייטקיסטי
# ==============================================================================
class LoginView(QWidget):
    def __init__(self, app_controller: "FitTrackApplication") -> None:
        super().__init__()
        self.app_controller = app_controller
        self._build_ui()

    def paintEvent(self, event) -> None:
        """יצירת רקע גרדיאנט דיגיטלי מדהים שזז בעין ללא צורך בתמונה חיצונית שבירה"""
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#0F172A"))  # כחול-שחור עמוק
        gradient.setColorAt(0.5, QColor("#1E1B4B"))  # סגול הייטק
        gradient.setColorAt(1.0, QColor("#031321"))  # אקווה כהה
        
        palette = self.palette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(gradient))
        self.setPalette(palette)

    def _build_ui(self) -> None:
        self.setAutoFillBackground(True)
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # כרטיס התחברות מרכזי צף (Frosted Glass Container)
        card = QFrame()
        card.setFixedSize(450, 480)
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 41, 59, 220); /* כרטיס שקוף למחצה */
                border: 1px solid rgba(56, 189, 248, 100); /* מסגרת ניאון עדינה */
                border-radius: 16px;
            }
        """)
        apply_neon_shadow(card, "#000000", blur=25, y_offset=8)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(35, 40, 35, 35)
        card_layout.setSpacing(20)

        # כותרות המערכת
        title_label = QLabel("FitTrack AI")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #38BDF8; background: transparent; border: none;")
        card_layout.addWidget(title_label)

        subtitle_label = QLabel("פלטפורמת בריאות וכושר חכמה — המרכז האקדמי לב")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 12px; color: #94A3B8; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        # טופס כניסה
        form_container = QWidget()
        form_container.setStyleSheet("background: transparent; border: none;")
        form_layout = QFormLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        input_style = """
            QLineEdit {
                padding: 12px; 
                background-color: #0F172A; 
                color: #F8FAFC;
                border: 1px solid #475569; 
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #38BDF8;
                background-color: #1E293B;
            }
        """

        label_style = "color: #E2E8F0; font-size: 13px; font-weight: bold;"

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("הזן/י שם משתמש")
        self.username_input.setStyleSheet(input_style)
        username_label = QLabel("שם משתמש:")
        username_label.setStyleSheet(label_style)
        form_layout.addRow(username_label, self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("הזן/י סיסמה")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(input_style)
        password_label = QLabel("סיסמה:")
        password_label.setStyleSheet(label_style)
        form_layout.addRow(password_label, self.password_input)

        card_layout.addWidget(form_container)

        # כפתור התחברות דיגיטלי מגיב
        login_button = QPushButton("התחברות למערכת")
        login_button.setStyleSheet("""
            QPushButton {
                background-color: #2563EB; 
                color: white; 
                font-weight: bold; 
                padding: 14px; 
                border: none; 
                border-radius: 8px; 
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #3B82F6;
                border: 1px solid #60A5FA;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)
        login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        login_button.clicked.connect(self.handle_login)
        card_layout.addWidget(login_button)

        # רשימת מפתחים ומשתמשים מורחבת (דרישת שלשה)
        hint_label = QLabel("סביבת פיתוח: Moriah | Moriya | LevDeveloper\nסיסמת גישה: 123456 (או לב2026)")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: #64748B; font-size: 11px; background: transparent; border: none; line-height: 15px;")
        card_layout.addWidget(hint_label)

        main_layout.addWidget(card)

    def handle_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "שגיאה", "יש להזין שם משתמש וסיסמה.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/users/login",
                json={"username": username, "password": password},
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "שגיאת תקשורת", "השרת כבוי. אנא הפעל/י את שרת ה-Backend (FastAPI) ונסה/י שוב.")
            return

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                self.app_controller.active_user = data.get("username", username)
                self.password_input.clear()
                self.app_controller.show_dashboard_view()
                return

        QMessageBox.warning(self, "פרטים שגויים", "שם משתמש או סיסמה שגויים. נסה/י שוב.")

    def reset_fields(self) -> None:
        self.username_input.clear()
        self.password_input.clear()


# ==============================================================================
# View 2: מסך בקרה מרכזי (Dashboard) דיגיטלי כהה
# ==============================================================================
class DashboardView(QWidget):
    def __init__(self, app_controller: "FitTrackApplication") -> None:
        super().__init__()
        self.app_controller = app_controller
        self.setStyleSheet("background-color: #0F172A; color: #E2E8F0;") # כחול-כהה דיגיטלי
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # סרגל ניווט צדדי (Sidebar)
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #1E293B; border-right: 1px solid #334155;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(16)

        sidebar_title = QLabel("תפריט FitTrack")
        sidebar_title.setStyleSheet("color: #38BDF8; font-size: 18px; font-weight: bold;")
        sidebar_layout.addWidget(sidebar_title)

        ai_button = QPushButton("💬 התייעצות עם AI")
        ai_button.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: white; padding: 12px; 
                border: 1px solid #475569; border-radius: 8px; font-weight: bold; text-align: right;
            }
            QPushButton:hover {
                background-color: #475569; border: 1px solid #38BDF8;
            }
        """)
        ai_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ai_button.clicked.connect(self.app_controller.show_ai_view)
        sidebar_layout.addWidget(ai_button)

        sidebar_layout.addStretch()

        logout_button = QPushButton("🚪 התנתק")
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #991B1B; color: white; padding: 12px; 
                border: none; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_button.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_button)

        # אזור התוכן המרכזי
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        self.welcome_label = QLabel("ברוכ/ה הבא/ה!")
        self.welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        content_layout.addWidget(self.welcome_label)

        # פריסה עליונה: טפסים + גרף
        top_section = QHBoxLayout()
        top_section.setSpacing(16)

        # קבוצת טפסי הזנה
        forms_group = QGroupBox("מרכז ניהול והזנת נתונים (Commands)")
        forms_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; color: #38BDF8; border: 1px solid #334155; 
                border-radius: 12px; margin-top: 12px; padding-top: 16px; background-color: #1E293B;
            }
        """)
        apply_neon_shadow(forms_group, "#000000", blur=15, y_offset=4)
        forms_layout = QVBoxLayout(forms_group)
        forms_layout.setSpacing(12)

        field_style = """
            QLineEdit {
                padding: 10px; border: 1px solid #475569; 
                border-radius: 6px; background-color: #0F172A; color: white;
            }
            QLineEdit:focus { border: 1px solid #38BDF8; }
        """
        label_style = "color: #94A3B8; font-weight: bold; font-size: 12px;"

        # תת טופס תזונה
        meal_box = QWidget()
        meal_form = QFormLayout(meal_box)
        meal_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.meal_name_input = QLineEdit()
        self.meal_name_input.setPlaceholderText("שם המאכל (לדוגמה: שייק חלבון)")
        self.meal_name_input.setStyleSheet(field_style)
        l1 = QLabel("מאכל:")
        l1.setStyleSheet(label_style)
        meal_form.addRow(l1, self.meal_name_input)

        self.meal_calories_input = QLineEdit()
        self.meal_calories_input.setPlaceholderText("משוער או 0 לחישוב AI חכם")
        self.meal_calories_input.setStyleSheet(field_style)
        l2 = QLabel("קלוריות:")
        l2.setStyleSheet(label_style)
        meal_form.addRow(l2, self.meal_calories_input)

        self.meal_protein_input = QLineEdit()
        self.meal_protein_input.setPlaceholderText("משוער או 0 לחישוב AI חכם")
        self.meal_protein_input.setStyleSheet(field_style)
        l3 = QLabel("חלבון (ג'):")
        l3.setStyleSheet(label_style)
        meal_form.addRow(l3, self.meal_protein_input)

        save_meal_button = QPushButton("💾 שמור ארוחה בענן")
        save_meal_button.setStyleSheet("""
            QPushButton { background-color: #059669; color: white; font-weight: bold; padding: 10px; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #10B981; }
        """)
        save_meal_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_meal_button.clicked.connect(self.save_meal)
        meal_form.addRow("", save_meal_button)
        forms_layout.addWidget(meal_box)

        # תת טופס שקילה
        weight_box = QWidget()
        weight_form = QFormLayout(weight_box)
        weight_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.weight_value_input = QLineEdit()
        self.weight_value_input.setPlaceholderText("משקל נוכחי בק\"ג")
        self.weight_value_input.setStyleSheet(field_style)
        l4 = QLabel("משקל:")
        l4.setStyleSheet(label_style)
        weight_form.addRow(l4, self.weight_value_input)

        self.weight_date_input = QLineEdit()
        self.weight_date_input.setText(date.today().isoformat())
        self.weight_date_input.setStyleSheet(field_style)
        l5 = QLabel("תאריך:")
        l5.setStyleSheet(label_style)
        weight_form.addRow(l5, self.weight_date_input)

        save_weight_button = QPushButton("⚖️ עדכן מדדי שקילה")
        save_weight_button.setStyleSheet("""
            QPushButton { background-color: #2563EB; color: white; font-weight: bold; padding: 10px; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #3B82F6; }
        """)
        save_weight_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_weight_button.clicked.connect(self.save_weight)
        weight_form.addRow("", save_weight_button)
        forms_layout.addWidget(weight_box)

        top_section.addWidget(forms_group, stretch=1)

        # קבוצת הגרף
        chart_container = QGroupBox("מרכז ניתוח חזותי (Queries)")
        chart_container.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; color: #38BDF8; border: 1px solid #334155; 
                border-radius: 12px; margin-top: 12px; padding-top: 16px; background-color: #1E293B;
            }
        """)
        apply_neon_shadow(chart_container, "#000000", blur=15, y_offset=4)
        chart_layout = QVBoxLayout(chart_container)

        self.chart_view = QChartView()
        self.chart_view.setMinimumHeight(280)
        self.chart_view.setStyleSheet("background-color: transparent;")
        chart_layout.addWidget(self.chart_view)

        top_section.addWidget(chart_container, stretch=1)
        content_layout.addLayout(top_section)

        # חלק תחתון: טבלה + מגמת משקל
        bottom_section = QHBoxLayout()
        bottom_section.setSpacing(16)

        table_container = QVBoxLayout()
        table_title = QLabel("📋 יומן ארוחות וסנכרון Event Store")
        table_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #94A3B8;")
        table_container.addWidget(table_title)

        self.meals_table = QTableWidget()
        self.meals_table.setColumnCount(3)
        self.meals_table.setHorizontalHeaderLabels(["שם המאכל", "קלוריות", "חלבון"])
        self.meals_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.meals_table.setAlternatingRowColors(True)
        self.meals_table.setStyleSheet("""
            QTableWidget { 
                background-color: #1E293B; color: white; border: 1px solid #334155; gridline-color: #334155; border-radius: 8px; padding: 5px;
            }
            QHeaderView::section { 
                background-color: #334155; color: #38BDF8; font-weight: bold; padding: 8px; border: none; 
            }
            QTableWidget::item { padding: 10px; }
        """)
        apply_neon_shadow(self.meals_table, "#000000", blur=10, y_offset=2)
        table_container.addWidget(self.meals_table)
        bottom_section.addLayout(table_container, stretch=3)

        trend_container = QVBoxLayout()
        trend_title = QLabel("📉 מגמות ואנליטיקה")
        trend_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #94A3B8;")
        trend_container.addWidget(trend_title)

        self.weight_trend_label = QLabel("טוען אנליטיקה...")
        self.weight_trend_label.setWordWrap(True)
        self.weight_trend_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.weight_trend_label.setStyleSheet("""
            background-color: #1E293B; border: 1px solid #334155; 
            border-radius: 8px; padding: 16px; font-size: 13px; color: #E2E8F0; line-height: 20px;
        """)
        self.weight_trend_label.setMinimumWidth(220)
        apply_neon_shadow(self.weight_trend_label, "#000000", blur=10, y_offset=2)
        trend_container.addWidget(self.weight_trend_label)
        trend_container.addStretch()
        bottom_section.addLayout(trend_container, stretch=1)

        content_layout.addLayout(bottom_section)

        root_layout.addWidget(sidebar, stretch=1)
        root_layout.addWidget(content_area, stretch=4)

    def update_welcome_message(self) -> None:
        if self.welcome_label and self.app_controller.active_user:
            self.welcome_label.setText(f"שלום, {self.app_controller.active_user}! מרכז הבקרה התזונתי שלך")

    def save_meal(self) -> None:
        meal_name = self.meal_name_input.text().strip() if self.meal_name_input else ""
        calories_text = self.meal_calories_input.text().strip() if self.meal_calories_input else "0"
        protein_text = self.meal_protein_input.text().strip() if self.meal_protein_input else "0"

        if not meal_name:
            QMessageBox.warning(self, "שגיאה", "שם המאכל הוא שדה חובה.")
            return

        # החלפת ערך ריק ב-0 כדי לאפשר לשרת להפעיל את רכיב ה-AI שלו
        calories = int(calories_text) if calories_text.isdigit() else 0
        protein_g = int(protein_text) if protein_text.isdigit() else 0

        try:
            response = requests.post(
                f"{API_BASE_URL}/users/log-meal",
                json={
                    "meal_name": meal_name,
                    "calories": calories,
                    "protein_g": protein_g,
                    "username": self.app_controller.active_user
                },
                timeout=10,
            )
            response.raise_for_status()
        except Exception as error:
            QMessageBox.critical(self, "שגיאה", f"שמירת הארוחה נכשלה:\n{error}")
            return

        self.meal_name_input.clear()
        self.meal_calories_input.clear()
        self.meal_protein_input.clear()
        self.refresh_data()

    def save_weight(self) -> None:
        weight_text = self.weight_value_input.text().strip() if self.weight_value_input else ""
        weight_date = self.weight_date_input.text().strip() if self.weight_date_input else ""

        if not weight_text or not weight_date:
            QMessageBox.warning(self, "שגיאה", "יש למלא משקל ותאריך.")
            return

        try:
            weight = float(weight_text)
        except ValueError:
            QMessageBox.warning(self, "שגיאה", "משקל חייב להיות מספר.")
            return

        try:
            response = requests.post(
                f"{API_BASE_URL}/users/log-weight",
                json={"weight": weight, "date": weight_date, "username": self.app_controller.active_user},
                timeout=10,
            )
            response.raise_for_status()
        except Exception as error:
            QMessageBox.critical(self, "שגיאה", f"עדכון המשקל נכשל:\n{error}")
            return

        self.weight_value_input.clear()
        self.weight_date_input.setText(date.today().isoformat())
        self.refresh_data()

    def update_weight_trend(self, weight_history: list, analysis_text: str) -> None:
        if not self.weight_trend_label:
            return
        
        # הדפסת הניתוח המפורט מהשרת (דרישה 3.2 ו-3.3)
        self.weight_trend_label.setText(analysis_text)

    def update_pie_chart(self, protein_g: int, carbs_g: int, fat_g: int, current_calories: int, target_calories: int) -> None:
        if not self.chart_view:
            return

        pie_series = QPieSeries()
        pie_series.append(f"חלבון: {protein_g}ג'", float(protein_g))
        pie_series.append(f"פחמימות: {carbs_g}ג'", float(carbs_g))
        pie_series.append(f"שומן: {fat_g}ג'", float(fat_g))
        
        # הוספת פלח קלוריות פרופורציונלי
        calories_divider = max(current_calories / 10, 1)
        pie_series.append(f"סך קלוריות: {current_calories} קק\"ל", calories_divider)

        # עיצוב פלח החלבון שיהיה בולט ומעוצב
        if len(pie_series.slices()) > 0:
            slice_protein = pie_series.slices()[0]
            slice_protein.setExploded(True)
            slice_protein.setLabelVisible(True)
            slice_protein.setBrush(QColor("#38BDF8")) # צבע ניאון זוהר

        chart = QChart()
        chart.addSeries(pie_series)
        chart.setTitle(f"יעד יומי: {current_calories} / {target_calories} קק\"ל")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundVisible(False)
        chart.setTitleBrush(QBrush(QColor("#FFFFFF")))
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor("#94A3B8"))

        self.chart_view.setChart(chart)

    def refresh_data(self) -> None:
        self.update_welcome_message()

        try:
            response = requests.get(
                f"{API_BASE_URL}/users/nutrition-summary?username={self.app_controller.active_user}",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as error:
            QMessageBox.critical(self, "שגיאה", f"טעינת הנתונים נכשלה:\n{error}")
            return

        meals = data.get("meals", [])
        if self.meals_table:
            self.meals_table.setRowCount(len(meals))
            for row_index, meal in enumerate(meals):
                self.meals_table.setItem(row_index, 0, QTableWidgetItem(str(meal.get("meal_name", ""))))
                self.meals_table.setItem(row_index, 1, QTableWidgetItem(f"{meal.get('calories', 0)} קק\"ל"))
                self.meals_table.setItem(row_index, 2, QTableWidgetItem(f"{meal.get('protein_g', 0)} גרם"))

        self.update_weight_trend(data.get("weight_history", []), data.get("weight_analysis", ""))
        self.update_pie_chart(
            protein_g=data.get("protein_g", 0),
            carbs_g=data.get("carbs_g", 180),
            fat_g=data.get("fat_g", 60),
            current_calories=data.get("current_calories", 0),
            target_calories=data.get("target_calories", 2000)
        )

    def handle_logout(self) -> None:
        self.app_controller.active_user = None
        self.app_controller.login_view.reset_fields()
        self.app_controller.show_login_view()


# ==============================================================================
# View 3: מסך צ'אט יועץ AI מתקדם (Ollama RAG Container)
# ==============================================================================
class AIConsultantView(QWidget):
    def __init__(self, app_controller: "FitTrackApplication") -> None:
        super().__init__()
        self.app_controller = app_controller
        self.setStyleSheet("background-color: #0F172A; color: #E2E8F0;")
        self.chat_display: QTextEdit | None = None
        self.message_input: QLineEdit | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        back_button = QPushButton("⬅️ חזרה למרכז הבקרה")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: white; padding: 10px 16px; 
                border: 1px solid #475569; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #475569; border: 1px solid #38BDF8; }
        """)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.app_controller.show_dashboard_view)
        back_button.setFixedWidth(200)
        main_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        title_label = QLabel("🤖 Ollama RAG Container — סוכן ייעוץ תזונה וכושר חכם")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1E293B; color: #E2E8F0; border: 1px solid #334155; 
                border-radius: 12px; padding: 16px; font-size: 13px; line-height: 22px;
            }
        """)
        apply_neon_shadow(self.chat_display, "#000000", blur=15, y_offset=4)
        
        self.chat_display.setHtml(
            "<p style='color:#38BDF8; font-size:14px;'>"
            "<b>FitTrack AI Agent:</b> שלום! מערכת ה-RAG עלתה בהצלחה ממיכל ה-Docker. "
            "שאל/י אותי כל שאלה לגבי תפריטים, חלבונים או יעדי משקל, ואנתח אותם עבורך באופן מותאם אישית."
            "</p><hr style='border-color:#334155;'>"
        )
        main_layout.addWidget(self.chat_display)

        input_row = QHBoxLayout()
        input_row.setSpacing(12)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("הקלד/י שאלה ליועץ ה-AI (לדוגמה: כמה חלבון מומלץ לי לאכול?)...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                padding: 12px; border: 1px solid #475569; border-radius: 8px; 
                background-color: #1E293B; color: white; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #38BDF8; }
        """)
        self.message_input.returnPressed.connect(self.send_to_ai)
        input_row.addWidget(self.message_input)

        send_button = QPushButton("שאל את הסוכן")
        send_button.setStyleSheet("""
            QPushButton { background-color: #2563EB; color: white; font-weight: bold; padding: 12px 24px; border: none; border-radius: 8px; }
            QPushButton:hover { background-color: #3B82F6; }
        """)
        send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        send_button.clicked.connect(self.send_to_ai)
        input_row.addWidget(send_button)

        main_layout.addLayout(input_row)

    def send_to_ai(self) -> None:
        if not self.message_input or not self.chat_display:
            return

        user_message = self.message_input.text().strip()
        if not user_message:
            return

        self.chat_display.append(f"<p style='font-size:13px;'><b>👤 את/ה:</b> {user_message}</p>")
        self.message_input.clear()

        try:
            response = requests.post(
                f"{API_BASE_URL}/ai/analyze-food",
                json={"message": user_message, "username": self.app_controller.active_user},
                timeout=30,
            )
            response.raise_for_status()
            ai_response = response.json().get("response", "לא התקבלה תשובה.")
        except Exception as error:
            ai_response = f"שגיאה בקבלת תשובה משרת ה-AI: {error}"

        formatted_response = ai_response.replace("\n", "<br>")
        self.chat_display.append(f"<p style='color:#38BDF8; font-size:13px;'><b>🤖 FitTrack AI:</b> {formatted_response}</p>")
        self.chat_display.append("<hr style='border-color:#334155;'>")


# ==============================================================================
# Main Application Controller (Stacked Layout Framework)
# ==============================================================================
class FitTrackApplication(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.active_user = None
        self.setWindowTitle("FitTrack AI - Lev Academic Center")
        self.setFixedSize(980, 680) # גודל מורחב ומקצועי למניעת חיתוכי מסך

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_view = LoginView(self)
        self.dashboard_view = DashboardView(self)
        self.ai_view = AIConsultantView(self)

        self.stacked_widget.addWidget(self.login_view)       # Index 0
        self.stacked_widget.addWidget(self.dashboard_view)   # Index 1
        self.stacked_widget.addWidget(self.ai_view)          # Index 2

        self.show_login_view()

    def show_login_view(self) -> None:
        self.stacked_widget.setCurrentIndex(0)
        play_fade_in_animation(self.login_view)

    def show_dashboard_view(self) -> None:
        self.stacked_widget.setCurrentIndex(1)
        self.dashboard_view.refresh_data()
        play_fade_in_animation(self.dashboard_view)

    def show_ai_view(self) -> None:
        self.stacked_widget.setCurrentIndex(2)
        play_fade_in_animation(self.ai_view)

def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = FitTrackApplication()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()