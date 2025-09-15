import os
import logging
from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
        
        if not self.bot_token or not self.channel_id:
            raise ValueError("Missing Telegram credentials in environment variables")
        
        self.bot = Bot(token=self.bot_token)
    
    def format_listing_alert(self, listing):
        """Format listing alert message"""
        exchange = listing['exchange'].upper()
        token = listing['token'].upper()
        
        # Exchange-specific emojis and impact info
        exchange_info = {
            'binance': {
                'emoji': '🔥',
                'impact': '41% avg price increase',
                'priority': 'HIGHEST PRIORITY'
            },
            'coinbase': {
                'emoji': '🏛️', 
                'impact': '91% avg in first 5 days',
                'priority': 'INSTITUTIONAL IMPACT'
            },
            'bybit': {
                'emoji': '⚡',
                'impact': 'High volume exchange',
                'priority': 'DERIVATIVES FOCUS'
            },
            'kraken': {
                'emoji': '📈',
                'impact': 'Regulated exchange',
                'priority': 'EU COMPLIANT'
            }
        }
        
        info = exchange_info.get(listing['exchange'], {
            'emoji': '📊',
            'impact': 'Exchange listing',
            'priority': 'STANDARD'
        })
        
        # Build message
        message = f"{info['emoji']} **{exchange} LISTING ALERT**\n\n"
        message += f"**Token**: ${token}"
        
        if 'name' in listing and listing['name']:
            message += f" ({listing['name']})"
        
        message += f"\n**Exchange**: {exchange}"
        message += f"\n**Priority**: {info['priority']}"
        
        if 'date' in listing and listing['date']:
            message += f"\n**Listing Date**: {listing['date']}"
        
        if 'pairs' in listing and listing['pairs']:
            pairs = ', '.join(listing['pairs']) if isinstance(listing['pairs'], list) else listing['pairs']
            message += f"\n**Trading Pairs**: {pairs}"
        
        message += f"\n**Expected Impact**: {info['impact']}"
        
        if 'url' in listing and listing['url']:
            message += f"\n\n[📋 Official Announcement]({listing['url']})"
        
        # Add timestamp
        message += f"\n\n🕐 Alert Time: {listing.get('timestamp', 'Unknown')}"
        
        return message
    
    async def send_listing_alert(self, listing):
        """Send listing alert to Telegram channel"""
        try:
            message = self.format_listing_alert(listing)
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            
            logger.info(f"Alert sent successfully for {listing['token']}")
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            # Try without markdown if formatting fails
            try:
                simple_message = f"🔥 NEW LISTING: {listing['token']} on {listing['exchange'].upper()}"
                if 'url' in listing:
                    simple_message += f"\nLink: {listing['url']}"
                
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=simple_message
                )
                logger.info("Sent simplified alert")
            except Exception as e2:
                logger.error(f"Failed to send simplified alert: {e2}")
                raise
    
    def send_listing_alert(self, listing):
        """Synchronous wrapper for async send method"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.send_listing_alert_async(listing))
        finally:
            loop.close()
    
    async def send_listing_alert_async(self, listing):
        """Async version of send_listing_alert"""
        await self.send_listing_alert(listing)
