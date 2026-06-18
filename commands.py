from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel
# תיקון הייבוא כאן:
from backend.main import get_db, UserEvent

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

@router.post("/log-meal")
def log_meal(meal: MealCreate, db: Session = Depends(get_db)):
    new_event = UserEvent(username=meal.username, event_type="meal", event_date=date.today().isoformat(),
                          meal_name=meal.meal_name, calories=meal.calories, protein_g=meal.protein_g)
    db.add(new_event)
    db.commit()
    return {"status": "success"}

@router.post("/log-weight")
def log_weight(weight_data: WeightCreate, db: Session = Depends(get_db)):
    new_event = UserEvent(username=weight_data.username, event_type="weight", event_date=weight_data.date, weight=weight_data.weight)
    db.add(new_event)
    db.commit()
    return {"status": "success"}

@router.post("/log-workout")
def log_workout(workout: WorkoutCreate, db: Session = Depends(get_db)):
    burned = workout.duration_minutes * 8
    new_event = UserEvent(username=workout.username, event_type="workout", event_date=date.today().isoformat(),
                          workout_type=workout.workout_type, duration_minutes=workout.duration_minutes, calories_burned=burned)
    db.add(new_event)
    db.commit()
    return {"status": "success"}