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
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "YOUR_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "YOUR_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "YOUR_API_SECRET"),
    secure=True,
)


def compress_image_for_ai(contents: bytes) -> str:
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
    """
    Strict JSON extraction: strip markdown, parse directly, then regex/brace-scan fallback.
    Expected shape: {"name": "...", "calories": 450, "protein": 25}
    """
    cleaned = ai_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    regex_match = re.search(
        r'\{\s*"name"\s*:\s*"(?:[^"\\]|\\.)*"\s*,\s*"calories"\s*:\s*\d+\s*,\s*"protein"\s*:\s*\d+\s*\}',
        cleaned,
        re.DOTALL,
    )
    if regex_match:
        return json.loads(regex_match.group(0))

    start_index = cleaned.find("{")
    if start_index == -1:
        raise ValueError("AI response does not contain a JSON object.")

    depth = 0
    for index in range(start_index, len(cleaned)):
        char = cleaned[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                json_block = cleaned[start_index : index + 1]
                return json.loads(json_block)

    raise ValueError("AI response contains an incomplete JSON object.")


class ExternalServicesGateway:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "aminadaven/dictalm2.0-instruct:q8_0")
    OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # הוגדל ל-300 שניות
    OPENFOODFACTS_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

    @classmethod
    def upload_image_to_cloudinary(cls, contents: bytes, folder: str = "fittrack_food") -> Optional[str]:
        try:
            result = cloudinary.uploader.upload(contents, folder=folder)
            return result.get("secure_url")
        except Exception as error:
            print(f"Cloudinary upload error: {error}")
            return None

    @classmethod
    def get_external_nutrition_data(cls, barcode: str) -> Optional[Dict[str, Any]]:
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
                "name": product.get("product_name_he")
                or product.get("product_name", "Unknown"),
                "calories": int(nutriments.get("energy-kcal_100g", 0) or 0),
                "protein": int(nutriments.get("proteins_100g", 0) or 0),
                "barcode": barcode,
                "source": "OpenFoodFacts",
            }
        except Exception as error:
            print(f"OpenFoodFacts API error: {error}")
            return None

    @classmethod
    def analyze_food_image(cls, image_base64: str) -> Dict[str, Any]:
        vision_prompt = (
            'Analyze this food image. Return ONLY a raw JSON object with this exact structure: '
            '{"name": "שם המאכל בעברית", "calories": 450, "protein": 25}. '
            "No markdown, no explanations, no extra text."
        )

        response = requests.post(
            cls.OLLAMA_URL,
            json={
                "model": cls.OLLAMA_VISION_MODEL,
                "prompt": vision_prompt,
                "stream": False,
                "images": [image_base64],
                "options": {"temperature": 0.0},
            },
            timeout=cls.OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        ai_text = response.json().get("response", "{}")
        return extract_json_from_ai_response(ai_text)

    @classmethod
    def get_ai_consultation(cls, system_prompt: str) -> str:
        try:
            response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_TEXT_MODEL,
                    "prompt": system_prompt,
                    "stream": False,
                    "options": {"temperature": 0.0},
                },
                timeout=cls.OLLAMA_TIMEOUT,  # שונה מ-120 ל-300
            )
            response.raise_for_status()

            raw_text = response.json().get("response", "שגיאה בפענוח.")
            formatted_text = raw_text.replace("\\n", "\n").replace("\n", "<br>")
            formatted_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", formatted_text)
            formatted_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", formatted_text)
            return formatted_text
        except requests.exceptions.Timeout:
            return "<b>שגיאה:</b><br>שרת Ollama לא הגיב בזמן (Timeout). תהליך טעינת המודל לקח יותר מדי זמן."
        except Exception as error:
            return f"<b>שגיאת חיבור ל-Ollama AI:</b><br>{error}"

    @classmethod
    def analyze_chat_image(cls, image_base64: str, prompt: str, db_context: str) -> str:
        try:
            vision_prompt = (
                f'Analyze this food image. User question: "{prompt}". '
                "List visible ingredients and estimate macros for the entire dish."
            )

            vision_response = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": cls.OLLAMA_VISION_MODEL,
                    "prompt": vision_prompt,
                    "stream": False,
                    "images": [image_base64],
                    "options": {"temperature": 0.0},
                },
                timeout=cls.OLLAMA_TIMEOUT,
            )
            vision_response.raise_for_status()
            english_analysis = vision_response.json().get("response", "")

            translation_prompt = f"""
            אתה יועץ תזונה מקצועי במערכת FitTrack AI.
            שאלת המשתמש: "{prompt}"
            ניתוח הראייה: {english_analysis}
            נתוני RAG מהמערכת:
            {db_context}

            ענה בעברית, בקצרה, עם הערכת קלוריות וחלבון למנה.
            """
            return cls.get_ai_consultation(translation_prompt)
        except requests.exceptions.Timeout:
            return "<b>שגיאה:</b><br>שרת Ollama לא הגיב בזמן עיבוד התמונה (Timeout)."
        except Exception as error:
            return f"<b>שגיאה בניתוח תמונה:</b><br>{error}"