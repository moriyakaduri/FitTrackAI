"""Gateway for Ollama, Cloudinary, and external nutrition services."""

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

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
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
        """Answer a chat question about an uploaded food image using LLaVA plus DictaLM."""
        user_question = (prompt or "").strip() or "אנא נתח את המאכל שבתמונה"
        rag_context = (db_context or "").strip() or "אין הקשר נוסף מהמאגר."
        vision_prompt = (
            "Look at this food image and answer the user's question using only what you see.\n"
            "Write a concise English description of the food and a direct answer to the question.\n"
            f"User question: {user_question}\n"
        )
        try:
            vision_response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_VISION_MODEL,
                    "prompt": vision_prompt,
                    "stream": False,
                    "images": [image_base64],
                    "options": {
                        "temperature": 0.0,
                        "num_predict": cls.OLLAMA_TEXT_NUM_PREDICT,
                    },
                    "keep_alive": "10m",
                },
                timeout=cls.OLLAMA_TIMEOUT,
            )
            vision_response.raise_for_status()
            image_description = vision_response.json().get("response", "").strip()
            if not image_description:
                raise ValueError("מודל הראייה לא החזיר תיאור לתמונה")

            hebrew_prompt = f"""
אתה יועץ כושר ותזונה וירטואלי בשם FitTrack AI.
ענה בעברית, בקצרה, ובקשר ישיר לשאלת המשתמש ולתמונה.
אם השתמשת במידע מהמאגר, ציין זאת.

שאלת המשתמש:
{user_question}

תיאור התמונה ממודל הראייה:
{image_description}

מידע מהמאגר:
{rag_context}
"""
            return cls.get_ai_consultation(hebrew_prompt)
        except Exception as error:
            return f"<b>שגיאה בניתוח התמונה:</b><br>{error}"
