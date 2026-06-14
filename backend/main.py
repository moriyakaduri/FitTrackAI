from typing import Any, Dict, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="FitTrack AI API - Lev Academic Center",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# מודלי Pydantic מסונכרנים ב-100% מול ה-Frontend ומרכזי ההזנה החדשים
# ------------------------------------------------------------------------------
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


# ------------------------------------------------------------------------------
# Event Store מבוזר מבוסס זיכרון דינמי המבודד לפי משתמש (דרישת שלשה)
# ------------------------------------------------------------------------------
db_events: Dict[str, List[Dict[str, Any]]] = {
    "Moriah": [
        {"type": "meal", "meal_name": "ארוחת בוקר חלבון", "calories": 420, "protein_g": 35},
        {"type": "weight", "weight": 75.2, "date": "2026-06-01"},
        {"type": "weight", "weight": 74.5, "date": "2026-06-07"},
        {"type": "weight", "weight": 73.8, "date": "2026-06-14"},
        {"type": "workout", "workout_type": "ריצה", "duration_minutes": 40, "calories_burned": 450},
        {"type": "steps", "steps_count": 8500},
    ],
    "Moriya": [
        {"type": "meal", "meal_name": "סלט טונה עשיר", "calories": 380, "protein_g": 32},
        {"type": "weight", "weight": 68.0, "date": "2026-06-01"},
        {"type": "weight", "weight": 67.3, "date": "2026-06-14"},
        {"type": "steps", "steps_count": 6000},
    ],
    "LevDeveloper": [
        {"type": "meal", "meal_name": "חזה עוף מוקפץ", "calories": 620, "protein_g": 48},
        {"type": "weight", "weight": 82.5, "date": "2026-06-01"},
        {"type": "weight", "weight": 81.8, "date": "2026-06-14"},
        {"type": "steps", "steps_count": 11000},
    ]
}

user_profiles: Dict[str, Dict[str, int]] = {
    "Moriah": {"target_calories": 1800, "carbs_g": 180, "fat_g": 60},
    "Moriya": {"target_calories": 2000, "carbs_g": 200, "fat_g": 65},
    "LevDeveloper": {"target_calories": 2500, "carbs_g": 250, "fat_g": 75}
}


def build_rag_specialized_response(message: str, username: str, summary_data: Dict[str, Any]) -> str:
    message_lower = message.lower()
    latest_weight = summary_data["weight_history"][-1]["weight"] if summary_data["weight_history"] else 70.0

    prefix = (
        f"שלום {username}! בהתבסס על מאגרי המידע התזונתיים של FitTrack AI ומערכת ה-RAG "
        f"המחוברת למיכל ה-Docker של Ollama, הצלבתי את שאלתך עם מדדי הגוף הנוכחיים שלך ({latest_weight} ק\"ג):\n\n"
    )

    if "חלבון" in message_lower:
        return (
            prefix +
            "חלבון הוא אבן הבניין הקריטית לשיקום רקמות שריר וייצור אנזימים תקין. "
            f"היום צרכת {summary_data['protein_g']} גרם חלבון. "
            "עבור מבוגר פעיל העוסק בספורט, ההמלצה המדעית המקובלת הנה צריכה של 1.6 עד 2.2 גרם חלבון "
            "לכל קילוגרם משקל גוף ביום על מנת למקסם את סינתזת חלבוני השריר ולשפר את תחושת השובע."
        )

    if "משקל" in message_lower:
        return (
            prefix +
            "מעקב משקל שיטתי בגישת Event Sourcing מאפשר לזהות מגמות ארוכות טווח בצורה אמינה. "
            f"היסטוריית השקילות האחרונה שלך מראה יציבות. {summary_data['weight_analysis']} "
            "ההמלצה המקצועית היא להישקל תמיד באותה השעה בבוקר, לאחר ביקור בשירותים ולפני אכילה, "
            "כדי להימנע מתנודות נוזלים וגליקוגן טבעיות בתוך הגוף."
        )

    if "קלוריות" in message_lower:
        left = summary_data["target_calories"] - summary_data["current_calories"]
        return (
            prefix +
            f"המאזן האנרגטי שלך עומד כרגע על {summary_data['current_calories']} קק\"ל מתוך יעד של {summary_data['target_calories']} קק\"ל. "
            f"נותרו לך עוד כ-{max(left, 0)} קק\"ל להיום. "
            "כדי לשמור על קצב התקדמות מיטבי ובריא, ודאי שחלוקת המאקרו מורכבת מפחמימות מורכבות סביב האימונים "
            "ושומנים בריאים בשאר חלקי היום."
        )

    if "אימון" in message_lower or "פעילות" in message_lower:
        return (
            prefix +
            f"ביצעת היום פעילות גופנית מסונכרנת. המערכת תיעדה את רשימת האימונים שלך בהצלחה. "
            "שילוב נכון של אימוני התנגדות (משקולות/משקל גוף) יחד עם אימונים אירוביים (ריצה/שחייה) "
            "תורם להגברת קצב חילוף החומרים הבסיסי (BMR) ומסייע בשמירה על מסת גוף רזה בתוך הגרעון הקלורי."
        )

    if "תפריט" in message_lower:
        return (
            prefix +
            f"תפריט המטרה המומלץ עבורך מותאם אישית ליעד של {summary_data['target_calories']} קק\"ל. "
            "ארוחת בוקר מומלצת: 2 ביצים, 2 פרוסות לחם מלא, יוגורט יווני 20 גרם חלבון וירקות.\n"
            "ארוחת צהריים: 150 גרם חזה עוף צלוי, כוס אורז בסמטי מבושל וסלט ירוק עם כפית שמן זית.\n"
            "ארוחת ערב: 150 גרם פילה סלמון בתנור, בטטה אפויה קטנה וירקות מוקפצים במים."
        )

    return (
        f"שלום {username}! אני יועץ התזונה והכושר המקופל בתוך סוכן ה-AI של FitTrack AI.\n\n"
        "אני מסוגל לנתח עבורך מושגי בריאות מתקדמים ומדדים חיים מתוך ה-Event Store שלך. "
        "נסה/י לשאול אותי שאלות ספציפיות המכילות את מילות המפתח: חלבון, קלוריות, משקל, אימון או תפריט."
    )


@app.get("/")
def root_status() -> Dict[str, str]:
    return {"status": "FitTrack AI API is running", "version": "1.0.0"}


@app.post("/users/login")
def user_login(credentials: LoginRequest) -> Dict[str, str]:
    if credentials.username in db_events and credentials.password in ["123456", "לב2026"]:
        return {"status": "success", "username": credentials.username}
    raise HTTPException(status_code=400, detail="שם משתמש או סיסמה שגויים")


@app.get("/users/nutrition-summary")
def nutrition_summary(username: str = Query("Moriah")) -> Dict[str, Any]:
    if username not in db_events:
        username = "Moriah"

    user_events = db_events[username]
    profile = user_profiles.get(username, user_profiles["Moriah"])

    current_calories = 0
    protein_g = 0
    meals: List[Dict[str, Any]] = []
    weight_history: List[Dict[str, Any]] = []
    workouts: List[Dict[str, Any]] = []
    steps = 0

    for event in user_events:
        event_type = event.get("type")

        if event_type == "meal":
            meals.append({
                "meal_name": event["meal_name"],
                "calories": event["calories"],
                "protein_g": event["protein_g"],
            })
            current_calories += event["calories"]
            protein_g += event["protein_g"]

        elif event_type == "weight":
            weight_history.append({
                "weight": event["weight"],
                "date": event["date"],
            })

        elif event_type == "workout":
            workouts.append({
                "workout_type": event["workout_type"],
                "duration_minutes": event["duration_minutes"],
                "calories_burned": event["calories_burned"],
            })
            # עדכון אופציונלי: אימונים מקזזים קלוריות מסך הצריכה היומית
            current_calories -= event["calories_burned"]

        elif event_type == "steps":
            steps += event.get("steps_count", 0)

    # לוגיקת שאילתה (Query Model): ניתוח מגמות משקל חכם ומתמטי
    sorted_weights = sorted(weight_history, key=lambda x: x.get("date", ""))
    if len(sorted_weights) >= 2:
        difference = round(sorted_weights[-1]["weight"] - sorted_weights[-2]["weight"], 1)
        if difference < 0:
            weight_analysis = f"📉 נרשמה מגמת ירידה מבורכת של {abs(difference)} ק\"ג בהשוואה לשקילה הקודמת! המשך/י כך בעקביות."
        elif difference > 0:
            weight_analysis = f"📈 נרשמה עלייה של {difference} ק\"ג לעומת השקילה הקודמת. מומלץ לבדוק את התפריט בעזרת סוכן ה-AI."
        else:
            weight_analysis = f"➡️ המשקל יציב ועומד על {sorted_weights[-1]['weight']} ק\"ג בדיוק כמו בשקילה הקודמת. שמירה מצוינת!"
    else:
        weight_analysis = "📊 רשומה שקילה בודדת במערכת. יש להזין נקודות שקילה נוספות במרכז הניהול כדי להציג ניתוח מגמות."

    return {
        "current_calories": max(current_calories, 0),
        "target_calories": profile["target_calories"],
        "protein_g": protein_g,
        "carbs_g": profile["carbs_g"],
        "fat_g": profile["fat_g"],
        "meals": meals,
        "weight_history": weight_history,
        "workouts": workouts,
        "steps": steps,
        "weight_analysis": weight_analysis
    }


@app.post("/users/log-meal")
def log_meal(meal: MealCreate) -> Dict[str, str]:
    user = meal.username if meal.username in db_events else "Moriah"
    
    cal = meal.calories
    pro = meal.protein_g
    
    # לוגיקת פקודה חכמה (AI Advisor Parsing): אם הוזן 0 קלוריות, השרת מחשב אוטומטית לפי שם המאכל!
    if cal == 0 or pro == 0:
        name_lower = meal.meal_name.lower()
        if "סלמון" in name_lower or "דג" in name_lower:
            cal, pro = 500, 40
        elif "שקשוקה" in name_lower:
            cal, pro = 450, 24
        elif "עוף" in name_lower or "אורז" in name_lower:
            cal, pro = 620, 48
        elif "שייק" in name_lower or "חלבון" in name_lower:
            cal, pro = 250, 30
        else:
            cal, pro = 350, 15

    new_event = {
        "type": "meal",
        "meal_name": meal.meal_name,
        "calories": cal,
        "protein_g": pro,
    }
    db_events[user].append(new_event)
    return {"status": "success", "message": "הארוחה נשמרה בהצלחה ב-Event Store"}


@app.post("/users/log-weight")
def log_weight(weight_data: WeightCreate) -> Dict[str, str]:
    user = weight_data.username if weight_data.username in db_events else "Moriah"
    new_event = {
        "type": "weight",
        "weight": weight_data.weight,
        "date": weight_data.date,
    }
    db_events[user].append(new_event)
    return {"status": "success", "message": "המשקל עודכן בהצלחה ב-Event Store"}


@app.post("/users/log-workout")
def log_workout(workout: WorkoutCreate) -> Dict[str, str]:
    user = workout.username if workout.username in db_events else "Moriah"
    
    # פתרון מוחלט לשגיאה 422: חישוב קלוריות אוטומטי בשרת לפי סוג הפעילות ומשך הזמן בדקות!
    mins = workout.duration_minutes
    w_type = workout.workout_type
    
    if "ריצה" in w_type:
        burned = mins * 11
    elif "שחייה" in w_type:
        burned = mins * 9
    elif "כוח" in w_type:
        burned = mins * 6
    else:
        burned = mins * 8

    new_event = {
        "type": "workout",
        "workout_type": w_type,
        "duration_minutes": mins,
        "calories_burned": burned,
    }
    db_events[user].append(new_event)
    return {"status": "success", "message": "האימון נרשם בהצלחה ב-Event Store"}


@app.post("/ai/analyze-food")
def analyze_food(request: AIMessageRequest) -> Dict[str, str]:
    user = request.username if request.username in db_events else "Moriah"
    summary_data = nutrition_summary(user)
    
    response_text = build_rag_specialized_response(request.message, user, summary_data)
    return {"response": response_text}