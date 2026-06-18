import requests
from PySide6.QtCore import QObject, QThread, Signal

API_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 60  # חזרנו ל-60 שניות, זה מספיק זמן

# ==========================================
# 1. יצירת Worker שרץ ברקע ולא תוקע את המסך
# ==========================================
class LoginWorker(QThread):
    # החוט ידווח למסך הראשי כשיסיים, בהצלחה או בשגיאה
    success_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            response = requests.post(
                f"{API_BASE_URL}/users/login", 
                json={"username": self.username, "password": self.password}, 
                timeout=TIMEOUT_SECONDS
            )
            if response.status_code == 200 and response.json().get("status") == "success":
                self.success_signal.emit(response.json().get("username", self.username))
            else:
                self.error_signal.emit("שם משתמש או סיסמה שגויים. נסו שוב.")
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("שרת ה-Backend כבוי. אנא ודאי שהפעלת את השרת בטרמינל נפרד.")
        except requests.exceptions.Timeout:
            self.error_signal.emit("הבקשה לשרת נקטעה (Timeout). המסד מתעורר לאט, אנא נסי שוב בעוד דקה.")
        except Exception as e:
            self.error_signal.emit(f"שגיאה בלתי צפויה: {e}")

# ==========================================
# 2. ה-Presenter שמנהל את הלוגיקה
# ==========================================
class FitTrackPresenter(QObject):
    def __init__(self):
        super().__init__()
        self.active_user = None
        self.dashboard_view = None
        self.login_view = None
        self.login_worker = None

    def set_views(self, login_view, dashboard_view):
        self.login_view = login_view
        self.dashboard_view = dashboard_view

    def login(self, username, password):
        if self.login_view:
            # הפיכת הכפתור לאפור ושינוי הטקסט בזמן ההמתנה
            self.login_view.login_button.setText("ממתין לשרת... ⏳")
            self.login_view.login_button.setEnabled(False)

        # הפעלת בקשת ה-HTTP בתהליך רקע (כדי למנוע מסך קפוא)
        self.login_worker = LoginWorker(username, password)
        self.login_worker.success_signal.connect(self.on_login_worker_success)
        self.login_worker.error_signal.connect(self.on_login_worker_error)
        self.login_worker.start()

    def on_login_worker_success(self, username):
        self.active_user = username
        if self.login_view:
            self.login_view.login_button.setText("התחברות למערכת")
            self.login_view.login_button.setEnabled(True)
            self.login_view.on_login_success()

    def on_login_worker_error(self, error_message):
        if self.login_view:
            self.login_view.login_button.setText("התחברות למערכת")
            self.login_view.login_button.setEnabled(True)
            self.login_view.on_login_error(error_message)

    def fetch_dashboard_data(self):
        if not self.active_user:
            return None
        try:
            response = requests.get(
                f"{API_BASE_URL}/queries/nutrition-summary?username={self.active_user}", 
                timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except Exception as error:
            print(f"שגיאה בהתחברות ל-API: {error}")
            return None

    def log_meal(self, meal_name, calories, protein_g):
        try:
            response = requests.post(
                f"{API_BASE_URL}/commands/log-meal",
                json={"meal_name": meal_name, "calories": calories, "protein_g": protein_g, "username": self.active_user},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            self.dashboard_view.refresh_data()
            return True
        except Exception as error:
            self.dashboard_view.show_error(f"שמירת הארוחה נכשלה:\n{error}")
            return False

    def log_weight(self, weight, weight_date):
        try:
            response = requests.post(
                f"{API_BASE_URL}/commands/log-weight",
                json={"weight": weight, "date": weight_date, "username": self.active_user},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            self.dashboard_view.refresh_data()
            return True
        except Exception as error:
            self.dashboard_view.show_error(f"עדכון המשקל נכשל:\n{error}")
            return False

    def log_workout(self, workout_type, duration_minutes):
        try:
            response = requests.post(
                f"{API_BASE_URL}/commands/log-workout",
                json={"workout_type": workout_type, "duration_minutes": duration_minutes, "username": self.active_user},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            self.dashboard_view.refresh_data()
            return True
        except Exception as error:
            self.dashboard_view.show_error(f"רישום האימון נכשל:\n{error}")
            return False

    def logout(self):
        self.active_user = None