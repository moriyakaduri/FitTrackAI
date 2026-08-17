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

# הגדרת תצורת Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "YOUR_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "YOUR_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "YOUR_API_SECRET"),
    secure=True,
)


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
    OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "aminadaven/dictalm2.0-instruct:q8_0")
    OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "moondream")

    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
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
        """ניתוח מהיר של תמונת אוכל והחזרת נתוני JSON מובנים לרישום יומן ארוחות"""
        vision_prompt = (
            "Analyze this food image accurately.\n"
            "Identify dish name, visible ingredients, and estimated macros.\n"
            "Return ONLY a valid raw JSON object with this exact structure:\n"
            '{\n'
            '  "name": "שם המנה בעברית",\n'
            '  "ingredients": ["מרכיב 1", "מרכיב 2"],\n'
            '  "calories": 450,\n'
            '  "protein": 25,\n'
            '  "fat": 15,\n'
            '  "carbs": 35\n'
            '}\n'
            "No markdown formatting, no explanations, no extra text."
        )

        try:
            response = requests.post(
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
            response.raise_for_status()
            ai_text = response.json().get("response", "{}")

            parsed_data = extract_json_from_ai_response(ai_text)

            return {
                "name": parsed_data.get("name", "מנה לא מזוהה"),
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
                    "options": {"temperature": 0.0},
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
        ניתוח תמונת צ'אט: חילוץ נתונים מהיר באנגלית דרך moondream
        וניסוח קצר, ממוקד וענייני בעברית דרך DictaLM.
        """
        try:
            # שלב 1: חילוץ נתונים מפורט ומהיר מהתמונה באנגלית
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

            # שלב 2: ניסוח קצר, תמציתי ומדויק בעברית בלבד
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