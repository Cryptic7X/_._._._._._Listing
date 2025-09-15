import requests
import feedparser
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

class BybitScraper:
    def __init__(self):
        self.base_url = "https://announcements.bybit.com"
        self.listings_url = "https://announcements.bybit.com/en/?category=new_crypto"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_upcoming_listings(self):
        """Scrape Bybit announcements for upcoming listings"""
        listings = []
        
        try:
            response = requests.get(self.listings_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Parse JSON response if available, otherwise HTML
            try:
                data = response.json()
                listings = self.parse_json_announcements(data)
            except:
                # Fallback to HTML parsing
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                listings = self.parse_html_announcements(soup)
                
        except Exception as e:
            logger.error(f"Error scraping Bybit: {e}")
        
        return listings
    
    def parse_json_announcements(self, data):
        """Parse JSON announcement data"""
        listings = []
        
        try:
            announcements = data.get('result', {}).get('list', [])
            
            for announcement in announcements[:5]:
                title = announcement.get('title', '')
                
                if self.is_listing_announcement(title):
                    listing_data = self.parse_announcement_data(announcement)
                    if listing_data:
                        listings.append(listing_data)
                        
        except Exception as e:
            logger.error(f"Error parsing Bybit JSON: {e}")
        
        return listings
    
    def parse_html_announcements(self, soup):
        """Parse HTML announcement data"""
        listings = []
        
        try:
            # Find announcement items
            announcements = soup.find_all('div', class_='announcement-item') or soup.find_all('article')
            
            for announcement in announcements[:5]:
                title_elem = announcement.find('h2') or announcement.find('h3') or announcement.find('a')
                if not title_elem:
                    continue
                
                title = title_elem.get_text().strip()
                
                if self.is_listing_announcement(title):
                    url_elem = announcement.find('a', href=True)
                    url = url_elem.get('href') if url_elem else ""
                    
                    if url and not url.startswith('http'):
                        url = self.base_url + url
                    
                    listing_data = self.parse_listing_announcement(title, url)
                    if listing_data:
                        listings.append(listing_data)
                        
        except Exception as e:
            logger.error(f"Error parsing Bybit HTML: {e}")
        
        return listings
    
    def is_listing_announcement(self, title):
        """Check if title indicates a listing announcement"""
        listing_keywords = [
            'new listing',
            'will list',
            'listing announcement',
            'now supports',
            'available for trading',
            'new token'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in listing_keywords)
    
    def parse_listing_announcement(self, title, url):
        """Parse listing details from announcement"""
        try:
            # Extract token from title
            token_match = re.search(r'([A-Z]{2,10})', title)
            if not token_match:
                return None
            
            token = token_match.group(1)
            
            return {
                'token': token,
                'name': None,
                'date': None,
                'pairs': [f'{token}/USDT'],  # Common Bybit pair
                'url': url,
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                'title': title
            }
            
        except Exception as e:
            logger.error(f"Error parsing Bybit announcement: {e}")
            return None
    
    def parse_announcement_data(self, announcement):
        """Parse individual announcement from JSON data"""
        try:
            title = announcement.get('title', '')
            url = announcement.get('url', '')
            
            if not url.startswith('http'):
                url = self.base_url + url
            
            return self.parse_listing_announcement(title, url)
            
        except Exception as e:
            logger.error(f"Error parsing Bybit announcement data: {e}")
            return None
