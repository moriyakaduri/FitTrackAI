"""Desktop composition shell and dashboard view for the feature-sliced MVP UI."""

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

from mvp.model.api import API_BASE_URL
from mvp.presenter import FitTrackPresenter
from mvp.view.features.ai_advisor_view import AIAgentView
from mvp.view.features.auth_view import LoginView
from mvp.view.features.data_entry_view import DataEntryWindow
from mvp.view.features.motivation_view import MotivationWindow
from mvp.view.features.trends_view import TrendsAndWorkoutsWindow
from mvp.view.features.ui_components import (
    GlowButton, HoverCard, MealDetailsDialog, play_fade_in_animation,
    show_styled_msgbox,
)

# =====================================================================
# רכיבי UI אינטראקטיביים חכמים 
# =====================================================================



# =====================================================================





# --- Workers לניהול תקשורת ברקע ---








# =====================================================================
# מסך התחברות עם וידאו רקע
# =====================================================================
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

        sidebar_title = QLabel("תפריט")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        sidebar_title.setStyleSheet("color: #38BDF8; font-size: 20px; font-weight: bold; background: transparent; border: none;")
        sidebar_layout.addWidget(sidebar_title)

        self.btn_nav_data_entry = GlowButton("הזנת נתונים", base_color="#0284C7", hover_color="#0EA5E9", glow_color="#7DD3FC", align="right", border_color="#0369A1")
        self.btn_nav_data_entry.clicked.connect(self.app_controller.open_data_entry_window)
        sidebar_layout.addWidget(self.btn_nav_data_entry)

        self.btn_nav_trends = GlowButton("מגמות ואימונים", base_color="#9333EA", hover_color="#A855F7", glow_color="#D8B4FE", align="right", border_color="#7E22CE")
        self.btn_nav_trends.clicked.connect(self.app_controller.open_trends_window)
        sidebar_layout.addWidget(self.btn_nav_trends)

        ai_button = GlowButton("יועץ AI", base_color="#1F2937", hover_color="#374151", glow_color="#9CA3AF", align="right", border_color="#111827")
        ai_button.clicked.connect(self.app_controller.show_ai_view)
        sidebar_layout.addWidget(ai_button)

        self.btn_open_motivation = GlowButton("מוטיבציה", base_color="#312E81", hover_color="#4338CA", glow_color="#A5B4FC", align="right", border_color="#1E1B4B")
        self.btn_open_motivation.clicked.connect(self.app_controller.open_motivation_window)
        sidebar_layout.addWidget(self.btn_open_motivation)

        sidebar_layout.addStretch()

        logout_button = GlowButton("התנתקות", base_color="#991B1B", hover_color="#DC2626", glow_color="#FCA5A5", align="center")
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

        self.welcome_label = QLabel("ברוכים הבאים")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.welcome_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: 800; 
            color: #E0F2FE; 
            background: transparent;
            padding: 5px;
        """)
        content_layout.addWidget(self.welcome_label)

        self.welcome_hint = QLabel("הזנת ארוחות, חיפוש במאגר וברקוד נמצאים בחלון הזנת נתונים.")
        self.welcome_hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.welcome_hint.setWordWrap(True)
        self.welcome_hint.setStyleSheet("color: #94A3B8; font-size: 13px; background: transparent; border: none;")
        content_layout.addWidget(self.welcome_hint)

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
        
        charts_title = QLabel("גרפים ומדדים יומיים")
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
        
        table_title = QLabel("יומן ארוחות היום")
        table_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        table_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #94A3B8; background: transparent; border: none;")
        table_layout.addWidget(table_title)

        self.lbl_meals_empty = QLabel("אין ארוחות להיום. הוסיפו ארוחה מחלון הזנת נתונים. לחיצה כפולה על שורה מציגה פרטים.")
        self.lbl_meals_empty.setWordWrap(True)
        self.lbl_meals_empty.setStyleSheet("color: #64748B; font-size: 13px; background: transparent; border: none;")
        table_layout.addWidget(self.lbl_meals_empty)

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
            self.welcome_label.setText(f"שלום {self.presenter.active_user}")

        data = self.presenter.fetch_dashboard_data()
        if not data:
            return

        meals = data.get("meals", [])
        self.meals_data = meals
        self.meals_table.setRowCount(len(meals))
        self.lbl_meals_empty.setVisible(len(meals) == 0)
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


class FitTrackApplication(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.presenter = FitTrackPresenter() 
        
        self.setWindowTitle("FitTrack AI — המרכז האקדמי לב")
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
            self.data_entry_window = DataEntryWindow(self.dashboard_view, API_BASE_URL)
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