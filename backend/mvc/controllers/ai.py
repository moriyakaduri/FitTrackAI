"""AI HTTP controller. RAG retrieval logic is unchanged."""

import json
import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.cqrs.queries import get_nutrition_summary
from backend.database import get_db
from backend.gateway import ExternalServicesGateway, compress_image_for_ai
from backend.mvc.models import Article, NutritionFact

router = APIRouter(tags=["AI"])


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


@router.post("/ai/analyze-food")
def analyze_food(request: AIMessageRequest, db: Session = Depends(get_db)) -> Dict[str, str]:
    summary_data = get_nutrition_summary(request.username, db)
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


@router.post("/ai/analyze-image")
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


@router.post("/ai/chat-image")
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
