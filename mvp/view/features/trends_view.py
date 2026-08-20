"""Trends and workout-entry feature window."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QLineEdit, QMessageBox, QVBoxLayout, QWidget

from mvp.view.features.ui_components import GlowButton, make_page_header, show_styled_msgbox

class TrendsAndWorkoutsWindow(QWidget):
    def __init__(self, dashboard_view: "DashboardView") -> None:
        super().__init__()
        self.dashboard_view = dashboard_view
        self.setWindowTitle("FitTrack AI — מגמות ואימונים")
        self.resize(600, 650)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #0A0F1D; border: 2px solid #06B6D4; border-radius: 12px;")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(16)

        layout.addWidget(make_page_header(
            "מגמות ואימונים",
            "כאן רואים מגמת משקל ורושמים אימון חדש.",
        ))

        self.trends_box = QGroupBox("מגמת משקל")
        self.trends_box.setStyleSheet("QGroupBox { font-weight: bold; color: #38BDF8; border: 1px solid #1E293B; border-radius: 8px; padding-top: 15px; }")
        tb_layout = QVBoxLayout(self.trends_box)

        self.lbl_analysis_text = QLabel("אין עדיין מספיק שקילות להצגת מגמה.")
        self.lbl_analysis_text.setWordWrap(True)
        self.lbl_analysis_text.setStyleSheet("font-size: 14px; color: #FFFFFF; line-height: 22px; border: none; background: transparent; padding: 5px;")
        tb_layout.addWidget(self.lbl_analysis_text)
        layout.addWidget(self.trends_box)

        workout_group = QGroupBox("רישום אימון")
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

        self.btn_save_workout = GlowButton("שמור אימון", base_color="#E11D48", hover_color="#F43F5E", glow_color="#FDA4AF")
        self.btn_save_workout.clicked.connect(self.trigger_workout_save)
        w_layout.addWidget(self.btn_save_workout)
        layout.addWidget(workout_group)

        self.btn_close = GlowButton("סגור", base_color="#374151", hover_color="#4B5563", glow_color="#D1D5DB")
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

        self.btn_save_workout.setEnabled(False)
        self.btn_save_workout.setText("שומר אימון...")
        success = self.dashboard_view.execute_remote_workout_save(w_type, duration)
        self.btn_save_workout.setEnabled(True)
        self.btn_save_workout.setText("שמור אימון")
        if success:
            self.workout_type_input.clear()
            self.workout_duration_input.clear()
            show_styled_msgbox(self, "הצלחה", "האימון נשמר ביומן.", QMessageBox.Icon.Information)

    def update_trends_text(self, text: str) -> None:
        self.lbl_analysis_text.setText(text)
