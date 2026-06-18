from typing import Dict
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import re
import urllib.parse
import pyodbc  # משתמשים בספרייה הרשמית של מיקרוסופט
from sqlalchemy import create_engine, Column, Integer, Float, NVARCHAR
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI(
    title="FitTrack AI API - Lev Academic Center",
    version="2.0.0", 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# DATABASE SETUP (מנגנון בחירת דרייבר דינמי ועמיד לענן)
# ==============================================================================
DB_USER = "moriyakaduri_SQLLogin_1"
DB_PASS = "8hw5dkrycj"
DB_SERVER = "FitTrackDB.mssql.somee.com"
DB_NAME = "FitTrackDB"

# סריקה אוטומטית של הדרייברים המותקנים אצלך במחשב כדי למנוע קפיאות ותקיעות
available_drivers = pyodbc.drivers()
best_driver = "SQL Server"  # ברירת מחדל ישנה כגיבוי אחרון

# מחפשים את הדרייברים המודרניים התומכים בהצפנת TLS 1.2/1.3 של שנת 2022
for driver in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server Native Client 11.0"]:
    if driver in available_drivers:
        best_driver = driver
        break

print(f"🔄 הארכיטקטורה בחרה באופן דינמי בדרייבר המאובטח: {best_driver}")

# בניית מחרוזת החיבור המדויקת עם הדרייבר שנמצא ואישור אבטחת השרת (TrustServerCertificate)
conn_str = (
    f"Driver={{{best_driver}}};"
    f"Server={DB_SERVER};"
    f"Database={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASS};"
    "TrustServerCertificate=yes;"
)

# קידוד מחרוזת החיבור עבור SQLAlchemy
quoted_conn_str = urllib.parse.quote_plus(conn_str)
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"timeout": 30},  # החזרנו ל-30 שניות הגיוניות, אין צורך ב-1000
    pool_pre_ping=True,
    pool_recycle=1800
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================================================================
# MODELS 
# ==============================================================================
class NutritionFact(Base):
    __tablename__ = "NutritionFacts"
    id = Column(Integer, primary_key=True, index=True)
    food_name = Column(NVARCHAR(100), unique=True, index=True)
    calories = Column(Integer)
    protein_g = Column(Float)

class User(Base):
    __tablename__ = "Users"
    username = Column(NVARCHAR(50), primary_key=True, index=True)
    password = Column(NVARCHAR(50))
    target_calories = Column(Integer)
    carbs_g = Column(Integer)
    fat_g = Column(Integer)

class UserEvent(Base):
    __tablename__ = "UserEvents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(NVARCHAR(50), index=True)
    event_type = Column(NVARCHAR(20)) 
    event_date = Column(NVARCHAR(50))
    meal_name = Column(NVARCHAR(100), nullable=True)
    calories = Column(Integer, nullable=True)
    protein_g = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True) 
    workout_type = Column(NVARCHAR(100), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    calories_burned = Column(Integer, nullable=True)

class Article(Base):
    __tablename__ = "Articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(NVARCHAR(200))
    content_summary = Column(NVARCHAR(None))
    category = Column(NVARCHAR(50))
    url = Column(NVARCHAR(None))

try:
    print("⏳ מנסה להתחבר למסד הנתונים בענן, אנא המתיני...")
    Base.metadata.create_all(bind=engine)
    print("✅ החיבור למסד הנתונים הצליח והטבלאות מוכנות לעבודה!")
except Exception as db_error:
    print(f"❌ שגיאה בחיבור למסד הנתונים: {db_error}")

class LoginRequest(BaseModel):
    username: str
    password: str

class AIMessageRequest(BaseModel):
    message: str
    username: str

# ==============================================================================
# EXTERNAL SERVICES & OLLAMA
# ==============================================================================
class ExternalServicesGateway:
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    OLLAMA_MODEL = "aminadaven/dictalm2.0-instruct:q8_0" 

    @classmethod
    def get_ai_consultation(cls, system_prompt: str) -> str:
        try:
            response = requests.post(
                cls.OLLAMA_URL,
                json={"model": cls.OLLAMA_MODEL, "prompt": system_prompt, "stream": False},
                timeout=1000
            )
            response.raise_for_status()
            return response.json().get("response", "שגיאה בפענוח.")
        except Exception as e:
            return f"**שגיאת חיבור ל-Ollama AI:**\n{str(e)}"

# ==============================================================================
# BASE ROUTES
# ==============================================================================
@app.post("/users/login")
def user_login(credentials: LoginRequest, db: Session = Depends(get_db)) -> Dict[str, str]:
    user = db.query(User).filter(User.username == credentials.username, User.password == credentials.password).first()
    if user:
        return {"status": "success", "username": user.username}
    raise HTTPException(status_code=400, detail="שם משתמש או סיסמה שגויים")

@app.post("/ai/analyze-food")
def analyze_food(request: AIMessageRequest, db: Session = Depends(get_db)) -> Dict[str, str]:
    import queries
    summary_data = queries.nutrition_summary(request.username, db)
    calories_left = summary_data["target_calories"] - summary_data["current_calories"]

    all_articles = db.query(Article).all()
    all_nutrition = db.query(NutritionFact).all()
    
    clean_message = re.sub(r'[^\w\s]', '', request.message)
    user_words = clean_message.split()
    
    context = "=== מאגר מידע מקצועי מתוך האתרים ===\n"
    
    for art in all_articles:
        for word in user_words:
            if len(word) >= 3 and ((art.title and word in art.title) or (art.category and word in art.category)):
                if art.content_summary and art.content_summary.strip() != "":
                    context += f"מקור: {art.title} ({art.url})\nתוכן: {art.content_summary}\n\n"
                break
                
    context += "=== ערכים תזונתיים מהמסד שלי ===\n"
    for food in all_nutrition:
        for word in user_words:
            if len(word) >= 2 and word in food.food_name:
                context += f"{food.food_name}: {food.calories} קלוריות, {food.protein_g} גרם חלבון.\n"
                break

    system_prompt = f"""
    אתה 'FitTrack AI', עוזר תזונה מומחה, ידידותי ומקצועי.
    כלל קריטי 1: עליך להשיב אך ורק בעברית תקנית. אין להשתמש במילים באנגלית.
    כלל קריטי 2: חובה לעצב את התשובה בצורה קריאה וברורה באמצעות Markdown.
    
    הנה מידע מהמאגר שעליך להשתמש בו כדי לענות למשתמש:
    {context}
    
    נתוני המשתמש:
    למשתמש נותרו {calories_left} קלוריות לצריכה להיום.
    
    שאלת המשתמש: {request.message}
    """
    
    response_text = ExternalServicesGateway.get_ai_consultation(system_prompt)
    return {"response": response_text}

# ==============================================================================
# IMPORT CQRS ROUTERS
# ==============================================================================
import commands
import queries

app.include_router(commands.router)
app.include_router(queries.router)