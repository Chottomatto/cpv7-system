import sys
import os
from flask import Flask, render_template, request, jsonify
import time
import logging
from backend.database.models import init_processed_db, init_raw_db
from backend.crawler.spider import WebSpider
from backend.ml.model import ArticleClassifier
from backend.database.operations import DatabaseOperations
from backend.config import Config
from backend.database.models import init_processed_db 


# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')

# Global instances
spider = None
classifier = ArticleClassifier()
db_ops = DatabaseOperations()


# --- PHASE 1: INITIALIZATION ---
def initialize_system():
    """Initialize system: Databases and ML Models """
    
    # 1. Initialize SQLite database for raw articles
    init_raw_db()
    
    # 2. Initialize PostgreSQL tables if NeonDB URL is set
    if Config.NEON_DB_URL:
        logger.info("NeonDB URL detected. Initializing PostgreSQL tables...")
        init_processed_db()
    
    # 3. Load ML models
    classifier.load_models()


# --- PHASE 2: CRAWLING (Blocking/Sequential) ---
def start_crawler_and_wait():
    """Initializes and runs the crawler to completion. This is a blocking call."""
    global spider
    
    # Instantiate the spider after models/db are ready
    spider = WebSpider() 
    
    logger.info("Starting CRAWLER...")
    spider.start_crawling()
    logger.info("CRAWLER FINISHED. Data is stored in raw_articles.")


# --- PHASE 3: ML PROCESSING (Blocking/Sequential) ---

def start_ml_processing():
    """Runs the ML pipeline on all unprocessed raw articles until complete."""
    logger.info("Starting ML PROCESSOR...")
    
    processed_count = 0
    batch_size = 50
    while True:
        # Fetch a batch of unprocessed articles
        articles = db_ops.get_unprocessed_articles(limit=batch_size)
        
        if not articles:
            logger.info(f"ML Processor found no more unprocessed articles. Total processed: {processed_count}")
            break
        
        processed_ids = []
        successful_processed = 0
        
        for article in articles:
            try:
                # Process article through ML pipeline
                processed_data = classifier.process_article(article)
                
                # Only save articles that are successfully processed and scored
                if processed_data and processed_data.get('total_score', 0) > 0.03:
                    success = db_ops.save_processed_article(processed_data)
                    if success:
                        successful_processed += 1
                        #logger.info(f"Saved processed article: {processed_data.get('title', 'No title')[:50]}... Score: {processed_data.get('total_score', 0):.3f}")
                    else:
                        logger.error(f"Failed to save processed article to NeonDB")
                
                processed_ids.append(article['id'])
                
            except Exception as e:
                logger.error(f"Error processing article ID {article.get('id')}: {e}")
                processed_ids.append(article['id'])  # Mark as processed even if failed
        
        # Mark the batch as processed in the raw_articles table
        if processed_ids:
            db_ops.mark_articles_as_processed(processed_ids)
        
        processed_count += len(articles)
        logger.info(f"Batch completed: {len(articles)} articles processed, {successful_processed} saved to NeonDB")
        
        # Small delay between batches
        time.sleep(1)

    logger.info(f"ML Processing completed. Total articles processed: {processed_count}")

# --- FLASK ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    query = request.args.get('q')
    limit = request.args.get('limit', 10, type=int)

    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    try:
        results = db_ops.search_articles(query, limit)
        return jsonify({
            'query': query,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/status')
def get_status():
    try:
        stats = db_ops.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'error': 'Could not fetch status'}), 500

@app.route('/api/articles')
def get_articles():
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    try:
        articles = db_ops.get_processed_articles(limit, offset)
        return jsonify({
            'articles': articles,
            'count': len(articles)
        })
    except Exception as e:
        logger.error(f"Articles fetch error: {e}")
        return jsonify({'error': 'Could not fetch articles'}), 500

if __name__ == '__main__':
    pass