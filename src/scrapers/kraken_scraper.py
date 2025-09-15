import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

class KrakenScraper:
    def __init__(self):
        self.base_url = "https://www.kraken.com"
        self.listings_url = "https://www.kraken.com/listings"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_upcoming_listings(self):
        """Scrape Kraken listings page for upcoming tokens"""
        listings = []
        
        try:
            response = requests.get(self.listings_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for upcoming listings section
            upcoming_sections = soup.find_all(['div', 'section'], class_=re.compile(r'upcoming|coming-soon|roadmap'))
            
            for section in upcoming_sections:
                tokens = self.extract_tokens_from_section(section)
                listings.extend(tokens)
            
            # Also check for any recent announcement links
            announcement_links = soup.find_all('a', href=True)
            for link in announcement_links[:10]:
                href = link.get('href')
                text = link.get_text().strip()
                
                if self.is_listing_related(text):
                    full_url = self.base_url + href if href.startswith('/') else href
                    listing_data = self.parse_listing_link(text, full_url)
                    if listing_data:
                        listings.append(listing_data)
            
        except Exception as e:
            logger.error(f"Error scraping Kraken: {e}")
        
        return listings
    
    def extract_tokens_from_section(self, section):
        """Extract token information from a section"""
        tokens = []
        
        try:
            # Look for token symbols or names
            text_content = section.get_text()
            
            # Find potential token symbols (2-6 uppercase letters)
            token_matches = re.findall(r'\b([A-Z]{2,6})\b', text_content)
            
            for token in token_matches:
                if self.is_valid_token_symbol(token):
                    token_data = {
                        'token': token,
                        'name': None,
                        'date': None,
                        'pairs': [f'{token}/USD', f'{token}/EUR'],
                        'url': self.listings_url,
                        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                        'title': f'Kraken roadmap includes {token}'
                    }
                    tokens.append(token_data)
                    
        except Exception as e:
            logger.error(f"Error extracting tokens from Kraken section: {e}")
        
        return tokens
    
    def is_valid_token_symbol(self, token):
        """Check if token symbol is valid (not common words)"""
        invalid_tokens = [
            'USD', 'EUR', 'GBP', 'THE', 'AND', 'FOR', 'NEW', 'API',
            'FAQ', 'APP', 'WEB', 'GET', 'SET', 'ALL', 'TOP', 'NOW'
        ]
        return token not in invalid_tokens and len(token) >= 2
    
    def is_listing_related(self, text):
        """Check if link text is related to listings"""
        listing_keywords = [
            'listing',
            'new asset',
            'coming soon',
            'roadmap',
            'upcoming'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in listing_keywords)
    
    def parse_listing_link(self, text, url):
        """Parse listing information from link"""
        try:
            # Extract token if present
            token_match = re.search(r'([A-Z]{2,6})', text)
            if not token_match:
                return None
            
            token = token_match.group(1)
            
            if not self.is_valid_token_symbol(token):
                return None
            
            return {
                'token': token,
                'name': None,
                'date': None,
                'pairs': [f'{token}/USD', f'{token}/EUR'],
                'url': url,
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                'title': text
            }
            
        except Exception as e:
            logger.error(f"Error parsing Kraken listing link: {e}")
            return None
