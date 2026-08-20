"""Authentication feature view."""

import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QMessageBox, QVBoxLayout, QWidget
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtMultimediaWidgets import QVideoWidget

from features.ui_components import (
    GlowButton, apply_neon_shadow, play_card_fly_animation, show_styled_msgbox,
)
from presenter import FitTrackPresenter

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

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        video_path = os.path.join(repo_root, "runner.mp4")
        if os.path.exists(video_path):
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
