"""Shared visual components used by desktop feature views."""

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QMessageBox,
    QPushButton, QWidget,
)

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
