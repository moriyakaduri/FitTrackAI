"""Management and data-entry feature window."""

from datetime import date

import requests
from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QScrollArea, QVBoxLayout, QWidget,
)

from features.ui_components import GlowButton, make_page_header, show_styled_msgbox

API_BASE_URL = "http://127.0.0.1:8000"

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

class DataEntryWindow(QWidget):
    def __init__(self, dashboard_view: "DashboardView", api_base_url: str = API_BASE_URL) -> None:
        super().__init__()
        self.dashboard_view = dashboard_view
        self.api_base_url = api_base_url
        self.setWindowTitle("FitTrack AI — הזנת נתונים")
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

        layout.addWidget(make_page_header(
            "הזנת נתונים",
            "חיפוש במאגר, ברקוד, ארוחה, משקל וניתוח תמונה.",
        ))

        input_style = """
            QLineEdit {
                padding: 12px; border: 1px solid #1E293B;
                border-radius: 8px; background-color: #111827; color: #FFFFFF;
                font-size: 14px; text-align: right;
            }
            QLineEdit:focus { border: 2px solid #06B6D4; background-color: #090D16; }
        """
        label_style = "color: #FFFFFF; font-weight: bold; font-size: 14px; text-align: right; border: none;"
        hint_style = "color: #94A3B8; font-size: 12px; font-weight: normal; text-align: right; border: none;"
        group_style = "QGroupBox { font-weight: bold; border: 1px solid #1E293B; border-radius: 8px; margin-top: 10px; padding-top: 15px; }"

        search_group = QGroupBox("חיפוש במאגר התזונה")
        search_group.setStyleSheet(group_style + " QGroupBox { color: #A855F7; }")
        search_layout = QVBoxLayout(search_group)
        search_hint = QLabel("חפשו מאכל או מאמר לפי שם. תוצאת מאכל ממלאת את טופס הארוחה.")
        search_hint.setWordWrap(True)
        search_hint.setStyleSheet(hint_style)
        search_layout.addWidget(search_hint)

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

        barcode_group = QGroupBox("שליפת מוצר לפי ברקוד")
        barcode_group.setStyleSheet(group_style + " QGroupBox { color: #14B8A6; }")
        barcode_layout = QVBoxLayout(barcode_group)
        barcode_hint = QLabel("הזינו ברקוד כדי לטעון נתוני מוצר. החיפוש ממלא את טופס הארוחה ואינו שומר אותה.")
        barcode_hint.setWordWrap(True)
        barcode_hint.setStyleSheet(hint_style)
        barcode_layout.addWidget(barcode_hint)
        barcode_row = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("לדוגמה: 3017620422003")
        self.barcode_input.setStyleSheet(input_style)
        self.btn_barcode = GlowButton("טען מוצר", base_color="#0F766E", hover_color="#0D9488", glow_color="#5EEAD4")
        self.btn_barcode.clicked.connect(self.trigger_barcode_lookup)
        barcode_row.addWidget(self.barcode_input)
        barcode_row.addWidget(self.btn_barcode)
        barcode_layout.addLayout(barcode_row)
        layout.addWidget(barcode_group)

        nutrition_group = QGroupBox("ארוחה")
        nutrition_group.setStyleSheet(group_style + " QGroupBox { color: #10B981; }")
        nut_layout = QVBoxLayout(nutrition_group)
        nut_layout.setSpacing(10)

        self.btn_camera_ai = GlowButton("ניתוח תמונת אוכל", base_color="#0F172A", hover_color="#1E293B", glow_color="#38BDF8", border_color="#06B6D4")
        self.btn_camera_ai.clicked.connect(self.simulate_camera_ai_analysis)
        nut_layout.addWidget(self.btn_camera_ai)

        self.lbl_image_status = QLabel("")
        self.lbl_image_status.setWordWrap(True)
        self.lbl_image_status.setStyleSheet(hint_style)
        nut_layout.addWidget(self.lbl_image_status)

        self.btn_open_calculator = GlowButton("מחשבון קלוריות חיצוני", base_color="#F59E0B", hover_color="#D97706", glow_color="#FDE68A")
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

        self.btn_save_meal = GlowButton("שמור ארוחה ליומן", base_color="#059669", hover_color="#10B981", glow_color="#6EE7B7")
        self.btn_save_meal.clicked.connect(self.trigger_meal_save)
        nut_layout.addWidget(self.btn_save_meal)

        layout.addWidget(nutrition_group)

        weight_group = QGroupBox("משקל")
        weight_group.setStyleSheet(group_style + " QGroupBox { color: #38BDF8; }")
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

        self.btn_save_weight = GlowButton("שמור משקל", base_color="#2563EB", hover_color="#3B82F6", glow_color="#93C5FD")
        self.btn_save_weight.clicked.connect(self.trigger_weight_save)
        w_layout.addWidget(self.btn_save_weight)

        layout.addWidget(weight_group)

        self.btn_close = GlowButton("סגור", base_color="#374151", hover_color="#4B5563", glow_color="#D1D5DB")
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

    def trigger_barcode_lookup(self) -> None:
        barcode = self.barcode_input.text().strip()
        if not barcode.isdigit() or not (8 <= len(barcode) <= 14):
            show_styled_msgbox(
                self,
                "שגיאה",
                "יש להזין ברקוד מספרי בן 8 עד 14 ספרות.",
                QMessageBox.Icon.Warning,
            )
            return

        self.btn_barcode.setText("טוען מוצר...")
        self.btn_barcode.setEnabled(False)
        QApplication.processEvents()

        result = self.dashboard_view.presenter.lookup_barcode(barcode)

        self.btn_barcode.setText("טען מוצר")
        self.btn_barcode.setEnabled(True)

        if result and result.get("status") == "success":
            self.meal_name_input.setText(str(result.get("name", "")))
            self.meal_calories_input.setText(str(result.get("calories", 0)))
            self.meal_protein_input.setText(str(result.get("protein", 0)))
            text = (
                f"שם המוצר: {result.get('name')}\n"
                f"קלוריות (ל-100 גרם): {result.get('calories')} קק\"ל\n"
                f"חלבון: {result.get('protein')} גרם\n"
                f"מקור: {result.get('source', 'OpenFoodFacts')}\n\n"
                "הערכים מולאו בטופס. שמירת הארוחה מתבצעת רק בלחיצה על שמור ארוחה ליומן."
            )
            show_styled_msgbox(self, "תוצאת OpenFoodFacts", text, QMessageBox.Icon.Information)
            return

        message = "המוצר לא נמצא ב-OpenFoodFacts."
        if isinstance(result, dict) and result.get("message"):
            message = str(result["message"])
        show_styled_msgbox(self, "חיפוש ברקוד נכשל", message, QMessageBox.Icon.Warning)

    def simulate_camera_ai_analysis(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "בחר תמונת ארוחה לניתוח", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return

        self.btn_camera_ai.setText("מנתח תמונה...")
        self.btn_camera_ai.setEnabled(False)
        self.lbl_image_status.setText("מנתח את התמונה... אפשר להמתין, המסך לא קפא.")

        self.vision_worker = VisionWorker(file_path, self.api_base_url)
        self.vision_worker.finished_signal.connect(self.on_vision_success)
        self.vision_worker.error_signal.connect(self.on_vision_error)
        self.vision_worker.start()

    def on_vision_success(self, data: dict) -> None:
        self.btn_camera_ai.setText("ניתוח תמונת אוכל")
        self.btn_camera_ai.setEnabled(True)
        self.lbl_image_status.setText("")

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
        self.btn_camera_ai.setText("ניתוח תמונת אוכל")
        self.btn_camera_ai.setEnabled(True)
        self.lbl_image_status.setText("")
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
        self.btn_save_meal.setText("שומר ארוחה...")
        presenter.log_meal(
            meal_name,
            calories,
            protein_g,
            self.on_meal_save_success,
            self.on_meal_save_error,
        )

    def on_meal_save_success(self) -> None:
        self.btn_save_meal.setEnabled(True)
        self.btn_save_meal.setText("שמור ארוחה ליומן")
        self.meal_name_input.clear()
        self.meal_calories_input.clear()
        self.meal_protein_input.clear()
        self.dashboard_view.refresh_data()
        show_styled_msgbox(self, "הצלחה", "הארוחה נשמרה ביומן.", QMessageBox.Icon.Information)

    def on_meal_save_error(self, error_message: str) -> None:
        self.btn_save_meal.setEnabled(True)
        self.btn_save_meal.setText("שמור ארוחה ליומן")
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

        self.btn_save_weight.setEnabled(False)
        self.btn_save_weight.setText("שומר משקל...")
        QApplication.processEvents()
        success = self.dashboard_view.execute_remote_weight_save(weight, weight_date)
        self.btn_save_weight.setEnabled(True)
        self.btn_save_weight.setText("שמור משקל")
        if success:
            self.weight_value_input.clear()
            self.weight_date_input.setText(date.today().isoformat())
            show_styled_msgbox(self, "הצלחה", "המשקל נשמר ביומן.", QMessageBox.Icon.Information)
