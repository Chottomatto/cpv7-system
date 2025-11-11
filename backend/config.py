import os
from dotenv import load_dotenv

# Load from root directory
load_dotenv()

class Config:
    # Database
    SQLITE_DB = "raw_articles.db"
    NEON_DB_URL = os.getenv("NEON_DB_URL")
    
    # Crawler settings
    CRAWL_DELAY = 1  
    MAX_PAGES = 1000
    USER_AGENT = "AcademicResearchBot/1.0"
    MAX_WORKERS = 10
    
    # ML Settings
    MODEL_PATH = "ml/models/"
    CLASSIFICATION_THRESHOLD = 0.75
    GUIMARAS_KEYWORDS = [
        "guimaras", "gsu", "guimaras state university", 
        "deped guimaras", "guimaras news", "buenavista",
        "jordan", "nueva valencia", "sibunag", "san lorenzo",
    ]
    
    # Seed URLs
    SEED_URLS = [
        "https://cst.gsu.edu.ph/2025/",
        "https://cst.gsu.edu.ph/2024/",
        "https://www.gsu.edu.ph/2023",
        "https://www.gsu.edu.ph/2024", 
        "https://www.gsu.edu.ph/2025",
        "https://guimaras.gov.ph/news-updates",
        "https://deped.sdguimaras.com/news"
    ]
    
    # Category weights for scoring
    CATEGORY_WEIGHTS = {
        'public_resource': 0.05,
        'public_events': 0.05, 
        'vocational_training': 0.05,
        'education_outreach': 0.05,
        'access_policy': 0.068,
        'teaching_qualifications': 0.154,
        'first_generation_students': 0.308
    }