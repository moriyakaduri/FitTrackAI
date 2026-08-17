from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.gateway import ExternalServicesGateway
from backend.models import User, UserEvent

router = APIRouter(prefix="/commands", tags=["Commands"])


class MealCreate(BaseModel):
    meal_name: str
    calories: int
    protein_g: int
    username: str


class WeightCreate(BaseModel):
    weight: float
    date: str
    username: str


class WorkoutCreate(BaseModel):
    workout_type: str
    duration_minutes: int
    username: str


def append_user_event(db: Session, event: UserEvent) -> None:
    """Event Sourcing: append-only immutable event write."""
    db.add(event)
    db.commit()
    db.refresh(event)


@router.post("/log-meal")
def log_meal(meal: MealCreate, db: Session = Depends(get_db)) -> Dict[str, str]:
    new_event = UserEvent(
        username=meal.username,
        event_type="meal",
        event_date=date.today().isoformat(),
        meal_name=meal.meal_name,
        calories=meal.calories,
        protein_g=meal.protein_g,
    )
    append_user_event(db, new_event)
    return {"status": "success", "message": "Meal event stored in UserEvents."}


@router.post("/log-weight")
def log_weight(weight_data: WeightCreate, db: Session = Depends(get_db)) -> Dict[str, str]:
    new_event = UserEvent(
        username=weight_data.username,
        event_type="weight",
        event_date=weight_data.date,
        weight=weight_data.weight,
    )
    append_user_event(db, new_event)
    return {"status": "success", "message": "Weight event stored in UserEvents."}


@router.post("/log-workout")
def log_workout(workout: WorkoutCreate, db: Session = Depends(get_db)) -> Dict[str, str]:
    calories_burned = workout.duration_minutes * 8
    new_event = UserEvent(
        username=workout.username,
        event_type="workout",
        event_date=date.today().isoformat(),
        workout_type=workout.workout_type,
        duration_minutes=workout.duration_minutes,
        calories_burned=calories_burned,
    )
    append_user_event(db, new_event)
    return {"status": "success", "message": "Workout event stored in UserEvents."}
