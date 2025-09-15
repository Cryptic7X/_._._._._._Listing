import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class BinanceScraper:
    def __init__(self):
        self.base_url = "https://www.binance.com"
        self.announcements_url = "https://www.binance.com/en/support/announcement/c-48?navId=48"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_upcoming_listings(self):
        """Scrape Binance announcements for upcoming listings"""
        listings = []
        
        try:
            response = requests.get(self.announcements_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for announcement links
            announcement_links = soup.find_all('a', href=True)
            
            for link in announcement_links[:10]:  # Check first 10 announcements
                href = link.get('href')
                title = link.get_text().strip()
                
                if not href or not title:
                    continue
                
                # Check if it's a listing announcement
                if self.is_listing_announcement(title):
                    full_url = self.base_url + href if href.startswith('/') else href
                    listing_data = self.parse_listing_announcement(title, full_url)
                    
                    if listing_data:
                        listings.append(listing_data)
            
        except Exception as e:
            logger.error(f"Error scraping Binance: {e}")
        
        return listings
    
    def is_listing_announcement(self, title):
        """Check if title indicates a listing announcement"""
        listing_keywords = [
            'binance will list',
            'will list',
            'new listing',
            'listing announcement',
            'will be listed'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in listing_keywords)
    
    def parse_listing_announcement(self, title, url):
        """Parse listing details from announcement"""
        try:
            # Extract token from title
            token_match = re.search(r'list\s+([A-Z]{2,10})', title, re.IGNORECASE)
            if not token_match:
                token_match = re.search(r'\(([A-Z]{2,10})\)', title)
            
            if not token_match:
                return None
            
            token = token_match.group(1).upper()
            
            # Try to get more details from the announcement page
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                content = response.text
                
                # Extract trading pairs
                pairs = self.extract_trading_pairs(content, token)
                
                # Extract listing date
                listing_date = self.extract_listing_date(content)
                
            except:
                pairs = []
                listing_date = None
            
            return {
                'token': token,
                'name': self.extract_token_name(title),
                'date': listing_date,
                'pairs': pairs,
                'url': url,
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                'title': title
            }
            
        except Exception as e:
            logger.error(f"Error parsing Binance announcement: {e}")
            return None
    
    def extract_token_name(self, title):
        """Extract full token name from title"""
        # Look for pattern like "Token Name (SYMBOL)"
        name_match = re.search(r'list\s+([^(]+)\s*\(', title, re.IGNORECASE)
        if name_match:
            return name_match.group(1).strip()
        return None
    
    def extract_trading_pairs(self, content, token):
        """Extract trading pairs from announcement content"""
        pairs = []
        
        # Common trading pair patterns
        pair_patterns = [
            f'{token}/USDT',
            f'{token}/BTC', 
            f'{token}/BNB',
            f'{token}/ETH'
        ]
        
        content_upper = content.upper()
        for pair in pair_patterns:
            if pair in content_upper:
                pairs.append(pair)
        
        return pairs
    
    def extract_listing_date(self, content):
        """Extract listing date from announcement content"""
        # Look for date patterns
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(will\s+list.*?on\s+(\d{4}-\d{2}-\d{2}))'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
