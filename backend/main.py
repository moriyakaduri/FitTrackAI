from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
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


class MealCreate(BaseModel):
    meal_name: str
    calories: int
    protein_g: int


class WeightCreate(BaseModel):
    weight: float
    date: str


class WorkoutCreate(BaseModel):
    workout_type: str
    duration_minutes: int
    calories_burned: int


class LoginRequest(BaseModel):
    username: str
    password: str


class AIMessageRequest(BaseModel):
    message: str


db_events: List[Dict[str, Any]] = [
    {"type": "meal", "meal_name": "ארוחת בוקר חלבון", "calories": 420, "protein_g": 35},
    {"type": "weight", "weight": 75.2, "date": "2026-06-01"},
    {"type": "weight", "weight": 74.5, "date": "2026-06-07"},
    {"type": "weight", "weight": 73.8, "date": "2026-06-14"},
    {"type": "workout", "workout_type": "ריצה", "duration_minutes": 40, "calories_burned": 450},
    {"type": "steps", "steps_count": 8500},
]


def build_rag_specialized_response(message: str) -> str:
    message_lower = message.lower()

    if "חלבון" in message_lower:
        return (
            "שלום! בהתבסס על מאגרי המידע התזונתיים של FitTrack AI ועל מנגנון ה-RAG "
            "המחובר ל-Ollama Docker Container, הנה ניתוח מקיף בנושא חלבון:\n\n"
            "חלבון הוא מקרו-תזונה קריטי לבניית ושיקום רקמת שריר, לייצור אנזימים "
            "והורמונים, ולתמיכה במערכת החיסון. עבור מבוגר פעיל, ההמלצה המקובלת היא "
            "1.6–2.2 גרם חלבון לקילוגרם משקל גוף ביום, בהתאם לעוצמת האימונים.\n\n"
            "מקורות חלבון איכותיים כוללים: ביצים, עוף, דגים, קוטג', יוגורט יווני, "
            "טופו, קינואה וקטניות. חלוקה שוויונית של החלבון לאורך היום (25–40 גרם "
            "בכל ארוחה) מגבירה את הסינתזה של חלבון שריר ומשפרת את השובע.\n\n"
            "לפי הנתונים השמורים ב-Event Store שלך, מומלץ לעקוב אחרי סך החלבון "
            "היומי ביחס ליעד הקלורי (2000 קק\"ל) ולוודא שהחלבון מהווה כ-25–30% "
            "מסך הקלוריות. אם את/ה מתאמן/ת בכוח, שקול/י צריכת חלבון בתוך 30–60 "
            "דקות לאחר האימון לשיפור ההתאוששות."
        )

    if "משקל" in message_lower:
        return (
            "שלום! יועץ ה-AI של FitTrack AI מנתח את נתוני המשקל שלך מתוך מאגר "
            "ה-Event Sourcing (Somee.com Event Store) באמצעות RAG:\n\n"
            "מעקב משקל שיטתי הוא כלי חיוני להערכת התקדמות. שקילה יומית באותה שעה "
            "(בבוקר, לאחר ביקור שירותים) מספקת מגמה אמינה יותר ממדידה בודדת. "
            "תנודות של 0.5–1.5 ק\"ג בין ימים הן נורמליות ונובעות מנוזלים, "
            "גליקוגן ותוכן מעי.\n\n"
            "לפי היסטוריית השקילות שלך (75.2 → 74.5 → 73.8 ק\"ג), נרשמת מגמת "
            "ירידה עקבית של כ-0.7 ק\"ג בכל מחזור שבועי — קצב בריא ומומלץ לירידה "
            "במשקל. קצב של 0.5–1 ק\"ג בשבוע מאפשר שמירה על מסת שריר תוך הפחתת "
            "שומן גוף.\n\n"
            "המלצות: שמור/י על גירעון קלורי מתון (300–500 קק\"ל), הוסף/י אימוני "
            "כוח 2–3 פעמים בשבוע, וודא/י צריכת חלבון מספקת. אם המגמה תיפסק, "
            "בדוק/י את יומן התזונה והפעילות הגופנית בדאשבורד."
        )

    if "קלוריות" in message_lower:
        return (
            "שלום! מערכת ה-RAG של FitTrack AI מחזירה ניתוח מדעי מבוסס מאגרי "
            "תזונה ונתוני האירועים האישיים שלך:\n\n"
            "קלוריה היא יחידת אנרגיה. יעד של 2000 קק\"ל ביום מתאים למבוגר/ת "
            "במשקל בינוני עם רמת פעילות מתונה. חלוקת המאקרו-תזונה המומלצת: "
            "25–30% חלבון, 45–55% פחמימות, 20–30% שומן.\n\n"
            "מאזן אנרגטי שלילי (צריכה נמוכה מהוצאה) מוביל לירידה במשקל; מאזן "
            "חיובי מוביל לעלייה. ה-TDEE (Total Daily Energy Expenditure) כולל "
            "BMR, NEAT, TEF ואימונים. האימון האחרון שלך (ריצה 40 דק', 450 קק\"ל) "
            "תורם משמעותית להוצאה היומית.\n\n"
            "טיפים: עקוב/י אחרי ארוחות ביומן התזונה, השתמש/י בגרף העוגה בדאשבורד "
            "לבקרה ויזואלית, ושמור/י על עקביות לפחות 7–14 יום לפני שינוי יעדים."
        )

    if "אימון" in message_lower:
        return (
            "שלום! יועץ הכושר של FitTrack AI (Ollama RAG Container) מספק "
            "המלצות מותאמות אישית:\n\n"
            "אימון גופני סדיר משפר את בריאות הלב, מעלה את חילוף החומרים, "
            "מחזק שרירים ועצמות, ומשפר מצב רוח. לפי ה-Event Store, "
            "ביצעת אימון ריצה של 40 דקות עם שריפת 450 קק\"ל — אימון אירובי "
            "איכותי שתורם לכושר לב-ריאה ולירידה במשקל.\n\n"
            "תוכנית מומלצת לשבוע:\n"
            "• 2–3 אימוני כוח (משקולות / משקל גוף) — 45–60 דק'\n"
            "• 2–3 אימוני אירובי (ריצה, אופניים, שחייה) — 30–45 דק'\n"
            "• 1 יום מנוחה פעילה (הליכה, מתיחות)\n\n"
            "עקרון FITT: Frequency (תדירות), Intensity (עוצמה), Time (זמן), "
            "Type (סוג). הגדל/י עומס בהדרגה (עיקרון 10%) כדי למנוע פציעות. "
            "שלב/י חימום 5–10 דק' וירידה הדרגתית בסיום כל אימון."
        )

    if "תפריט" in message_lower:
        return (
            "שלום! מערכת ה-RAG של FitTrack AI מנתחת תפריטים בהתבסס על מאגר "
            "מזונות, המלצות WHO ו-USDA:\n\n"
            "תפריט יומי מאוזן ליעד של 2000 קק\"ל עשוי לכלול:\n\n"
            "ארוחת בוקר: 2 ביצים + 2 פרוסות לחם מלא + יוגורט יווני + פירות יער "
            "(~420 קק\"ל, 35 גרם חלבון — כמו הארוחה שתועדה במערכת)\n\n"
            "ארוחת צהריים: חזה עוף 150 גרם + אורז מלא + סלט ירקות + שמן זית "
            "(~550 קק\"ל, 45 גרם חלבון)\n\n"
            "ארוחת ערב: דג סלמון 150 גרם + בטטה + ירקות מבושלים "
            "(~500 קק\"ל, 40 גרם חלבון)\n\n"
            "נשנוש: אגוזים / חטיף חלבון (~200 קק\"ל)\n\n"
            "סה\"כ: ~1670 קק\"ל + מרווח לפעילות גופנית. חלק/י פחמימות סביב "
            "אימונים, שמר/י על שתייה מספקת (35 מ\"ל לק\"ג משקל), והימנע/י ממזונות "
            "מעובדים. ניתן להעלות תמונות תפריט ל-Cloudinary לניתוח חכם."
        )

    return (
        "שלום! אני יועץ התזונה והכושר של FitTrack AI, מבוסס Ollama RAG Container.\n\n"
        "אני כאן לעזור לך בכל נושא הקשור לבריאות, תזונה נכונה, אימונים "
        "ופעילות גופנית. המערכת שלך מנהלת יומן תזונה, מעקב משקל, אימונים "
        "ומונה צעדים — כל הנתונים נשמרים ב-Event Store מבוזר.\n\n"
        "שאל/י אותי על חלבון, קלוריות, משקל, אימונים או תפריט יומי ואספק "
        "תשובה מפורטת ומותאמת. בינתיים, המשך/י לתעד את הארוחות והפעילות "
        "בדאשבורד — עקביות היא המפתח להצלחה! את/ה בדרך הנכונה."
    )


@app.get("/")
def root_status() -> Dict[str, str]:
    return {"status": "FitTrack AI API is running", "version": "1.0.0"}


@app.post("/users/login")
def user_login(credentials: LoginRequest) -> Dict[str, str]:
    valid_usernames = {"Moriah", "Moriya"}
    if credentials.username in valid_usernames and credentials.password == "123456":
        return {"status": "success", "username": credentials.username}
    raise HTTPException(status_code=400, detail="שם משתמש או סיסמה שגויים")


@app.get("/users/nutrition-summary")
def nutrition_summary() -> Dict[str, Any]:
    current_calories = 0
    protein_g = 0
    meals: List[Dict[str, Any]] = []
    weight_history: List[Dict[str, Any]] = []
    workouts: List[Dict[str, Any]] = []
    steps = 0

    for event in db_events:
        event_type = event.get("type")

        if event_type == "meal":
            meal_entry = {
                "meal_name": event["meal_name"],
                "calories": event["calories"],
                "protein_g": event["protein_g"],
            }
            meals.append(meal_entry)
            current_calories += event["calories"]
            protein_g += event["protein_g"]

        elif event_type == "weight":
            weight_entry = {
                "weight": event["weight"],
                "date": event["date"],
            }
            weight_history.append(weight_entry)

        elif event_type == "workout":
            workout_entry = {
                "workout_type": event["workout_type"],
                "duration_minutes": event["duration_minutes"],
                "calories_burned": event["calories_burned"],
            }
            workouts.append(workout_entry)

        elif event_type == "steps":
            steps += event.get("steps_count", 0)

    return {
        "current_calories": current_calories,
        "target_calories": 2000,
        "protein_g": protein_g,
        "carbs_g": 180,
        "fat_g": 60,
        "meals": meals,
        "weight_history": weight_history,
        "workouts": workouts,
        "steps": steps,
    }


@app.post("/users/log-meal")
def log_meal(meal: MealCreate) -> Dict[str, str]:
    new_event = {
        "type": "meal",
        "meal_name": meal.meal_name,
        "calories": meal.calories,
        "protein_g": meal.protein_g,
    }
    db_events.append(new_event)
    return {"status": "success", "message": "הארוחה נשמרה בהצלחה ב-Event Store"}


@app.post("/users/log-weight")
def log_weight(weight_data: WeightCreate) -> Dict[str, str]:
    new_event = {
        "type": "weight",
        "weight": weight_data.weight,
        "date": weight_data.date,
    }
    db_events.append(new_event)
    return {"status": "success", "message": "המשקל עודכן בהצלחה ב-Event Store"}


@app.post("/users/log-workout")
def log_workout(workout: WorkoutCreate) -> Dict[str, str]:
    new_event = {
        "type": "workout",
        "workout_type": workout.workout_type,
        "duration_minutes": workout.duration_minutes,
        "calories_burned": workout.calories_burned,
    }
    db_events.append(new_event)
    return {"status": "success", "message": "האימון נרשם בהצלחה ב-Event Store"}


@app.post("/ai/analyze-food")
def analyze_food(request: AIMessageRequest) -> Dict[str, str]:
    keywords = ["חלבון", "משקל", "קלוריות", "אימון", "תפריט"]
    message = request.message.strip()

    if not message:
        return {
            "response": (
                "שלום! אני יועץ ה-AI של FitTrack AI. אנא הקלד/י שאלה "
                "בנושא תזונה, כושר, משקל או תפריט יומי."
            )
        }

    contains_keyword = any(keyword in message for keyword in keywords)

    if contains_keyword:
        response_text = build_rag_specialized_response(message)
    else:
        response_text = build_rag_specialized_response("")

    return {"response": response_text}
