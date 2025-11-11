import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import sqlite3
from trafilatura import extract
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from backend.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSpider:
    def __init__(self):
        self.visited_urls = set()
        self.to_visit = set(Config.SEED_URLS)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': Config.USER_AGENT})
        self.domain_patterns = self._extract_domains()
        self.init_database()
    
    def _extract_domains(self):
        """Extract base domains from seed URLs"""
        domains = set()
        for url in Config.SEED_URLS:
            parsed = urlparse(url)
            domains.add(parsed.netloc)
        return domains
    
    def init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(Config.SQLITE_DB)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    content TEXT,
                    author TEXT,
                    doi TEXT,
                    html_content TEXT,
                    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def is_valid_url(self, url):
        """Check if URL is valid for crawling"""
        try:
            parsed = urlparse(url)
            
            if parsed.fragment:
                return False
            
            if not parsed.netloc:
                return False
            
            if not any(domain in parsed.netloc for domain in self.domain_patterns):
                return False
            
            excluded_extensions = [
                '.pdf', '.doc', '.docx', '.zip', '.rar', '.exe',
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'
            ]
            if any(url.lower().endswith(ext) for ext in excluded_extensions):
                return False
            
            excluded_patterns = [
                'facebook.com', 'twitter.com', 'instagram.com', 'tel:', 'mailto:',
                '/wp-content/', '/wp-includes/', '/wp-json/', 'xmlrpc.php'
            ]
            if any(pattern in url.lower() for pattern in excluded_patterns):
                return False
            
            return True
        except:
            return False

    # --- HELPER METHODS FOR DATA EXTRACTION ---

    def _get_generic_title(self, soup):
        """Get title from a standard list of selectors."""
        title = ""
        title_selectors = ['h1.h1', 'h1', '.entry-title', '.post-title', '.article-title', 'title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                if title:
                    return title
        return ""

    def _get_generic_author(self, soup):
        """Get author from a standard list of selectors."""
        author = ""
        author_selectors = [
            'meta[name="author"]', '.author', '[class*="author"]',
            'meta[property="article:author"]', '.byline', '[class*="byline"]'
        ]
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get('content') or author_elem.get_text()
                author = re.sub(r'^by\s+', '', author, flags=re.IGNORECASE).strip()
                if author:
                    return author
        return ""

    def _get_generic_doi(self, soup):
        """Get DOI from a standard list of selectors."""
        doi = ""
        doi_selectors = [
            'meta[name="citation_doi"]', 'meta[name="doi"]', '[class*="doi"]',
            'meta[property="citation_doi"]'
        ]
        for selector in doi_selectors:
            doi_elem = soup.select_one(selector)
            if doi_elem:
                doi = doi_elem.get('content') or doi_elem.get_text()
                doi = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', doi, re.IGNORECASE)
                if doi:
                    return doi.group()
        return ""


    def extract_article_data(self, html, url):
        """
        Extract structured article data with site-specific rules.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            parsed_url = urlparse(url)
            
            title = ""
            content = ""
            author = ""
            doi = ""

            # --- Rule for guimaras.gov.ph ---
            if 'guimaras.gov.ph' in parsed_url.netloc:
                # First, check if this is a list page (like /news-updates/)
                if soup.select_one('div.col-md-4.n-a-u-page'):
                    logger.info(f"Skipping non-article page (archive/list): {url}")
                    return None

                # Primary extraction: Get title from H1 and content from the main div
                title_elem = soup.select_one('section.nau-single-page-content h1')
                if title_elem:
                    title = title_elem.get_text().strip()

                content_container = soup.select_one('div.nau-single-col')
                if content_container:
                    if title_elem:
                        title_elem.decompose()
                    
                    # Extract all paragraph text from the cleaned container and join
                    paragraphs = content_container.find_all('p')
                    content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
                
                # Fallback to OG meta tags if primary title extraction failed
                if not title:
                    title_elem = soup.select_one('meta[property="og:title"]')
                    if title_elem:
                        title = title_elem.get('content', '').strip()
                
                # Fallback to OG meta tags if primary content extraction failed
                if not content:
                    content_elem = soup.select_one('meta[property="og:description"]')
                    if content_elem:
                        content = content_elem.get('content', '').strip()
            
            # --- Rule for gsu.edu.ph ---
            elif 'gsu.edu.ph' in parsed_url.netloc and 'cst.gsu.edu.ph' not in parsed_url.netloc:
                body_tag = soup.find('body')
                # Check if it's a single article page (not an archive/list page)
                if body_tag and 'single-post' in body_tag.get('class', []):
                    title = self._get_generic_title(soup)
                    author = self._get_generic_author(soup)
                    doi = self._get_generic_doi(soup)
                    
                    # Extract content ONLY from the main article body
                    content_div = soup.select_one('div.entry-content')
                    if content_div:
                        # Remove known junk *within* the content div (like iframes, share buttons)
                        junk_in_content = ['iframe', '.d-flex.align-items-center.justify-content-center']
                        for selector in junk_in_content:
                            for element in content_div.select(selector):
                                element.decompose()

                        content = content_div.get_text(separator=' ', strip=True)
                    
                    # If content is still empty (e.g., page was just an iframe),
                    # trafilatura will also find nothing, which is correct.
                    if not content:
                         content = self._extract_generic_content(html, content_div)

                else:
                    # This is a list page (like /2024/page/2/), not an article
                    logger.info(f"Skipping non-article page (archive/list): {url}")
                    return None

            # --- FIXED RULE for cst.gsu.edu.ph
            elif 'cst.gsu.edu.ph' in parsed_url.netloc:
                if soup.select_one('ul.wp-block-post-template'):
                    logger.info(f"Skipping list/archive page for cst.gsu.edu.ph: {url}")
                    return None
                else:
                    # This is an ARTICLE PAGE - extract content
                    logger.info(f"Processing CST article page: {url}")
                    
                    # Extract title
                    title = self._get_generic_title(soup)
                    
                    # Extract content using generic method
                    content = self._extract_generic_content(html)
                    
                    # Extract author and DOI
                    author = self._get_generic_author(soup)
                    doi = self._get_generic_doi(soup)
                    
                    logger.info(f"CST Article extracted - Title: {title[:50]}, Content length: {len(content)}")

            # --- Default Rule (for deped.sdguimaras.com and others) ---
            else:
                title = self._get_generic_title(soup)
                author = self._get_generic_author(soup)
                doi = self._get_generic_doi(soup)
                content = self._extract_generic_content(html)

            # Final validation - ensure we have enough content
            if not content or len(content.strip()) < 50:
                logger.info(f"Insufficient content extracted from {url}")
                return None
                
            if not title or len(title.strip()) < 5:
                logger.info(f"Insufficient title extracted from {url}")
                return None

            return {
                'title': title,
                'content': content or "",
                'author': author,
                'doi': doi,
                'html_content': html
            }

        except Exception as e:
            logger.error(f"Error extracting article data from {url}: {e}")
            return None

    def _extract_generic_content(self, html, content_node=None):
        """Generic content extraction fallback using pre-cleaning and trafilatura."""
        
        # If a specific content node (like div.entry-content) was passed, use it.
        if content_node:
            target_html = str(content_node)
        else:
            # Otherwise, pre-clean the whole body
            soup_for_content = BeautifulSoup(html, 'html.parser')
            junk_selectors = [
                'header', 'footer', '.footer', '.footer-links', '.site-footer', 'section.section-subfooter',
                'nav', '.nav', '.navbar', '#navbar', '.primary-menu-nav', '.sec-menu-nav', '.top-nav-bar',
                '.sidebar', '.widget-area', '#secondary',
                '.title-bar', '.pagination', '.mobile-menu-canvas', '.header',
                '.search-form', '#search-light', '.related-posts', '.post-navigation'
            ]
            for selector in junk_selectors:
                for element in soup_for_content.select(selector):
                    element.decompose()
            target_html = str(soup_for_content)

        content = extract(target_html,
                          include_links=False,
                          include_tables=False,
                          include_images=False,
                          favor_precision=True)
        return content
    
    def save_article(self, url, article_data):
        """Save article to SQLite database"""
        try:
            conn = sqlite3.connect(Config.SQLITE_DB)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO raw_articles 
                (url, title, content, author, doi, html_content)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                url, 
                article_data['title'], 
                article_data['content'], 
                article_data['author'], 
                article_data['doi'], 
                article_data['html_content']
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving article {url}: {e}")
            return False
    
    def extract_links(self, html, base_url):
        """Extract all valid links from page based on site-specific rules"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = set()
            parsed_base = urlparse(base_url)

            # Rule for guimaras.gov.ph
            if 'guimaras.gov.ph' in parsed_base.netloc:
                for link in soup.select('div.col-md-4.n-a-u-page > a'):
                    links.add(link.get('href'))
                for link in soup.select('div.pagination > a.page-numbers'):
                    links.add(link.get('href'))

            elif 'cst.gsu.edu.ph' in parsed_base.netloc:
                if soup.select_one('ul.wp-block-post-template'):
                    logger.info(f"Extracting links from CST list page: {base_url}")
                    
                    # Extract article links from the post template
                    for link in soup.select('ul.wp-block-post-template h2.wp-block-post-title a'):
                        href = link.get('href')
                        if href:
                            links.add(href)
                    
                    # Extract pagination links
                    next_page_link = soup.select_one('a.wp-block-query-pagination-next')
                    if next_page_link:
                        href = next_page_link.get('href')
                        if href:
                            links.add(href)
                            logger.info(f"Found next page: {href}")
                    
                    # Also check for any pagination links in the navigation
                    for link in soup.select('nav.wp-block-query-pagination a'):
                        href = link.get('href')
                        if href and href not in links:
                            links.add(href)
                    
                    logger.info(f"CST List Page: Found {len(links)} links from {base_url}")
                else:
                    pass

            # Rule for gsu.edu.ph (main site)
            elif 'gsu.edu.ph' in parsed_base.netloc and 'cst.gsu.edu.ph' not in parsed_base.netloc:
                # Find article links (from list pages)
                for link in soup.select('article.post header.entry-header h2.h2 > a'):
                    links.add(link.get('href'))
                # Find pagination links
                for link in soup.select('nav.navigation.pagination div.nav-links > a.page-numbers'):
                    links.add(link.get('href'))
                # Find "Next/Prev" links on single article pages
                for link in soup.select('nav.post-navigation a[rel="prev"], nav.post-navigation a[rel="next"]'):
                    links.add(link.get('href'))
            
            # Rule for deped.sdguimaras.com
            elif 'deped.sdguimaras.com' in parsed_base.netloc:
                form = soup.select_one('form[id="viewNewsForm"]')
                action = form.get('action', 'news_view') if form else 'news_view'
                for button in soup.select('button.news_title[name="news_id"]'):
                    news_id = button.get('value')
                    if news_id:
                        links.add(f"{action}?news_id={news_id}")

                pagination_form = soup.select_one('form[action="news"][method="get"]')
                if pagination_form:
                    action = pagination_form.get('action', 'news')
                    cur_limit_input = pagination_form.select_one('input[name="cur_limit"]')
                    if cur_limit_input:
                        limit_val = cur_limit_input.get('value')
                        if limit_val:
                            links.add(f"{action}?cur_limit={limit_val}")

            final_links = set()
            for link in links:
                if not link:
                    continue
                
                full_url = urljoin(base_url, link)
                
                if self.is_valid_url(full_url) and full_url not in self.visited_urls:
                    final_links.add(full_url)
            
            if final_links:
                logger.info(f"Found {len(final_links)} new links from {base_url}")
            return final_links
        
        except Exception as e:
            logger.error(f"Error extracting links from {base_url}: {e}")
            return set()
    
    def crawl_page(self, url):
        """Crawl a single page"""
        try:
            if url in self.visited_urls:
                return set()
            
            logger.info(f"Crawling: {url}")
            self.visited_urls.add(url)
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type:
                logger.warning(f"Skipping non-HTML content at: {url}")
                return set()
            
            article_data = self.extract_article_data(response.text, url)
            
            if (article_data and 
                article_data['content'] and 
                len(article_data['content']) > 20):
                
                self.save_article(url, article_data)
                logger.info(f"Saved article: {article_data['title'][:60]}...")
            elif article_data is None:
                pass
            else:
                logger.info(f"No content extracted or content too short: {url}")
            
            new_links = self.extract_links(response.text, url)
            return new_links
            
        except requests.RequestException as e:
            logger.error(f"Request error crawling {url}: {e}")
            return set()
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return set()
    
    def start_crawling(self):
        """Start the crawling process"""
        logger.info(f"Starting crawler with {len(self.to_visit)} seed URLs")
        logger.info(f"Max workers: {Config.MAX_WORKERS}, Max pages: {Config.MAX_PAGES}")
        
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            while self.to_visit and len(self.visited_urls) < Config.MAX_PAGES:
                current_batch = list(self.to_visit)[:Config.MAX_WORKERS * 5]
                self.to_visit.difference_update(current_batch)
                
                future_to_url = {
                    executor.submit(self.crawl_page, url): url 
                    for url in current_batch
                    if url not in self.visited_urls
                }
                
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        new_links = future.result()
                        for link in new_links:
                            if link not in self.visited_urls and link not in self.to_visit:
                                self.to_visit.add(link)
                    except Exception as e:
                        logger.error(f"Error processing {url}: {e}")
                
                time.sleep(Config.CRAWL_DELAY)
                
                logger.info(f"Progress: {len(self.visited_urls)} pages visited, {len(self.to_visit)} in queue")
        
        logger.info(f"Crawling completed. Visited {len(self.visited_urls)} pages.")