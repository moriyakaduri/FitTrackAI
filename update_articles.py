import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import Article  # מייבא את טבלת המאמרים מהשרת שלך

# 1. התחברות למסד הנתונים שלך
DB_URL = "mssql+pymssql://moriyakaduri_SQLLogin_1:8hw5dkrycj@FitTrackDB.mssql.somee.com/FitTrackDB"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
session = Session()

def fetch_full_article(url: str) -> str:
    """ גולש לכתובת ומוריד את כל הטקסט של המאמר """
    try:
        print(f"סורק את: {url}...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        paragraphs = soup.find_all('p')
        full_text = " ".join([p.get_text() for p in paragraphs])
        
        # אנחנו שומרים טקסט ארוך יותר כי אנחנו לא בזמן אמת!
        return full_text[:2000] if full_text else ""
    except Exception as e:
        print(f"שגיאה בסריקה: {e}")
        return ""

def run_scraper_job():
    print("מתחיל עדכון מאמרים במסד הנתונים...")
    # מביא את כל המאמרים
    articles = session.query(Article).all()
    
    for art in articles:
        # סורק רק מאמרים שאין להם תקציר או שהתקציר קצר מדי
        if not art.content_summary or len(art.content_summary) < 50:
            new_text = fetch_full_article(art.url)
            if new_text:
                art.content_summary = new_text
                session.commit()
                print(f"✅ עודכן בהצלחה: {art.title}")
                
    print("🎉 עדכון המאמרים הסתיים!")

if __name__ == "__main__":
    run_scraper_job()