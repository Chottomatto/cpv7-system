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


    #Guimaras keywords
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
        'ethical_sourcing_policy': 0.048,
        'policy_waste_disposal_hazardous_materials': 0.048, 
        'policy_waste_disposal_landfill_policy': 0.048,
        'policy_for_minimisation_of_plastic_use': 0.048,
        'policy_for_minimisation_of_disposable_items': 0.048,
        'disposable_policy': 0.0135,
        'minimisation_policies_extended_to_suppliers': 0.0135
    }