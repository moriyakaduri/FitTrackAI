import os
import urllib.parse

import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.mvc.models.entities import Base

DB_USER = os.getenv("FITTRACK_DB_USER", "moriyakaduri_SQLLogin_1")
DB_PASS = os.getenv("FITTRACK_DB_PASS", "8hw5dkrycj")
DB_SERVER = os.getenv("FITTRACK_DB_SERVER", "FitTrackDB.mssql.somee.com")
DB_NAME = os.getenv("FITTRACK_DB_NAME", "FitTrackDB")

available_drivers = pyodbc.drivers()
best_driver = "SQL Server"

for driver in [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
]:
    if driver in available_drivers:
        best_driver = driver
        break

conn_str = (
    f"Driver={{{best_driver}}};"
    f"Server={DB_SERVER};"
    f"Database={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASS};"
    "TrustServerCertificate=yes;"
)

quoted_conn_str = urllib.parse.quote_plus(conn_str)
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"timeout": 60},
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables are ready.")
    except Exception as db_error:
        print(f"Database initialization error: {db_error}")
