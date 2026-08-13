from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import re
import urllib.parse
import pyodbc  # משתמשים בספרייה הרשמית של מיקרוסופט
from sqlalchemy import create_engine, Column, Integer, Float, NVARCHAR
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import base64
import json
import os
from PIL import Image
import io

# --- חובה לשלשות: ייבוא Cloudinary ---
import cloudinary
import cloudinary.uploader

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
# CLOUDINARY SETUP
# ==============================================================================
cloudinary.config(
    cloud_name="YOUR_CLOUD_NAME",
    api_key="YOUR_API_KEY",
    api_secret="YOUR_API_SECRET",
    secure=True
)

# ==============================================================================
# DATABASE SETUP
# ==============================================================================
DB_USER = "moriyakaduri_SQLLogin_1"
DB_PASS = "8hw5dkrycj"
DB_SERVER = "FitTrackDB.mssql.somee.com"
DB_NAME = "FitTrackDB"

available_drivers = pyodbc.drivers()
best_driver = "SQL Server" 

for driver in ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server Native Client 11.0"]:
    if driver in available_drivers:
        best_driver = driver
        break

print(f"🔄 הארכיטקטורה בחרה באופן דינמי בדרייבר המאובטח: {best_driver}")

conn_str = (
    f"Driver={{{best_driver}}};"
    f"Server={DB_SERVER};"
    f"Database={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASS};"
    "TrustServerCertificate=yes;"
)

quoted_conn_str = urllib.parse.quote_plus(conn_str)
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"timeout": 60},  
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
# EXTERNAL SERVICES, GATEWAY & OLLAMA 
# ==============================================================================
class ExternalServicesGateway:
    OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
    OLLAMA_MODEL = "aminadaven/dictalm2.0-instruct:q8_0" 
    
    @classmethod
    def get_external_nutrition_data(cls, barcode: str) -> dict:
        try:
            url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    product = data.get('product', {})
                    nutriments = product.get('nutriments', {})
                    return {
                        "name": product.get('product_name_he') or product.get('product_name', 'Unknown'),
                        "calories": nutriments.get('energy-kcal_100g', 0),
                        "protein": nutriments.get('proteins_100g', 0)
                    }
        except Exception as e:
            print(f"External API Error: {e}")
        return None

    @classmethod
    def get_ai_consultation(cls, system_prompt: str) -> str:
        try:
            response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_MODEL, 
                    "prompt": system_prompt, 
                    "stream": False,
                    "options": {"temperature": 0.0} 
                },
                timeout=1000
            )
            response.raise_for_status()
            
            raw_text = response.json().get("response", "שגיאה בפענוח.")
            formatted_text = raw_text.replace("\\n", "\n").replace("\n", "<br>")
            formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_text)
            formatted_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', formatted_text)
            
            return formatted_text
            
        except Exception as e:
            return f"<b>שגיאת חיבור ל-Ollama AI:</b><br>{str(e)}"

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

    clean_message = re.sub(r'[^\w\s]', '', request.message)
    stop_words = {"את", "של", "על", "עם", "אנא", "נתח", "המאכל", "שבתמונה", "מה", "זה", "תמונה", "כמה", "קלוריות", "יש", "במנה", "הזאת", "הזה", "אני", "רוצה"}
    user_words = [w for w in clean_message.split() if w not in stop_words and len(w) >= 3]
    
    context = "=== מאגר מידע מקצועי מתוך האתרים (RAG) ===\n"
    
    art_count = 0
    all_articles = db.query(Article).all()
    for art in all_articles:
        if art_count >= 2: break
        for word in user_words:
            if len(word) >= 3 and ((art.title and word in art.title) or (art.category and word in art.category)):
                if art.content_summary and art.content_summary.strip() != "":
                    context += f"מקור למאמר: {art.title} ({art.url})\nתוכן: {art.content_summary[:300]}...\n\n"
                    art_count += 1
                break
                
    context += "=== ערכים תזונתיים מהמסד שלי ===\n"
    nut_count = 0
    all_nutrition = db.query(NutritionFact).all()
    for food in all_nutrition:
        if nut_count >= 5: break
        for word in user_words:
            if len(word) >= 2 and word in food.food_name:
                context += f"{food.food_name}: {food.calories} קלוריות, {food.protein_g} גרם חלבון.\n"
                nut_count += 1
                break

    system_prompt = f"""
    אתה יועץ כושר ותזונה וירטואלי בשם 'FitTrack AI'.
    עליך לסייע למשתמש בצורה מקצועית וידידותית.
    
    הנחיות קריטיות לתשובה שלך:
    1. ענה בעברית תקנית בלבד.
    2. תהיה קצר ולעניין - אל תכתוב מגילות.
    3. חלק את התשובה לפסקאות קצרות.
    4.זיהוי מדוייק של כל האלמנטים שיש במנה מדוייק !
    5.אל תוסיף אלמנטים שלא נמצאים בתמונה ושאתה לא מזהה בבירור  
    6.אזכור מקורות (RAG): אם השתמשת במידע ממסד הנתונים שסופק לך, ציין זאת.
    
    הנה מידע מהמאגר:
    {context}
    
    נתוני המשתמש: נותרו {calories_left} קלוריות לצריכה להיום.
    
    שאלת המשתמש: {request.message}
    """
    
    response_text = ExternalServicesGateway.get_ai_consultation(system_prompt)
    return {"response": response_text}

# ==============================================================================
# VISION ROUTES
# ==============================================================================
def compress_image_for_ai(contents: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(contents))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.thumbnail((768, 768))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error compressing image: {e}")
        return base64.b64encode(contents).decode("utf-8")

@app.post("/ai/analyze-image")
async def analyze_image_route(file: UploadFile = File(...)) -> Dict[str, str]:
    try:
        contents = await file.read()
        
        try:
            cloudinary.uploader.upload(contents, folder="fittrack_food")
            print(f"✅ תמונה הועלתה ל-Cloudinary")
        except Exception as cloud_err:
            print(f"❌ שגיאה בהעלאה ל-Cloudinary: {cloud_err}")

        img_base64 = compress_image_for_ai(contents)

        vision_prompt = """
        Analyze this food image meticulously.
        List ALL visible components. 
        Return the result STRICTLY in this JSON format based on your analysis (provide absolute numbers for the whole dish, not ranges):
        {"name": "Food Name in Hebrew", "calories": 500, "protein": 30}
        Do not include any explanations, markdown or other text. ONLY JSON.
        """

        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "llava",  
                "prompt": vision_prompt, 
                "stream": False, 
                "images": [img_base64],
                "options": {"temperature": 0.0}
            },
            timeout=300 
        )
        response.raise_for_status()

        ai_text = response.json().get("response", "{}")
        ai_text = ai_text.replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(ai_text)
            return {"status": "success", "name": result.get("name", "לא זוהה"), "calories": str(result.get("calories", 0)), "protein": str(result.get("protein", 0))}
        except json.JSONDecodeError:
            return {"status": "error", "message": "ה-AI לא הצליח לנתח את הערכים."}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/ai/chat-image")
async def chat_image_route(file: UploadFile = File(...), prompt: str = Form("אנא נתח את המאכל שבתמונה"), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        
        try:
            cloudinary.uploader.upload(contents, folder="fittrack_chat")
        except Exception as e:
            print("Cloudinary upload skipped in chat")

        img_base64 = compress_image_for_ai(contents)

        # ---------------------------------------------------------
        # RAG קליל וממוקד למניעת עומס וסינון הזיות
        # ---------------------------------------------------------
        clean_message = re.sub(r'[^\w\s]', '', prompt)
        stop_words = {"את", "של", "על", "עם", "אנא", "נתח", "המאכל", "שבתמונה", "מה", "זה", "תמונה", "כמה", "קלוריות", "יש", "במנה", "הזאת", "הזה", "אני", "רוצה"}
        user_words = [w for w in clean_message.split() if w not in stop_words and len(w) >= 3]
        
        db_context = ""
        nut_count = 0
        all_nutrition = db.query(NutritionFact).all()
        for food in all_nutrition:
            if nut_count >= 5: break
            for word in user_words:
                if len(word) >= 2 and word in food.food_name:
                    db_context += f"{food.food_name}: {food.calories} קלוריות, {food.protein_g} גרם חלבון.\n"
                    nut_count += 1
                    break

        db_context += "\n"
        art_count = 0
        all_articles = db.query(Article).all()
        for art in all_articles:
            if art_count >= 2: break
            for word in user_words:
                if len(word) >= 3 and ((art.title and word in art.title) or (art.category and word in art.category)):
                    if art.content_summary and art.content_summary.strip() != "":
                        db_context += f"מקור למאמר: {art.title} ({art.url})\nתוכן: {art.content_summary[:300]}...\n\n"
                        art_count += 1
                    break

        # ---------------------------------------------------------
        # שלב 1: מודל הראייה מנתח את התמונה באנגלית
        # ---------------------------------------------------------
        vision_prompt_english = f"""
        Analyze this food image strictly. The user asked: "{prompt}".
        1. List the visible ingredients.
        2. Give absolute numbers (NO RANGES) for the ENTIRE dish weight, protein (g), carbs (g), and fat (g).
        Return a concise factual summary in English.
        """

        vision_response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "llava",  
                "prompt": vision_prompt_english, 
                "stream": False, 
                "images": [img_base64],
                "options": {"temperature": 0.0} 
            },
            timeout=900
        )
        vision_response.raise_for_status()
        english_analysis = vision_response.json().get("response", "")

        # ---------------------------------------------------------
        # שלב 2: מודל השפה - תבנית קשיחה בלבד (Strict Template)
        # ---------------------------------------------------------
        translation_prompt = f"""
        אתה יועץ תזונה מקצועי במערכת FitTrack AI.
        המשתמש שאל: "{prompt}".
        מערכת הראייה סרקה והחזירה את המידע הבא:
        {english_analysis}
        
        נתוני RAG מהמערכת:
        {db_context}
        
        חובה עליך לענות **בדיוק** בתבנית הבאה, ללא הקדמות, ללא הסברים מיותרים וללא טווחים (השתמש במספר שלם בלבד):

        רכיבים שזוהו במנה: [רשום כאן את המרכיבים בשורה אחת]
        
        - חלבון: [מספר] גרם
        - פחמימות: [מספר] גרם
        - שומן: [מספר] גרם
        סך הכל קלוריות למנה: [כאן תרשום את התוצאה של: חלבון*4 + פחמימות*4 + שומן*9] קק"ל
        
        מקורות מידע: [ציין אם השתמשת במידע מה-RAG, אם לא, השאר ריק]
        
        💡 שים/י לב: זוהי הערכה בלבד המבוססת על מראה עיניים. לנתונים מדויקים יותר, עדיף להזין את המשקלים במרכז ההזנה.
        """

        final_response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": ExternalServicesGateway.OLLAMA_MODEL, 
                "prompt": translation_prompt, 
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=900
        )
        final_response.raise_for_status()
        raw_text = final_response.json().get("response", "שגיאה בפענוח עברית.")

        formatted_text = raw_text.replace("\\n", "\n").replace("\n", "<br>")
        formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_text)
        
        return {"response": formatted_text}
    except Exception as e:
        return {"response": f"שגיאה בניתוח: {str(e)}"}

import commands
import queries

app.include_router(commands.router)
app.include_router(queries.router)