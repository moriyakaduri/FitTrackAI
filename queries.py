from typing import Any, Dict, List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.gateway import ExternalServicesGateway
from backend.models import User, UserEvent

router = APIRouter(prefix="/queries", tags=["Queries"])


def get_nutrition_summary(username: str, db: Session) -> Dict[str, Any]:
    user_profile = db.query(User).filter(User.username == username).first()
    if not user_profile:
        user_profile = User(
            username=username,
            target_calories=2000,
            carbs_g=200,
            fat_g=60,
        )

    user_events = db.query(UserEvent).filter(UserEvent.username == username).all()
    
    # תאריך של היום לאיפוס יומי!
    today_str = date.today().isoformat()

    current_calories = 0
    protein_g = 0
    meals: List[Dict[str, Any]] = []
    weights: List[Dict[str, Any]] = []
    workouts: List[Dict[str, Any]] = []
    total_workout_minutes = 0
    total_calories_burned = 0

    for event in user_events:
        # סוכם רק ארוחות של היום הנוכחי (איפוס יומי)
        if event.event_type == "meal" and event.event_date == today_str:
            meals.append(
                {
                    "id": event.id,
                    "meal_name": event.meal_name,
                    "calories": event.calories,
                    "protein_g": event.protein_g,
                    "event_date": event.event_date,
                }
            )
            current_calories += event.calories or 0
            protein_g += event.protein_g or 0
            
        # סוכם רק אימונים של היום הנוכחי
        elif event.event_type == "workout" and event.event_date == today_str:
            burned = event.calories_burned or 0
            duration = event.duration_minutes or 0
            workouts.append(
                {
                    "id": event.id,
                    "workout_type": event.workout_type,
                    "duration_minutes": duration,
                    "calories_burned": burned,
                    "event_date": event.event_date,
                }
            )
            current_calories -= burned
            total_workout_minutes += duration
            total_calories_burned += burned
            
        # משקלים אנחנו לוקחים תמיד (כל ההיסטוריה) כדי לבנות את גרף המגמות
        elif event.event_type == "weight":
            if event.weight is not None and event.event_date:
                weights.append({"weight": event.weight, "date": event.event_date})

    weight_analysis = (
        "אין מספיק נתוני שקילה כדי לייצר ניתוח מגמות. "
        "אנא הזיני שקילות במרכז ההזנה."
    )

    if len(weights) >= 2:
        weights.sort(key=lambda entry: entry["date"])
        first_weight = weights[0]["weight"]
        last_weight = weights[-1]["weight"]
        diff = last_weight - first_weight

        if diff < 0:
            weight_analysis = (
                f"מגמה חיובית! ירדת {abs(diff):.1f} ק\"ג "
                f"מאז השקילה הראשונה שלך."
            )
        elif diff > 0:
            weight_analysis = (
                f"מגמת עלייה: עלית {diff:.1f} ק\"ג מאז השקילה הראשונה."
            )
        else:
            weight_analysis = "המשקל שלך יציב ללא שינוי מהשקילה הראשונה."
    elif len(weights) == 1:
        weight_analysis = (
            f"שקילה ראשונה בוצעה ({weights[0]['weight']} ק\"ג). "
            "הוסיפי עוד שקילות לצורך מעקב מגמה."
        )

    return {
        "current_calories": max(current_calories, 0),
        "target_calories": user_profile.target_calories or 2000,
        "protein_g": protein_g,
        "carbs_g": user_profile.carbs_g or 200,
        "fat_g": user_profile.fat_g or 60,
        "meals": meals,
        "workouts": workouts,
        "total_workout_minutes": total_workout_minutes,
        "total_calories_burned": total_calories_burned,
        "weight_history": weights,
        "weight_analysis": weight_analysis,
    }


@router.get("/nutrition-summary")
def nutrition_summary(
    username: str = Query("Moriah"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return get_nutrition_summary(username, db)


@router.get("/meal-details")
def meal_details(
    event_id: int = Query(...),
    username: str = Query(...),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    event = (
        db.query(UserEvent)
        .filter(
            UserEvent.id == event_id,
            UserEvent.username == username,
            UserEvent.event_type == "meal",
        )
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Meal event not found.")

    return {
        "id": event.id,
        "username": event.username,
        "event_type": event.event_type,
        "event_date": event.event_date,
        "meal_name": event.meal_name,
        "calories": event.calories,
        "protein_g": event.protein_g,
    }


@router.get("/openfoodfacts")
def openfoodfacts_lookup(
    barcode: str = Query(..., min_length=8),
) -> Dict[str, Any]:
    product = ExternalServicesGateway.get_external_nutrition_data(barcode)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in OpenFoodFacts.")
    return product