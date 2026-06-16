from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(
    title="FitTrack AI API - Lev Academic Center",
    version="1.3.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# MODELS (Pydantic)
# ==============================================================================
class MealCreate(BaseModel):
    meal_name: str
    calories: int
    protein_g: int
    username: str

class WeightCreate(BaseModel):
    weight: float
    date: str
    username: str

class WorkoutCreate(BaseModel):
    workout_type: str
    duration_minutes: int
    username: str

class LoginRequest(BaseModel):
    username: str
    password: str

class AIMessageRequest(BaseModel):
    message: str
    username: str

# ==============================================================================
# EVENT STORE (In-Memory Database - עונה על דרישה 5 לעיקרון Event Sourcing)
# ==============================================================================
db_events: Dict[str, List[Dict[str, Any]]] = {
    "Moriah": [
        {"type": "meal", "meal_name": "ארוחת בוקר חלבון", "calories": 420, "protein_g": 35},
        {"type": "weight", "weight": 75.2, "date": "2026-06-01"},
        {"type": "weight", "weight": 74.5, "date": "2026-06-07"},
        {"type": "workout", "workout_type": "ריצה", "duration_minutes": 40, "calories_burned": 450},
    ],
    "Moriya": [
        {"type": "meal", "meal_name": "סלט טונה עשיר", "calories": 380, "protein_g": 32},
        {"type": "weight", "weight": 68.0, "date": "2026-06-01"},
    ],
    "LevDeveloper": [
        {"type": "meal", "meal_name": "חזה עוף מוקפץ", "calories": 620, "protein_g": 48},
        {"type": "weight", "weight": 82.5, "date": "2026-06-01"},
    ]
}

user_profiles: Dict[str, Dict[str, int]] = {
    "Moriah": {"target_calories": 1800, "carbs_g": 180, "fat_g": 60},
    "Moriya": {"target_calories": 2000, "carbs_g": 200, "fat_g": 65},
    "LevDeveloper": {"target_calories": 2500, "carbs_g": 250, "fat_g": 75}
}

# ==============================================================================
# EXTERNAL SERVICES GATEWAY (עונה על דרישות 6, 7, 8 של הפרויקט)
# ==============================================================================
class ExternalServicesGateway:
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    OLLAMA_MODEL = "llama3"

    @classmethod
    def get_ai_consultation(cls, system_prompt: str) -> str:
        try:
            response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_MODEL,
                    "prompt": system_prompt,
                    "stream": False
                },
                timeout=120 
            )
            
            if response.status_code == 404:
                return "**שגיאת חיבור:**\nמודל ה-AI טרם הותקן ב-Docker. הריצי בטרמינל:\n`docker exec -it ollama ollama run llama3`"
            
            response.raise_for_status()
            return response.json().get("response", "שגיאה בפענוח התשובה מהמודל.")
            
        except requests.exceptions.ConnectionError:
            return "**שגיאת רשת:**\nלא ניתן להתחבר למיכל ה-Docker. אנא ודאי שהוא רץ ברקע."
        except Exception as e:
            return f"**שגיאת AI כללית:**\n{str(e)}"

    @classmethod
    def fetch_external_nutrition_fact(cls) -> str:
        try:
            res = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random", timeout=5)
            if res.status_code == 200:
                return f"הידעת? {res.json().get('text', '')}"
            return ""
        except:
            return ""

# ==============================================================================
# QUERIES & COMMANDS
# ==============================================================================
@app.get("/")
def root_status() -> Dict[str, str]:
    return {"status": "FitTrack API is running", "version": "1.3.2"}

@app.get("/users/nutrition-summary")
def nutrition_summary(username: str = Query("Moriah")) -> Dict[str, Any]:
    if username not in db_events:
        username = "Moriah"

    user_events = db_events[username]
    profile = user_profiles.get(username, user_profiles["Moriah"])

    current_calories = protein_g = steps = 0
    meals, weight_history, workouts = [], [], []

    for event in user_events:
        e_type = event.get("type")
        if e_type == "meal":
            meals.append(event)
            current_calories += event["calories"]
            protein_g += event["protein_g"]
        elif e_type == "weight":
            weight_history.append(event)
        elif e_type == "workout":
            workouts.append(event)
            current_calories -= event["calories_burned"]
        elif e_type == "steps":
            steps += event.get("steps_count", 0)

    sorted_weights = sorted(weight_history, key=lambda x: x.get("date", ""))
    weight_analysis = "📊 אין מספיק נתונים לניתוח מגמות."
    if len(sorted_weights) >= 2:
        diff = round(sorted_weights[-1]["weight"] - sorted_weights[-2]["weight"], 1)
        if diff < 0: weight_analysis = f"📉 מגמת ירידה של {abs(diff)} ק\"ג!"
        elif diff > 0: weight_analysis = f"📈 עלייה של {diff} ק\"ג."
        else: weight_analysis = f"➡️ המשקל יציב על {sorted_weights[-1]['weight']} ק\"ג."

    return {
        "current_calories": max(current_calories, 0),
        "target_calories": profile["target_calories"],
        "protein_g": protein_g,
        "carbs_g": profile["carbs_g"],
        "fat_g": profile["fat_g"],
        "meals": meals, "weight_history": weight_history,
        "workouts": workouts, "steps": steps,
        "weight_analysis": weight_analysis
    }

@app.post("/users/login")
def user_login(credentials: LoginRequest) -> Dict[str, str]:
    if credentials.username in db_events and credentials.password in ["123456", "לב2026"]:
        return {"status": "success", "username": credentials.username}
    raise HTTPException(status_code=400, detail="שם משתמש או סיסמה שגויים")

@app.post("/users/log-meal")
def log_meal(meal: MealCreate) -> Dict[str, str]:
    user = meal.username if meal.username in db_events else "Moriah"
    db_events[user].append({"type": "meal", "meal_name": meal.meal_name, "calories": meal.calories, "protein_g": meal.protein_g})
    return {"status": "success", "message": "הארוחה נשמרה ב-Event Store"}

@app.post("/users/log-weight")
def log_weight(weight_data: WeightCreate) -> Dict[str, str]:
    user = weight_data.username if weight_data.username in db_events else "Moriah"
    db_events[user].append({"type": "weight", "weight": weight_data.weight, "date": weight_data.date})
    return {"status": "success", "message": "המשקל עודכן"}

@app.post("/users/log-workout")
def log_workout(workout: WorkoutCreate) -> Dict[str, str]:
    user = workout.username if workout.username in db_events else "Moriah"
    db_events[user].append({"type": "workout", "workout_type": workout.workout_type, "duration_minutes": workout.duration_minutes, "calories_burned": workout.duration_minutes*8})
    return {"status": "success", "message": "האימון נרשם"}

@app.post("/ai/analyze-food")
def analyze_food(request: AIMessageRequest) -> Dict[str, str]:
    user = request.username if request.username in db_events else "Moriah"
    summary_data = nutrition_summary(user)
    calories_left = summary_data["target_calories"] - summary_data["current_calories"]
    external_fact = ExternalServicesGateway.fetch_external_nutrition_fact()

    # פרומפט מעודכן עם "Few-Shot" שמכריח את המודל לתבנית מדויקת ועברית טבעית
    system_prompt = f"""
    You are 'FitTrack AI', a highly professional and friendly Israeli fitness coach.
    Language: ONLY Hebrew (עברית). Never use English.

    The user is telling you what they ate or asking for a calorie calculation.
    You must calculate the TOTAL calories for their specific request.

    Data for context:
    - Leftover calories before this meal: {calories_left}
    - External fact: {external_fact}

    YOU MUST FORMAT YOUR RESPONSE EXACTLY LIKE THIS TEMPLATE:
    
    **[שם הארוחה שהמשתמש שאל עליה]** [אמוג'י מתאים]
    סה"כ קלוריות מוערך: [המספר הסופי שחישבת] קק"ל.
    
    שים/י לב: היתרה שלך להיום (לפני הארוחה) היא {calories_left} קלוריות.
    
    [משפט מוטיבציה קצר, חברותי וטבעי בעברית (למשל: בחירה מעולה! או: פצצה של חלבון!)]

    Now, answer the user request EXACTLY in the format above:
    User: {request.message}
    """

    response_text = ExternalServicesGateway.get_ai_consultation(system_prompt)
    return {"response": response_text}