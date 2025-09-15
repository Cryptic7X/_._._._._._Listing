import os
import logging
from telegram import Bot
from telegram.constants import ParseMode
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
        
        if not self.bot_token or not self.channel_id:
            raise ValueError("Missing Telegram credentials in environment variables")
        
        self.bot = Bot(token=self.bot_token)
    
    def format_listing_alert(self, listing):
        """Format listing alert message with rich formatting"""
        exchange = listing['exchange'].upper()
        token = listing['token'].upper()
        
        # Get exchange-specific info
        from coinmarketcal_client import CoinMarketCalClient
        client = CoinMarketCalClient()
        exchange_info = client.get_exchange_info(listing['exchange'])
        
        emoji = exchange_info['emoji']
        impact = exchange_info['impact']
        
        # Determine priority level
        priority_map = {
            'binance': 'HIGHEST PRIORITY',
            'coinbase': 'INSTITUTIONAL IMPACT',
            'coinbase pro': 'INSTITUTIONAL IMPACT', 
            'bybit': 'DERIVATIVES FOCUS',
            'kraken': 'EU REGULATED'
        }
        
        priority = priority_map.get(listing['exchange'], 'STANDARD')
        
        # Build message
        message = f"{emoji} **{exchange} UPCOMING LISTING**\n\n"
        message += f"**Token**: ${token}"
        
        if listing.get('name'):
            message += f" ({listing['name']})"
        
        message += f"\n**Exchange**: {exchange}"
        message += f"\n**Priority**: {priority}"
        
        if listing.get('date') and listing['date'] != 'TBA':
            message += f"\n**Listing Date**: {listing['date']}"
        else:
            message += f"\n**Listing Date**: To Be Announced"
        
        if listing.get('pairs'):
            pairs = ', '.join(listing['pairs'])
            message += f"\n**Trading Pairs**: {pairs}"
        
        message += f"\n**Expected Impact**: {impact}"
        
        # Add confidence score
        if listing.get('confidence'):
            confidence = listing['confidence']
            confidence_emoji = "🔥" if confidence >= 80 else "📈" if confidence >= 60 else "⚠️"
            message += f"\n**Confidence**: {confidence_emoji} {confidence}%"
        
        # Add links
        if listing.get('url'):
            message += f"\n\n[📋 Event Details]({listing['url']})"
        
        # Add source and timestamp
        message += f"\n\n📊 Source: {listing.get('source', 'CoinMarketCal')}"
        message += f"\n🕐 Alert Time: {listing.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M UTC'))}"
        
        return message
    
    async def send_listing_alert_async(self, listing):
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
                exchange = listing['exchange'].upper()
                token = listing['token'].upper()
                date = listing.get('date', 'TBA')
                confidence = listing.get('confidence', 'Unknown')
                
                simple_message = f"🔥 UPCOMING LISTING ALERT\n"
                simple_message += f"Token: ${token}\n"
                simple_message += f"Exchange: {exchange}\n"
                simple_message += f"Date: {date}\n"
                simple_message += f"Confidence: {confidence}%"
                
                if listing.get('url'):
                    simple_message += f"\nDetails: {listing['url']}"
                
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
        
        # Handle different Python versions and event loops
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            if loop.is_running():
                # If loop is running, schedule the coroutine
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.send_listing_alert_async(listing))
                    )
                    future.result()
            else:
                # If no loop is running, run directly
                loop.run_until_complete(self.send_listing_alert_async(listing))
        except Exception as e:
            logger.error(f"Error in synchronous wrapper: {e}")
            # Final fallback - create new loop
            new_loop = asyncio.new_event_loop()
            try:
                new_loop.run_until_complete(self.send_listing_alert_async(listing))
            finally:
                new_loop.close()
