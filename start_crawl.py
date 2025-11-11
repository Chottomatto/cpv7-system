import logging
import sys

# Configure logging with proper encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log', encoding='utf-8'),
        # Fix for console encoding issues
        logging.StreamHandler(sys.stdout)
    ],
    # Force UTF-8 encoding
    force=True
)

# Additional fix for Windows console encoding
if sys.platform == "win32":
    try:
        # Try to set console to UTF-8 on Windows
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass  # If reconfigure fails, continue anyway

logger = logging.getLogger(__name__)

def main():
    """Main function to run the data pipeline."""
    try:
        logger.info("Starting CPV7 Data Processing Pipeline...")
        
        # Test environment first
        from backend.config import Config
        logger.info(f"NEON_DB_URL configured: {bool(Config.NEON_DB_URL)}")
        if Config.NEON_DB_URL:
            logger.info(f"NEON_DB_URL: {Config.NEON_DB_URL[:30]}...")
        else:
            logger.error("NEON_DB_URL is not configured! Check your .env file")
            return
        
        from backend.app import initialize_system, start_crawler_and_wait, start_ml_processing
        
        # --- STEP 1: INITIALIZE / LOAD MODELS (and create NeonDB  ---
        logger.info("Initializing system...")
        initialize_system()
        
        # --- STEP 2: CRAWL AND STORE TO RAW_DB ---
        logger.info("Starting crawler...")
        start_crawler_and_wait()
        
        # --- STEP 3: ML ANALYZE AND SCORE > STORE TO PROCESSED_DB (NeonDB) ---
        logger.info("Starting ML processing...")
        start_ml_processing()
        
        logger.info("Data Processing Pipeline completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()