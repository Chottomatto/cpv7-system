from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import sqlite3
from backend.config import Config

# Create separate bases for different databases
ProcessedBase = declarative_base()

# Only ProcessedArticle should be in NeonDB
class ProcessedArticle(ProcessedBase):
    __tablename__ = "processed_articles"
    
    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False)
    title = Column(Text)
    content = Column(Text)
    author = Column(String(200))
    doi = Column(String(100))
    categories = Column(JSON)
    total_score = Column(Float)
    processed_at = Column(DateTime, default=func.now())

def init_processed_db():
    """Initialize ONLY processed articles in NeonDB"""
    try:
        if Config.NEON_DB_URL:
            engine = create_engine(Config.NEON_DB_URL)
            ProcessedBase.metadata.create_all(engine)  # ← Only creates processed_articles
            print("Processed articles table created in NeonDB")
        else:
            print("No NeonDB URL provided. Processed articles will not be saved.")
    except Exception as e:
        print(f"Error initializing processed articles database: {e}")

# SQLite initialization for raw articles (separate function)
def init_raw_db():
    """Initialize raw articles in SQLite"""
    try:
        conn = sqlite3.connect(Config.SQLITE_DB)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                author TEXT,
                doi TEXT,
                html_content TEXT,
                crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed ON raw_articles(processed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON raw_articles(url)')
        
        conn.commit()
        conn.close()
        print("Raw articles database (SQLite) initialized successfully")
    except Exception as e:
        print(f"Error initializing raw articles database: {e}")