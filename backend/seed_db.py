from sqlalchemy import create_engine, Column, Integer, Float, NVARCHAR
from sqlalchemy.orm import declarative_base, sessionmaker

# החיבור היציב לענן
SQLALCHEMY_DATABASE_URL = "mssql+pymssql://moriyakaduri_SQLLogin_1:8hw5dkrycj@FitTrackDB.mssql.somee.com/FitTrackDB?charset=utf8"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"timeout": 60})
Base = declarative_base()

class NutritionFact(Base):
    __tablename__ = "NutritionFacts"
    id = Column(Integer, primary_key=True, index=True)
    food_name = Column(NVARCHAR(100), unique=True, index=True)
    calories = Column(Integer)
    protein_g = Column(Float)

class Article(Base):
    __tablename__ = "Articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(NVARCHAR(200))
    content_summary = Column(NVARCHAR(4000))
    category = Column(NVARCHAR(50))
    url = Column(NVARCHAR(1000))

# פקודה אחת שבונה טבלאות אם הן לא קיימות, בלי למחוק כלום!
Base.metadata.create_all(bind=engine)
print("✅ המערכת וידאה שהטבלאות קיימות.")