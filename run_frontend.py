import os
import sys
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
# ... (logging setup remains the same) ...

logger = logging.getLogger(__name__)

def main():
    """Main function to start the web server."""
    try:
        logger.info("Starting CPV7 Web Server (Frontend/API)...")
        
        # Import the app and the initialization function
        # We REMOVE the imports for start_crawler_and_wait and start_ml_processing
        from backend.app import app, initialize_system
        
        # --- STEP 1: INITIALIZE / LOAD MODELS (Phase 1) ---
        # This is VITAL: It creates the NeonDB table and loads ML models.
        initialize_system() 
        
        # --- STEP 2: START THE FLASK SERVER ---
        logger.info("System initialized. Starting web server...")
        # The web server can now run immediately without waiting for crawling/processing.
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False) 
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()