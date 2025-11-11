import logging
from backend.config import Config

import sys
import io
import logging

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging with UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class CrawlerPipeline:
    def __init__(self):
        self.stats = {
            'crawled': 0,
            'saved': 0,
            'failed': 0
        }
    
    def process_item(self, item, spider):
        """Process crawled item"""
        try:
            self.stats['crawled'] += 1
            
            # Validate item
            if self.is_valid_article(item):
                # Save to database
                if self.save_to_database(item):
                    self.stats['saved'] += 1
                    logger.info(f"Saved article: {item['title'][:50]}...")
                else:
                    self.stats['failed'] += 1
            else:
                self.stats['failed'] += 1
                
            return item
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.stats['failed'] += 1
            return item
    
    def is_valid_article(self, item):
        """Validate if article meets minimum requirements"""
        if not item.get('content'):
            return False
        
        if len(item['content'].strip()) < 10:
            return False
        
        if not item.get('title') or len(item['title'].strip()) < 5:
            return False
            
        return True
    
    def save_to_database(self, item):
        """Save item to database"""
        return True
    
    def get_stats(self):
        """Get pipeline statistics"""
        return self.stats.copy()