from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
# תיקון הייבוא כאן:
from backend.main import get_db, User, UserEvent

router = APIRouter(prefix="/queries", tags=["Queries"])

@router.get("/nutrition-summary")
def nutrition_summary(username: str = Query("Moriah"), db: Session = Depends(get_db)) -> Dict[str, Any]:
    user_profile = db.query(User).filter(User.username == username).first()
    if not user_profile:
        user_profile = User(target_calories=2000, carbs_g=200, fat_g=60)

    user_events = db.query(UserEvent).filter(UserEvent.username == username).all()
    current_calories = protein_g = 0
    meals = []

    for event in user_events:
        if event.event_type == "meal":
            meals.append({"meal_name": event.meal_name, "calories": event.calories, "protein_g": event.protein_g})
            current_calories += event.calories or 0
            protein_g += event.protein_g or 0
        elif event.event_type == "workout":
            current_calories -= event.calories_burned or 0

    return {
        "current_calories": max(current_calories, 0),
        "target_calories": user_profile.target_calories,
        "protein_g": protein_g,
        "carbs_g": user_profile.carbs_g,
        "fat_g": user_profile.fat_g,
        "meals": meals
    }