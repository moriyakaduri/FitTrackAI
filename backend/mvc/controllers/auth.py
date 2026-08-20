"""Login HTTP controller."""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.mvc.models import User

router = APIRouter(tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/users/login")
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
