from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Float, NVARCHAR

Base = declarative_base()

class NutritionFact(Base):
    __tablename__ = "NutritionFacts"
    id = Column(Integer, primary_key=True, index=True)
    food_name = Column(NVARCHAR(100), unique=True, index=True)
    calories = Column(Integer)
    protein_g = Column(Float)

class User(Base):
    __tablename__ = "Users"
    username = Column(NVARCHAR(50), primary_key=True, index=True)
    password = Column(NVARCHAR(50))
    target_calories = Column(Integer)
    carbs_g = Column(Integer)
    fat_g = Column(Integer)

class UserEvent(Base):
    __tablename__ = "UserEvents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(NVARCHAR(50), index=True)
    event_type = Column(NVARCHAR(20)) 
    event_date = Column(NVARCHAR(50))
    meal_name = Column(NVARCHAR(100), nullable=True)
    calories = Column(Integer, nullable=True)
    protein_g = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True) 
    workout_type = Column(NVARCHAR(100), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    calories_burned = Column(Integer, nullable=True)

class Article(Base):
    __tablename__ = "Articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(NVARCHAR(200))
    content_summary = Column(NVARCHAR(None))
    category = Column(NVARCHAR(50))
    url = Column(NVARCHAR(None))