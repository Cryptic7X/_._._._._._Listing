import os
import json
import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode
import re
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceListingBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
        self.bot = Bot(token=self.bot_token)
        self.cache_file = 'cache.json'
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def load_cache(self):
        """Load previous announcements"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_cache(self, data):
        """Save current announcements"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_binance_announcements(self):
        """Get Binance listing announcements"""
        url = "https://www.binance.com/en/support/announcement/c-48?navId=48"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            announcements = []
            
            # Find announcement links
            links = soup.find_all('a', href=True)
            
            for link in links[:10]:  # Check first 10
                title = link.get_text().strip()
                href = link.get('href')
                
                if self.is_listing_announcement(title):
                    full_url = f"https://www.binance.com{href}" if href.startswith('/') else href
                    
                    announcement = {
                        'title': title,
                        'url': full_url,
                        'token': self.extract_token(title),
                        'id': href.split('/')[-1] if href else title
                    }
                    
                    if announcement['token']:
                        announcements.append(announcement)
            
            logger.info(f"Found {len(announcements)} Binance listing announcements")
            return announcements
            
        except Exception as e:
            logger.error(f"Error getting Binance announcements: {e}")
            return []
    
    def is_listing_announcement(self, title):
        """Check if title is a listing announcement"""
        keywords = ['will list', 'listing', 'binance will list', 'will be listed']
        return any(keyword in title.lower() for keyword in keywords)
    
    def extract_token(self, title):
        """Extract token symbol from title"""
        # Look for patterns like "List TOKEN" or "TOKEN ("
        matches = re.findall(r'\b([A-Z]{2,8})\b', title)
        
        # Filter out common false positives
        false_positives = {'UTC', 'GMT', 'THE', 'AND', 'FOR', 'NEW'}
        tokens = [m for m in matches if m not in false_positives and len(m) >= 2]
        
        return tokens[0] if tokens else None
    
    def format_alert(self, announcement):
        """Format alert exactly like @cmcnewcoinlistingbot"""
        token = announcement['token']
        
        # Try to extract date/time from announcement page
        date_time = self.extract_listing_datetime(announcement['url'])
        
        message = f"{token} is going to be listed on Binance"
        
        if date_time:
            message += f" on {date_time}"
        
        message += ". Mark your calendars!\n\n"
        message += "#newcoinlisting\n\n"
        message += "View more details here: " + announcement['url']
        
        return message
    
    def extract_listing_datetime(self, url):
        """Extract listing date/time from announcement page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            content = response.text
            
            # Look for date patterns
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',
                r'(\d{2}:\d{2}\s+\(UTC\))',
                r'at\s+(\d{2}:\d{2}\s+UTC)'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
            
        except:
            pass
        
        return None
    
    async def send_alert(self, message):
        """Send alert to Telegram"""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                disable_web_page_preview=True
            )
            logger.info("Alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def run(self):
        """Main monitoring function"""
        logger.info("Starting Binance listing monitor...")
        
        # Load previous announcements
        previous = self.load_cache()
        
        # Get current announcements
        current_announcements = self.get_binance_announcements()
        
        # Check for new announcements
        new_announcements = []
        current_cache = {}
        
        for announcement in current_announcements:
            ann_id = announcement['id']
            current_cache[ann_id] = announcement
            
            if ann_id not in previous:
                new_announcements.append(announcement)
                logger.info(f"New listing found: {announcement['token']}")
        
        # Send alerts for new announcements
        if new_announcements:
            for announcement in new_announcements:
                message = self.format_alert(announcement)
                
                # Send alert
                asyncio.run(self.send_alert(message))
        else:
            logger.info("No new listings found")
        
        # Save current state
        self.save_cache(current_cache)
        logger.info("Monitor completed")

if __name__ == "__main__":
    bot = BinanceListingBot()
    bot.run()
