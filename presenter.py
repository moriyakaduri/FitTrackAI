"""MVP presenter coordinating desktop views with the FitTrackAI HTTP API."""

import requests
from PySide6.QtCore import QObject, QThread, Signal

API_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 60


class LoginWorker(QThread):
    success_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            response = requests.post(
                f"{API_BASE_URL}/users/login",
                json={"username": self.username, "password": self.password},
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code == 200 and response.json().get("status") == "success":
                self.success_signal.emit(response.json().get("username", self.username))
            else:
                self.error_signal.emit("שם משתמש או סיסמה שגויים. נסו שוב.")
        except requests.exceptions.ConnectionError:
            self.error_signal.emit(
                "שרת ה-Backend כבוי. אנא ודאי שהפעלת את השרת בטרמינל נפרד."
            )
        except requests.exceptions.Timeout:
            self.error_signal.emit(
                "הבקשה לשרת נקטעה (Timeout). המסד מתעורר לאט, אנא נסי שוב בעוד דקה."
            )
        except Exception as error:
            self.error_signal.emit(f"שגיאה בלתי צפויה: {error}")


class SaveMealWorker(QThread):
    success_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, username: str, meal_name: str, calories: int, protein_g: int):
        super().__init__()
        self.username = username
        self.meal_name = meal_name
        self.calories = calories
        self.protein_g = protein_g

    def run(self):
        try:
            response = requests.post(
                f"{API_BASE_URL}/commands/log-meal",
                json={
                    "meal_name": self.meal_name,
                    "calories": self.calories,
                    "protein_g": self.protein_g,
                    "username": self.username,
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            self.success_signal.emit()
        except Exception as error:
            self.error_signal.emit(str(error))


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

    def login(self, username: str, password: str):
        if self.login_view:
            self.login_view.login_button.setText("ממתין לשרת... ⏳")
            self.login_view.login_button.setEnabled(False)

        self.login_worker = LoginWorker(username, password)
        self.login_worker.success_signal.connect(self.on_login_worker_success)
        self.login_worker.error_signal.connect(self.on_login_worker_error)
        self.login_worker.start()

    def on_login_worker_success(self, username: str):
        self.active_user = username
        if self.login_view:
            self.login_view.login_button.setText("התחברות למערכת")
            self.login_view.login_button.setEnabled(True)
            self.login_view.on_login_success()

    def on_login_worker_error(self, error_message: str):
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
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except Exception as error:
            print(f"API error: {error}")
            return None

    def fetch_meal_details(self, event_id: int):
        if not self.active_user:
            return None
        try:
            response = requests.get(
                f"{API_BASE_URL}/queries/meal-details",
                params={"event_id": event_id, "username": self.active_user},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except Exception as error:
            print(f"Meal details error: {error}")
            return None

    def search_data(self, query: str):
        try:
            response = requests.get(
                f"{API_BASE_URL}/queries/search",
                params={"q": query},
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as error:
            print(f"Search error: {error}")
            return None

    def lookup_barcode(self, barcode: str):
        try:
            response = requests.get(
                f"{API_BASE_URL}/queries/barcode",
                params={"barcode": barcode},
                timeout=TIMEOUT_SECONDS,
            )
            payload = response.json() if response.content else {}
            if response.status_code == 200:
                return payload
            return {
                "status": "error",
                "message": payload.get("detail", "חיפוש הברקוד נכשל."),
            }
        except Exception as error:
            return {"status": "error", "message": f"חיפוש הברקוד נכשל: {error}"}

    def log_meal(self, meal_name: str, calories: int, protein_g: int):
        try:
            response = requests.post(
                f"{API_BASE_URL}/commands/log-meal",
                json={
                    "meal_name": meal_name,
                    "calories": calories,
                    "protein_g": protein_g,
                    "username": self.active_user,
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            self.dashboard_view.refresh_data()
            return True
        except Exception as error:
            self.dashboard_view.show_error(f"שמירת הארוחה נכשלה:\n{error}")
            return False

    def log_weight(self, weight: float, weight_date: str):
        try:
            response = requests.post(
                f"{API_BASE_URL}/commands/log-weight",
                json={
                    "weight": weight,
                    "date": weight_date,
                    "username": self.active_user,
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            self.dashboard_view.refresh_data()
            return True
        except Exception as error:
            self.dashboard_view.show_error(f"עדכון המשקל נכשל:\n{error}")
            return False

    def log_workout(self, workout_type: str, duration_minutes: int):
        try:
            response = requests.post(
                f"{API_BASE_URL}/commands/log-workout",
                json={
                    "workout_type": workout_type,
                    "duration_minutes": duration_minutes,
                    "username": self.active_user,
                },
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