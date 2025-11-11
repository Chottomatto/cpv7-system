import sqlite3
import json
import logging
from typing import List, Dict, Any
from backend.config import Config

logger = logging.getLogger(__name__)

class DatabaseOperations:
    def __init__(self):
        self.sqlite_db = Config.SQLITE_DB
        self.neon_db_url = Config.NEON_DB_URL
    
    def init_databases(self):
        """Initialize both databases"""
        try:
            # Initialize SQLite for raw articles
            conn = sqlite3.connect(self.sqlite_db)
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
            
            pass
                
            logger.info("Raw articles database (SQLite) initialized successfully.")
            
        except Exception as e:
            logger.error(f"Error initializing databases: {e}")

    def save_raw_article(self, article: Dict[str, Any]) -> bool:
        """Save a raw article to the SQLite database."""
        try:
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO raw_articles 
                (url, title, content, author, doi, html_content)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                article.get('url'), 
                article.get('title'), 
                article.get('content'), 
                article.get('author'), 
                article.get('doi'), 
                article.get('html_content')
            ))
            
            inserted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return inserted
        except Exception as e:
            logger.error(f"Error saving raw article {article.get('url')}: {e}")
            return False

    def get_unprocessed_articles(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch a batch of articles that have not yet been processed."""
        articles = []
        try:
            conn = sqlite3.connect(self.sqlite_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM raw_articles 
                WHERE processed = 0 
                LIMIT ?
            ''', (limit,))
            
            articles = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
        except Exception as e:
            logger.error(f"Error fetching unprocessed articles: {e}")
            
        return articles

    def mark_articles_as_processed(self, article_ids: List[int]):
        """Mark a list of articles in the raw_articles table as processed."""
        if not article_ids:
            return
        
        # Prepare the placeholder string: (?, ?, ?, ...) for the SQL IN clause
        placeholders = ', '.join('?' * len(article_ids))
        
        try:
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()
            
            # Use IN clause to update all articles in one query
            cursor.execute(f'''
                UPDATE raw_articles
                SET processed = 1
                WHERE id IN ({placeholders})
            ''', tuple(article_ids))
            
            conn.commit()
            conn.close()
            logger.info(f"Successfully marked {cursor.rowcount} articles as processed.")
        except Exception as e:
            logger.error(f"Error marking articles as processed: {e}")            

    def save_processed_article(self, article: Dict[str, Any]) -> bool:
        """Save a processed article to the processed_articles table (PostgreSQL only)."""
        
        if not self.neon_db_url:
            logger.error("No NeonDB URL configured. Cannot save processed article.")
            return False
            
        try:
            import psycopg2
            conn = psycopg2.connect(self.neon_db_url)
            cursor = conn.cursor()
            
            columns = [
                'url', 'title', 'content', 'author', 'doi', 
                'categories', 'total_score'
            ]
            
            # Prepare JSON data for categories
            categories_json = json.dumps(article.get('categories'))
            
            # Build the insert statement
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            
            cursor.execute(f'''
                INSERT INTO processed_articles ({column_names})
                VALUES ({placeholders})
                ON CONFLICT (url) DO UPDATE 
                SET 
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    categories = EXCLUDED.categories,
                    total_score = EXCLUDED.total_score,
                    processed_at = NOW()
            ''', (
                article.get('url'), 
                article.get('title'), 
                article.get('content'), 
                article.get('author'), 
                article.get('doi'), 
                categories_json,
                article.get('total_score')
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving processed article to NeonDB: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the databases."""
        stats = {}
        
        # Stats from raw_articles (SQLite)
        try:
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM raw_articles')
            total_raw = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM raw_articles WHERE processed = 1')
            processed_raw = cursor.fetchone()[0]
            
            conn.close()
            
            stats['raw_articles_total'] = total_raw
            stats['raw_articles_processed'] = processed_raw
            stats['raw_articles_unprocessed'] = total_raw - processed_raw
        except Exception as e:
            logger.warning(f"Could not get raw article stats: {e}")
            
        # Stats from processed_articles
        if self.neon_db_url:
            try:
                import psycopg2
                conn = psycopg2.connect(self.neon_db_url)
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM processed_articles')
                total_processed = cursor.fetchone()[0]
                
                conn.close()
                stats['processed_articles_source'] = 'PostgreSQL (NeonDB)'
                stats['processed_articles_total'] = total_processed
            except Exception as e:
                logger.warning(f"Could not get NeonDB stats: {e}")
                stats['processed_articles_source'] = 'NeonDB Error'
                stats['processed_articles_total'] = 0
        else:
            stats['processed_articles_source'] = 'Not Configured'
            stats['processed_articles_total'] = 0
                
        return stats

    def search_articles(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search processed articles by title/content/author and order by score."""
        articles = []
        
        if not self.neon_db_url:
            logger.error("No NeonDB URL configured. Cannot search articles.")
            return []
        
        # Simple wildcard search prep
        search_term = f'%{query.lower()}%'
        
        try:
            # PostgreSQL (using psycopg2)
            import psycopg2
            conn = psycopg2.connect(self.neon_db_url)
            cursor = conn.cursor()
            
            cursor.execute(f'''
                SELECT * FROM processed_articles 
                WHERE LOWER(title) LIKE %s OR LOWER(content) LIKE %s OR LOWER(author) LIKE %s
                ORDER BY total_score DESC, processed_at DESC
                LIMIT %s
            ''', (search_term, search_term, search_term, limit))
            
            columns = [desc[0] for desc in cursor.description]
            articles = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            
            return articles
            
        except Exception as e:
            logger.error(f"Error searching processed articles: {e}")
            return []

    def get_articles(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Fetch processed articles ordered by score and date."""
        articles = []
        
        if not self.neon_db_url:
            logger.error("No NeonDB URL configured. Cannot fetch articles.")
            return []
            
        try:
            # PostgreSQL
            import psycopg2
            conn = psycopg2.connect(self.neon_db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM processed_articles 
                ORDER BY total_score DESC, processed_at DESC
                LIMIT %s OFFSET %s
            ''', (limit, offset))
            
            columns = [desc[0] for desc in cursor.description]
            articles = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching processed articles: {e}")
            return []
        

def get_unprocessed_articles(self, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch a batch of articles that have not yet been processed."""
    articles = []
    try:
        conn = sqlite3.connect(self.sqlite_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM raw_articles 
            WHERE processed = 0 
            LIMIT ?
        ''', (limit,))
        
        articles = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        logger.info(f"Retrieved {len(articles)} unprocessed articles")
    except Exception as e:
        logger.error(f"Error fetching unprocessed articles: {e}")
        
    return articles


def mark_articles_as_processed(self, article_ids: List[int]):
    """Mark a list of articles in the raw_articles table as processed."""
    if not article_ids:
        return
    
    try:
        conn = sqlite3.connect(self.sqlite_db)
        cursor = conn.cursor()
        
        # Use parameterized query with IN clause
        placeholders = ','.join(['?'] * len(article_ids))
        query = f'''
            UPDATE raw_articles 
            SET processed = 1 
            WHERE id IN ({placeholders})
        '''
        
        cursor.execute(query, article_ids)
        conn.commit()
        conn.close()
        logger.info(f"Marked {len(article_ids)} articles as processed")
    except Exception as e:
        logger.error(f"Error marking articles as processed: {e}")