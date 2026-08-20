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
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
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
    def upload_image_to_cloudinary(cls, contents: bytes, folder: str = "fittrack_food") -> str:
        """העלאת תמונת מנה או פרופיל לענן Cloudinary"""
        required_variables = (
            "CLOUDINARY_CLOUD_NAME",
            "CLOUDINARY_API_KEY",
            "CLOUDINARY_API_SECRET",
        )
        missing_variables = [
            name for name in required_variables if not os.getenv(name)
        ]
        if missing_variables:
            raise RuntimeError(
                "Cloudinary is not configured. Missing environment variables: "
                + ", ".join(missing_variables)
            )

        try:
            result = cloudinary.uploader.upload(
                contents,
                folder=folder,
                resource_type="image",
            )
            secure_url = result.get("secure_url")
            if not secure_url:
                raise RuntimeError("Cloudinary did not return a secure URL.")
            return str(secure_url)
        except Exception as error:
            raise RuntimeError(f"Cloudinary image upload failed: {error}") from error

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
        def estimated_int(value: Any, field_name: str) -> int:
            match = re.search(r"-?\d+(?:\.\d+)?", str(value))
            if not match:
                raise ValueError(f"חסר ערך מספרי עבור {field_name}")
            number = int(float(match.group()))
            if number < 0:
                raise ValueError(f"ערך לא תקין עבור {field_name}")
            return number

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

            final_name = str(parsed_data.get("name", "")).strip()
            if (
                not final_name
                or "name" in final_name.lower()
                or "e.g." in final_name.lower()
                or not re.search(r"[\u0590-\u05ff]", final_name)
            ):
                raise ValueError("המודל לא החזיר שם מנה מזוהה בעברית")

            ingredients = parsed_data.get("ingredients", [])
            if not isinstance(ingredients, list):
                ingredients = []

            calories = estimated_int(parsed_data.get("calories"), "קלוריות")
            protein = estimated_int(parsed_data.get("protein"), "חלבון")
            fat = estimated_int(parsed_data.get("fat"), "שומן")
            carbs = estimated_int(parsed_data.get("carbs"), "פחמימות")
            if calories == 0:
                raise ValueError("המודל לא החזיר הערכת קלוריות שימושית")

            return {
                "name": final_name,
                "ingredients": [str(item) for item in ingredients if str(item).strip()],
                "calories": calories,
                "protein": protein,
                "fat": fat,
                "carbs": carbs,
            }
        except Exception as error:
            print(f"Error parsing vision JSON: {error}")
            raise ValueError(f"לא ניתן לזהות את המנה באופן אמין: {error}") from error

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
        ניתוח תמונת צ'אט באמצעות אותו פלט מובנה ואמין של מסך הזנת הארוחה.
        """
        try:
            result = cls.analyze_food_image(image_base64)
            ingredients = ", ".join(result["ingredients"]) or "לא זוהו רכיבים נוספים"
            return (
                f"1. <b>שם המנה:</b> {result['name']}<br>"
                f"2. <b>רכיבים גלויים:</b> {ingredients}<br>"
                "3. <b>ערכים תזונתיים משוערים (לכל המנה):</b><br>"
                f"• קלוריות: {result['calories']} קק\"ל | "
                f"חלבון: {result['protein']} גרם | "
                f"שומן: {result['fat']} גרם | "
                f"פחמימות: {result['carbs']} גרם"
            )
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
async def analyze_image_route(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        contents = await file.read()
        secure_url = ExternalServicesGateway.upload_image_to_cloudinary(
            contents, folder="fittrack_food"
        )
        img_base64 = compress_image_for_ai(contents)
        
        result = ExternalServicesGateway.analyze_food_image(img_base64)

        return {
            "status": "success",
            "name": str(result.get("name", "לא זוהה")),
            "calories": str(int(result.get("calories", 0) or 0)),
            "protein": str(int(result.get("protein", 0) or 0)),
            "ingredients": result.get("ingredients", []),
            "fat": str(int(result.get("fat", 0) or 0)),
            "carbs": str(int(result.get("carbs", 0) or 0)),
            "secure_url": secure_url,
        }
    except (ValueError, json.JSONDecodeError) as parse_error:
        return {
            "status": "error",
            "message": f"ניתוח התמונה נכשל: {parse_error}",
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
        secure_url = ExternalServicesGateway.upload_image_to_cloudinary(
            contents, folder="fittrack_chat"
        )
        img_base64 = compress_image_for_ai(contents)
        db_context = build_rag_context(db, prompt)
        response_text = ExternalServicesGateway.analyze_chat_image(
            img_base64, prompt, db_context
        )
        return {
            "status": "success",
            "response": response_text,
            "secure_url": secure_url,
        }
    except Exception as error:
        return {
            "status": "error",
            "response": f"שגיאה בניתוח: {error}",
            "message": str(error),
        }