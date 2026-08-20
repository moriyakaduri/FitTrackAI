import base64
import io
import json
import os
import re
from typing import Any, Dict, Optional

import cloudinary
import cloudinary.uploader
import requests
from PIL import Image

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# ייבוא מהמודולים שלכם - ודאי שהנתיבים מתאימים למבנה הפרויקט
import commands
import queries
from backend.database import get_db, init_database
from backend.models import Article, NutritionFact, User

# הגדרת תצורת Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "YOUR_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "YOUR_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "YOUR_API_SECRET"),
    secure=True,
)

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

init_database()

app.include_router(commands.router)
app.include_router(queries.router)


def compress_image_for_ai(contents: bytes) -> str:
    """דחיסת תמונה והמרתה ל-Base64 על מנוע שיפור ביצועי AI"""
    try:
        image = Image.open(io.BytesIO(contents))
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((768, 768))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as error:
        print(f"Image compression fallback: {error}")
        return base64.b64encode(contents).decode("utf-8")


def extract_json_from_ai_response(ai_text: str) -> Dict[str, Any]:
    """חילוץ אובייקט JSON נקי מתשובת מודל ה-AI"""
    cleaned = ai_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start_index = cleaned.find("{")
    if start_index != -1:
        depth = 0
        for index in range(start_index, len(cleaned)):
            char = cleaned[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    json_block = cleaned[start_index : index + 1]
                    try:
                        parsed = json.loads(json_block)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break

    raise ValueError("AI response does not contain a valid JSON object.")


class ExternalServicesGateway:
    """
    ניהול תקשורת מול שירותים חיצוניים ומודלי AI תחת תבנית Gateway
    בהתאם לדרישות הארכיטקטורה והפרדת האחריות במערכת.
    """
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "aminadaven/dictalm2.0-instruct:q4_k_m")
    OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")

    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "1200"))
    OLLAMA_TEXT_NUM_CTX = int(os.getenv("OLLAMA_TEXT_NUM_CTX", "2048"))
    OLLAMA_TEXT_NUM_PREDICT = int(os.getenv("OLLAMA_TEXT_NUM_PREDICT", "256"))
    OPENFOODFACTS_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

    @classmethod
    def upload_image_to_cloudinary(cls, contents: bytes, folder: str = "fittrack_food") -> Optional[str]:
        """העלאת תמונת מנה או פרופיל לענן Cloudinary"""
        try:
            result = cloudinary.uploader.upload(contents, folder=folder)
            return result.get("secure_url")
        except Exception as error:
            print(f"Cloudinary upload error: {error}")
            return None

    @classmethod
    def get_external_nutrition_data(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """שליפת נתוני תזונה לפי ברקוד מ-OpenFoodFacts API"""
        try:
            response = requests.get(
                cls.OPENFOODFACTS_URL.format(barcode=barcode),
                timeout=10,
            )
            if response.status_code != 200:
                return None

            data = response.json()
            if data.get("status") != 1:
                return None

            product = data.get("product", {})
            nutriments = product.get("nutriments", {})
            return {
                "name": product.get("product_name_he") or product.get("product_name", "Unknown"),
                "calories": int(nutriments.get("energy-kcal_100g", 0) or 0),
                "protein": int(nutriments.get("proteins_100g", 0) or 0),
                "fat": int(nutriments.get("fat_100g", 0) or 0),
                "carbs": int(nutriments.get("carbohydrates_100g", 0) or 0),
                "barcode": barcode,
                "source": "OpenFoodFacts",
            }
        except Exception as error:
            print(f"OpenFoodFacts API error: {error}")
            return None

    @classmethod
    def analyze_food_image(cls, image_base64: str) -> Dict[str, Any]:
        """
        ניתוח של תמונת אוכל. שלב ראשון מזהה באנגלית (מניעת תקלות במודל ראייה), 
        בשלב השני הנתונים מתורגמים לעברית תקנית דרך מודל השפה.
        """
        # שלב 1: זיהוי באנגלית (מודל Vision פשוט מזהה יותר טוב באנגלית)
        vision_prompt = (
            "Analyze this food image accurately. Identify the actual food in the image.\n"
            "Return ONLY a valid raw JSON object. Do not output placeholder text.\n"
            "The JSON must have this exact structure, filled with your estimates:\n"
            "{\n"
            '  "name": "Write the actual name of the food in English here (e.g., Pizza, Salad, Chicken Breast)",\n'
            '  "ingredients": ["ingredient 1", "ingredient 2"],\n'
            '  "calories": 300,\n'
            '  "protein": 15,\n'
            '  "fat": 10,\n'
            '  "carbs": 20\n'
            "}\n"
        )

        try:
            # 1. קריאה למודל הראייה
            vision_response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_VISION_MODEL,
                    "prompt": vision_prompt,
                    "stream": False,
                    "images": [image_base64],
                    "options": {"temperature": 0.0},
                    "keep_alive": "10m",
                },
                timeout=cls.OLLAMA_TIMEOUT,
            )
            vision_response.raise_for_status()
            english_json_str = vision_response.json().get("response", "{}")

            # שלב 2: תרגום לעברית באמצעות מודל השפה (DictaLM) ויצירת JSON סופי
            translation_prompt = f"""
I have a JSON describing a food item in English. I need you to translate the 'name' and the 'ingredients' array to HEBREW.
Keep the numerical values exactly the same. Do not add any extra text or markdown. Output ONLY a valid JSON.

Original JSON:
{english_json_str}

Output Format:
{{
  "name": "[השם בעברית]",
  "ingredients": ["[רכיב בעברית]"],
  "calories": [number],
  "protein": [number],
  "fat": [number],
  "carbs": [number]
}}
"""
            translation_response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_TEXT_MODEL,
                    "prompt": translation_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_ctx": cls.OLLAMA_TEXT_NUM_CTX,
                        "num_predict": cls.OLLAMA_TEXT_NUM_PREDICT,
                    },
                    "keep_alive": "10m",
                },
                timeout=cls.OLLAMA_TIMEOUT,
            )
            translation_response.raise_for_status()
            hebrew_json_str = translation_response.json().get("response", "{}")

            # חילוץ סופי
            parsed_data = extract_json_from_ai_response(hebrew_json_str)

            final_name = parsed_data.get("name", "מנה לא מזוהה")
            if "name" in final_name or "e.g." in final_name:
                 final_name = "מנה (יש לעדכן ידנית)"

            return {
                "name": final_name,
                "ingredients": parsed_data.get("ingredients", []),
                "calories": int(parsed_data.get("calories", 0)),
                "protein": int(parsed_data.get("protein", 0)),
                "fat": int(parsed_data.get("fat", 0)),
                "carbs": int(parsed_data.get("carbs", 0)),
            }
        except Exception as error:
            print(f"Error parsing vision JSON: {error}")
            return {
                "name": "שגיאה בזיהוי המנה",
                "ingredients": [],
                "calories": 0,
                "protein": 0,
                "fat": 0,
                "carbs": 0,
            }

    @classmethod
    def get_ai_consultation(cls, system_prompt: str) -> str:
        """שליחת פרומפט למודל הטקסט העברי DictaLM2.0 וקבלת מענה מעוצב"""
        try:
            response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_TEXT_MODEL,
                    "prompt": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_ctx": cls.OLLAMA_TEXT_NUM_CTX,
                        "num_predict": cls.OLLAMA_TEXT_NUM_PREDICT,
                    },
                    "keep_alive": "10m",
                },
                timeout=cls.OLLAMA_TIMEOUT,
            )
            response.raise_for_status()

            raw_text = response.json().get("response", "שגיאה בפענוח.")
            formatted_text = raw_text.replace("\\n", "\n").replace("\n", "<br>")
            formatted_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", formatted_text)
            formatted_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", formatted_text)
            return formatted_text
        except requests.exceptions.Timeout:
            return "<b>שגיאה:</b><br>שרת Ollama לא הגיב בזמן (Timeout). המודל לא הספיק לעבד את הבקשה."
        except Exception as error:
            return f"<b>שגיאת חיבור ל-Ollama AI:</b><br>{error}"

    @classmethod
    def analyze_chat_image(cls, image_base64: str, prompt: str, db_context: str) -> str:
        """
        ניתוח תמונת צ'אט: חילוץ נתונים מהיר באנגלית 
        וניסוח קצר, ממוקד וענייני בעברית דרך DictaLM.
        """
        try:
            vision_prompt = (
                f'Analyze this food image for a nutrition assistant. User question: "{prompt}". '
                "Identify dish name, visible ingredients, and estimate numerical macros (Protein, Fat, Carbohydrates, Calories)."
            )

            vision_response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_VISION_MODEL,
                    "prompt": vision_prompt,
                    "stream": False,
                    "images": [image_base64],
                    "options": {"temperature": 0.0},
                    "keep_alive": "10m",
                },
                timeout=cls.OLLAMA_TIMEOUT,
            )
            vision_response.raise_for_status()
            english_analysis = vision_response.json().get("response", "")

            translation_prompt = f"""
אתה יועץ תזונה במערכת FitTrack AI.
שאלת המשתמש: "{prompt}"
ניתוח התמונה (באנגלית): {english_analysis}
נתוני רקע מהמערכת (RAG): {db_context}

הנחיות קשיחות לפלט (אורך כולל: גג 6-8 שורות בלבד):
1. כתוב בעברית בלבד. ללא אנגלית כלל.
2. אל תציג הקדמות, ברכות, הסברים על וויטמינים, ואל תרשום דיסקליימרים/הסתייגויות.
3. הצג אך ורק את הפורמט המדויק הבא:

1. **שם המנה:** [שם קצר ומדויק בעברית]
2. **רכיבים גלויים:** [רשימה קצרה מופרדת בפסיקים בלבד]
3. **ערכים תזונתיים משוערים (לכל המנה):**
• קלוריות: X קק"ל | חלבון: X גרם | שומן: X גרם | פחמימות: X גרם
"""
            return cls.get_ai_consultation(translation_prompt)

        except requests.exceptions.Timeout:
            return "<b>שגיאה:</b><br>שרת Ollama עמוס מדי וההמתנה חרגה מזמן היעד."
        except Exception as error:
            return f"<b>שגיאה בניתוח התמונה:</b><br>{error}"


class LoginRequest(BaseModel):
    username: str
    password: str


class AIMessageRequest(BaseModel):
    message: str
    username: str


def build_rag_context(db: Session, user_message: str) -> str:
    clean_message = re.sub(r"[^\w\s]", "", user_message)
    stop_words = {
        "את", "של", "על", "עם", "אנא", "נתח", "המאכל", "שבתמונה", "מה", "זה",
        "תמונה", "כמה", "קלוריות", "יש", "במנה", "הזאת", "הזה", "אני", "רוצה",
    }
    user_words = [
        word for word in clean_message.split()
        if word not in stop_words and len(word) >= 3
    ]

    context = "=== מאגר מידע מקצועי (RAG) ===\n"
    article_count = 0
    for article in db.query(Article).all():
        if article_count >= 2:
            break
        for word in user_words:
            if len(word) >= 3 and (
                (article.title and word in article.title)
                or (article.category and word in article.category)
            ):
                if article.content_summary and article.content_summary.strip():
                    context += (
                        f"מקור: {article.title} ({article.url})\n"
                        f"תוכן: {article.content_summary[:300]}...\n\n"
                    )
                    article_count += 1
                break

    context += "=== ערכים תזונתיים מהמסד ===\n"
    nutrition_count = 0
    for food in db.query(NutritionFact).all():
        if nutrition_count >= 5:
            break
        for word in user_words:
            if len(word) >= 2 and word in food.food_name:
                context += (
                    f"{food.food_name}: {food.calories} קלוריות, "
                    f"{food.protein_g} גרם חלבון.\n"
                )
                nutrition_count += 1
                break

    return context


@app.get("/")
def root_status() -> Dict[str, str]:
    return {"status": "FitTrack AI API is running", "version": "2.0.0"}


@app.post("/users/login")
def user_login(credentials: LoginRequest, db: Session = Depends(get_db)) -> Dict[str, str]:
    user = (
        db.query(User)
        .filter(
            User.username == credentials.username,
            User.password == credentials.password,
        )
        .first()
    )
    if user:
        return {"status": "success", "username": user.username}
    raise HTTPException(status_code=400, detail="שם משתמש או סיסמה שגויים")


@app.post("/ai/analyze-food")
def analyze_food(request: AIMessageRequest, db: Session = Depends(get_db)) -> Dict[str, str]:
    summary_data = queries.get_nutrition_summary(request.username, db)
    calories_left = summary_data["target_calories"] - summary_data["current_calories"]
    context = build_rag_context(db, request.message)

    system_prompt = f"""
    אתה יועץ כושר ותזונה וירטואלי בשם FitTrack AI.
    ענה בעברית, בקצרה, בפסקאות קצרות.
    אם השתמשת במידע מה-RAG, ציין זאת.

    מידע מהמאגר:
    {context}

    נותרו {calories_left} קלוריות לצריכה היום.
    שאלת המשתמש: {request.message}
    """

    response_text = ExternalServicesGateway.get_ai_consultation(system_prompt)
    return {"response": response_text}


@app.post("/ai/analyze-image")
async def analyze_image_route(file: UploadFile = File(...)) -> Dict[str, str]:
    try:
        contents = await file.read()
        ExternalServicesGateway.upload_image_to_cloudinary(contents, folder="fittrack_food")
        img_base64 = compress_image_for_ai(contents)
        
        result = ExternalServicesGateway.analyze_food_image(img_base64)

        return {
            "status": "success",
            "name": str(result.get("name", "לא זוהה")),
            "calories": str(int(result.get("calories", 0) or 0)),
            "protein": str(int(result.get("protein", 0) or 0)),
        }
    except (ValueError, json.JSONDecodeError) as parse_error:
        return {
            "status": "error",
            "message": f"לא ניתן לחלץ JSON מה-AI: {parse_error}",
        }
    except Exception as error:
        return {"status": "error", "message": str(error)}


@app.post("/ai/chat-image")
async def chat_image_route(
    file: UploadFile = File(...),
    prompt: str = Form("אנא נתח את המאכל שבתמונה"),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    try:
        contents = await file.read()
        ExternalServicesGateway.upload_image_to_cloudinary(contents, folder="fittrack_chat")
        img_base64 = compress_image_for_ai(contents)
        db_context = build_rag_context(db, prompt)
        response_text = ExternalServicesGateway.analyze_chat_image(
            img_base64, prompt, db_context
        )
        return {"response": response_text}
    except Exception as error:
        return {"response": f"שגיאה בניתוח: {error}"}