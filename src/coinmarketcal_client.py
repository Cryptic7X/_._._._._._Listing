import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from dateutil import parser

logger = logging.getLogger(__name__)

class CoinMarketCalClient:
    def __init__(self):
        self.api_key = os.getenv('COINMARKETCAL_API_KEY')
        if not self.api_key:
            raise ValueError("COINMARKETCAL_API_KEY environment variable is required")
        
        self.base_url = "https://developers.coinmarketcal.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        
        # Priority exchanges mapping
        self.priority_exchanges = {
            'binance': {'priority': 1, 'emoji': '🔥', 'impact': '41% avg price increase'},
            'coinbase': {'priority': 2, 'emoji': '🏛️', 'impact': '91% avg in first 5 days'},  
            'coinbase pro': {'priority': 2, 'emoji': '🏛️', 'impact': '91% avg in first 5 days'},
            'bybit': {'priority': 3, 'emoji': '⚡', 'impact': 'High volume derivatives'},
            'kraken': {'priority': 4, 'emoji': '📈', 'impact': 'Regulated EU exchange'}
        }
    
    def get_upcoming_listings(self, days_ahead=7):
        """Get upcoming exchange listings from CoinMarketCal"""
        listings = []
        
        try:
            # Calculate date range
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=days_ahead)
            
            params = {
                'dateRangeStart': start_date.strftime('%Y-%m-%d'),
                'dateRangeEnd': end_date.strftime('%Y-%m-%d'),
                'page': 1,
                'max': 50
            }
            
            response = requests.get(
                f"{self.base_url}/events",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Retrieved {len(data.get('body', []))} events from CoinMarketCal")
            
            # Process events
            for event in data.get('body', []):
                if self.is_exchange_listing(event):
                    listing = self.parse_listing_event(event)
                    if listing and self.is_priority_exchange(listing.get('exchange', '')):
                        listings.append(listing)
            
            # Sort by priority (Binance first, then Coinbase, etc.)
            listings.sort(key=lambda x: self.get_exchange_priority(x.get('exchange', '')))
            
            logger.info(f"Found {len(listings)} priority exchange listings")
            
        except Exception as e:
            logger.error(f"Error fetching from CoinMarketCal API: {e}")
        
        return listings
    
    def is_exchange_listing(self, event):
        """Check if event is an exchange listing"""
        title = event.get('title', '').lower()
        description = event.get('description', '').lower()
        
        listing_keywords = [
            'listing',
            'will list',
            'lists',
            'trading pair',
            'available for trading',
            'spot trading',
            'perpetual',
            'futures'
        ]
        
        # Check title and description for listing keywords
        text_to_check = f"{title} {description}"
        
        return any(keyword in text_to_check for keyword in listing_keywords)
    
    def parse_listing_event(self, event):
        """Parse CoinMarketCal event into listing format"""
        try:
            title = event.get('title', '')
            description = event.get('description', '')
            
            # Extract exchange name from title/description
            exchange = self.extract_exchange_name(f"{title} {description}")
            
            # Extract token symbol from title
            tokens = self.extract_tokens(title)
            if not tokens:
                tokens = self.extract_tokens(description)
            
            if not tokens or not exchange:
                return None
            
            # Use first token found
            token = tokens[0]
            
            # Parse date
            date_created = event.get('date_event')
            if date_created:
                try:
                    event_date = parser.parse(date_created)
                    formatted_date = event_date.strftime('%Y-%m-%d %H:%M UTC')
                except:
                    formatted_date = date_created
            else:
                formatted_date = "TBA"
            
            # Extract trading pairs
            pairs = self.extract_trading_pairs(f"{title} {description}", token)
            
            return {
                'token': token,
                'name': event.get('coins', [{}])[0].get('name') if event.get('coins') else None,
                'exchange': exchange.lower(),
                'date': formatted_date,
                'pairs': pairs,
                'url': f"https://coinmarketcal.com/en/event/{event.get('id', '')}",
                'title': title,
                'description': description,
                'confidence': event.get('percentage', 0),
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
                'source': 'CoinMarketCal'
            }
            
        except Exception as e:
            logger.error(f"Error parsing listing event: {e}")
            return None
    
    def extract_exchange_name(self, text):
        """Extract exchange name from text"""
        text_lower = text.lower()
        
        # Check for exchange names (order matters - check longer names first)
        exchanges = [
            'coinbase pro', 'coinbase', 'binance', 'bybit', 'kraken',
            'kucoin', 'huobi', 'okx', 'gate.io', 'bitget', 'mexc'
        ]
        
        for exchange in exchanges:
            if exchange in text_lower:
                return exchange
        
        return None
    
    def extract_tokens(self, text):
        """Extract token symbols from text"""
        import re
        
        # Look for token patterns
        patterns = [
            r'\b([A-Z]{2,8})\b',  # Uppercase letters 2-8 chars
            r'\$([A-Z]{2,8})\b',  # $TOKEN format
            r'\(([A-Z]{2,8})\)'   # (TOKEN) format
        ]
        
        tokens = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            tokens.extend(matches)
        
        # Filter out common false positives
        false_positives = {
            'USD', 'EUR', 'GBP', 'BTC', 'ETH', 'USDT', 'USDC', 
            'API', 'NEW', 'THE', 'AND', 'FOR', 'UTC', 'GMT', 'UTC'
        }
        
        # Keep tokens that are 2-6 characters and not false positives
        valid_tokens = []
        for token in tokens:
            if 2 <= len(token) <= 6 and token not in false_positives:
                valid_tokens.append(token)
        
        return list(dict.fromkeys(valid_tokens))  # Remove duplicates while preserving order
    
    def extract_trading_pairs(self, text, token):
        """Extract trading pairs from text"""
        import re
        
        pairs = []
        text_upper = text.upper()
        
        # Common quote currencies
        quote_currencies = ['USDT', 'USDC', 'BTC', 'ETH', 'BNB', 'USD', 'EUR']
        
        for quote in quote_currencies:
            pair_pattern = f"{token}/{quote}"
            if pair_pattern in text_upper:
                pairs.append(pair_pattern)
        
        # If no pairs found, add common defaults
        if not pairs:
            pairs = [f"{token}/USDT", f"{token}/BTC"]
        
        return pairs
    
    def is_priority_exchange(self, exchange):
        """Check if exchange is in our priority list"""
        return exchange.lower() in self.priority_exchanges
    
    def get_exchange_priority(self, exchange):
        """Get priority number for sorting"""
        return self.priority_exchanges.get(exchange.lower(), {}).get('priority', 999)
    
    def get_exchange_info(self, exchange):
        """Get exchange emoji and impact info"""
        return self.priority_exchanges.get(exchange.lower(), {
            'emoji': '📊',
            'impact': 'Exchange listing'
        })
