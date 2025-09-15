import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import logging
import json

logger = logging.getLogger(__name__)

class CoinbaseScraper:
    def __init__(self):
        self.base_url = "https://www.coinbase.com"
        self.blog_url = "https://blog.coinbase.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_upcoming_listings(self):
        """Scrape Coinbase for upcoming listings"""
        listings = []
        
        # Check multiple sources
        listings.extend(self.check_blog_announcements())
        listings.extend(self.check_twitter_api())
        
        return listings
    
    def check_blog_announcements(self):
        """Check Coinbase blog for listing announcements"""
        listings = []
        
        try:
            # Coinbase blog search for listing announcements
            search_url = f"{self.blog_url}/tagged/new-assets"
            response = requests.get(search_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article links
            articles = soup.find_all('article') or soup.find_all('a', href=True)
            
            for article in articles[:5]:  # Check latest 5 articles
                try:
                    title_elem = article.find('h2') or article.find('h3') or article
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text().strip()
                    
                    if self.is_listing_announcement(title):
                        link_elem = article.find('a', href=True) or article
                        url = link_elem.get('href') if link_elem else ""
                        
                        if url and not url.startswith('http'):
                            url = self.blog_url + url
                        
                        listing_data = self.parse_listing_announcement(title, url)
                        if listing_data:
                            listings.append(listing_data)
                            
                except Exception as e:
                    logger.debug(f"Error parsing Coinbase article: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error checking Coinbase blog: {e}")
        
        return listings
    
    def check_twitter_api(self):
        """Check for Coinbase Assets Twitter announcements"""
        # Note: This would require Twitter API access
        # For now, we'll simulate checking recent announcements
        listings = []
        
        try:
            # This is a placeholder - you would need Twitter API credentials
            # For demonstration, we'll check Coinbase's public announcements
            pass
            
        except Exception as e:
            logger.debug(f"Twitter API not available: {e}")
        
        return listings
    
    def is_listing_announcement(self, title):
        """Check if title indicates a listing announcement"""
        listing_keywords = [
            'now available',
            'new asset',
            'adding support',
            'now supports',
            'available on coinbase',
            'listing',
            'new digital asset'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in listing_keywords)
    
    def parse_listing_announcement(self, title, url):
        """Parse listing details from announcement"""
        try:
            # Extract token symbols from title
            tokens = self.extract_tokens_from_title(title)
            
            if not tokens:
                return None
            
            # For multiple tokens, create separate listings
            results = []
            for token in tokens:
                listing_data = {
                    'token': token,
                    'name': self.extract_token_name(title, token),
                    'date': None,  # Coinbase often doesn't announce exact times
                    'pairs': [f'{token}/USD', f'{token}/EUR'],  # Common Coinbase pairs
                    'url': url,
                    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                    'title': title
                }
                results.append(listing_data)
                
            return results[0] if len(results) == 1 else results
            
        except Exception as e:
            logger.error(f"Error parsing Coinbase announcement: {e}")
            return None
    
    def extract_tokens_from_title(self, title):
        """Extract token symbols from title"""
        tokens = []
        
        # Look for patterns like (TOKEN), TOKEN, or $TOKEN
        patterns = [
            r'\(([A-Z]{2,6})\)',  # (BTC)
            r'\b([A-Z]{2,6})\b',   # BTC
            r'\$([A-Z]{2,6})\b'    # $BTC
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, title.upper())
            for match in matches:
                if len(match) >= 2 and len(match) <= 6:
                    tokens.append(match)
        
        # Remove common false positives
        false_positives = ['USD', 'EUR', 'GBP', 'API', 'NEW', 'THE', 'AND', 'FOR']
        tokens = [token for token in tokens if token not in false_positives]
        
        return list(set(tokens))  # Remove duplicates
    
    def extract_token_name(self, title, token):
        """Extract full token name from title"""
        # This is challenging without the full article content
        # Return None for now, could be enhanced
        return None
