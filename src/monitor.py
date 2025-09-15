import os
import json
import logging
from datetime import datetime, timezone
from scrapers.binance_scraper import BinanceScraper
from scrapers.coinbase_scraper import CoinbaseScraper
from scrapers.bybit_scraper import BybitScraper
from scrapers.kraken_scraper import KrakenScraper
from telegram_bot import TelegramBot

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ListingMonitor:
    def __init__(self):
        self.telegram_bot = TelegramBot()
        self.cache_file = 'cache/previous_listings.json'
        self.previous_listings = self.load_cache()
        
        # Initialize scrapers with priority order
        self.scrapers = {
            'binance': BinanceScraper(),
            'coinbase': CoinbaseScraper(), 
            'bybit': BybitScraper(),
            'kraken': KrakenScraper()
        }
    
    def load_cache(self):
        """Load previous listings from cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
        return {}
    
    def save_cache(self, listings):
        """Save current listings to cache"""
        try:
            os.makedirs('cache', exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(listings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_listing_key(self, listing):
        """Generate unique key for listing"""
        return f"{listing['exchange']}_{listing['token']}_{listing.get('date', 'unknown')}"
    
    def is_new_listing(self, listing):
        """Check if listing is new"""
        key = self.get_listing_key(listing)
        return key not in self.previous_listings
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting listing monitor...")
        
        all_listings = {}
        new_listings = []
        
        # Scrape all exchanges
        for exchange_name, scraper in self.scrapers.items():
            try:
                logger.info(f"Scraping {exchange_name}...")
                listings = scraper.get_upcoming_listings()
                
                for listing in listings:
                    listing['exchange'] = exchange_name
                    key = self.get_listing_key(listing)
                    all_listings[key] = listing
                    
                    if self.is_new_listing(listing):
                        new_listings.append(listing)
                        logger.info(f"New listing found: {listing['token']} on {exchange_name}")
                
            except Exception as e:
                logger.error(f"Error scraping {exchange_name}: {e}")
                continue
        
        # Send alerts for new listings
        if new_listings:
            # Sort by priority (Binance first, then Coinbase)
            priority_order = {'binance': 1, 'coinbase': 2, 'bybit': 3, 'kraken': 4}
            new_listings.sort(key=lambda x: priority_order.get(x['exchange'], 5))
            
            for listing in new_listings:
                try:
                    self.telegram_bot.send_listing_alert(listing)
                    logger.info(f"Alert sent for {listing['token']} on {listing['exchange']}")
                except Exception as e:
                    logger.error(f"Error sending alert: {e}")
        else:
            logger.info("No new listings found")
        
        # Update cache
        self.save_cache(all_listings)
        logger.info(f"Monitor completed. Found {len(new_listings)} new listings")

if __name__ == "__main__":
    try:
        monitor = ListingMonitor()
        monitor.run()
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        raise
