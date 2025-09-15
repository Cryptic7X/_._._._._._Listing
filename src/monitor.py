import os
import json
import logging
from datetime import datetime, timezone
from coinmarketcal_client import CoinMarketCalClient
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
        self.coinmarketcal = CoinMarketCalClient()
        self.telegram_bot = TelegramBot()
        self.cache_file = 'cache/previous_listings.json'
        self.previous_listings = self.load_cache()
    
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
    
    def filter_high_confidence_listings(self, listings):
        """Filter listings by confidence score"""
        filtered = []
        
        for listing in listings:
            confidence = listing.get('confidence', 0)
            
            # Accept listings with confidence > 60% or from high-priority exchanges
            if confidence >= 60 or listing.get('exchange') in ['binance', 'coinbase']:
                filtered.append(listing)
            else:
                logger.info(f"Filtered low confidence listing: {listing['token']} on {listing['exchange']} ({confidence}%)")
        
        return filtered
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting CoinMarketCal listing monitor...")
        
        try:
            # Get upcoming listings from CoinMarketCal
            upcoming_listings = self.coinmarketcal.get_upcoming_listings(days_ahead=7)
            
            if not upcoming_listings:
                logger.info("No upcoming listings found")
                return
            
            # Filter by confidence
            high_confidence_listings = self.filter_high_confidence_listings(upcoming_listings)
            
            # Check for new listings
            new_listings = []
            all_listings = {}
            
            for listing in high_confidence_listings:
                key = self.get_listing_key(listing)
                all_listings[key] = listing
                
                if self.is_new_listing(listing):
                    new_listings.append(listing)
                    logger.info(f"New listing found: {listing['token']} on {listing['exchange']} ({listing.get('confidence', 0)}% confidence)")
            
            # Send alerts for new listings
            if new_listings:
                logger.info(f"Sending {len(new_listings)} new listing alerts...")
                
                for listing in new_listings:
                    try:
                        self.telegram_bot.send_listing_alert(listing)
                        logger.info(f"Alert sent for {listing['token']} on {listing['exchange']}")
                        
                        # Small delay to avoid rate limiting
                        import time
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error sending alert for {listing['token']}: {e}")
            else:
                logger.info("No new listings to alert")
            
            # Update cache
            self.save_cache(all_listings)
            logger.info(f"Monitor completed. Processed {len(high_confidence_listings)} listings, sent {len(new_listings)} alerts")
            
        except Exception as e:
            logger.error(f"Monitor failed: {e}")
            raise

if __name__ == "__main__":
    try:
        monitor = ListingMonitor()
        monitor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
