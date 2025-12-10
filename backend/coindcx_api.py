"""
CoinDCX API Wrapper - Spot + Futures
====================================
"""

import hmac
import hashlib
import time
import json
import requests
from config import API_KEY, API_SECRET


class CoinDCXAPI:
    
    BASE_URL = "https://api.coindcx.com"
    PUBLIC_URL = "https://public.coindcx.com"
    
    def __init__(self):
        self.api_key = API_KEY
        self.api_secret = API_SECRET
    
    def _generate_signature(self, body):
        secret_bytes = bytes(self.api_secret, encoding='utf-8')
        body_bytes = bytes(json.dumps(body, separators=(',', ':')), encoding='utf-8')
        return hmac.new(secret_bytes, body_bytes, hashlib.sha256).hexdigest()
    
    def _make_request(self, endpoint, body=None, method="POST"):
        url = f"{self.BASE_URL}{endpoint}"
        
        if body is None:
            body = {}
        
        body['timestamp'] = int(time.time() * 1000)
        signature = self._generate_signature(body)
        
        headers = {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-SIGNATURE': signature
        }
        
        try:
            if method == "POST":
                response = requests.post(url, json=body, headers=headers, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    # ==========================================
    # PUBLIC ENDPOINTS - SPOT
    # ==========================================
    
    def get_ticker(self):
        try:
            response = requests.get(f"{self.BASE_URL}/exchange/ticker", timeout=10)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_price(self, market):
        """Get price for spot market"""
        tickers = self.get_ticker()
        
        if isinstance(tickers, dict) and "error" in tickers:
            return None
        
        for ticker in tickers:
            if ticker.get('market') == market:
                return float(ticker.get('last_price', 0))
        
        return None
    
    # ==========================================
    # PUBLIC ENDPOINTS - FUTURES / USDT PAIRS
    # ==========================================
    
    def get_futures_ticker(self):
        """Get all futures/USDT pairs"""
        try:
            # CoinDCX uses same ticker endpoint, filter USDT pairs
            response = requests.get(f"{self.BASE_URL}/exchange/ticker", timeout=10)
            data = response.json()
            
            # Filter USDT pairs
            usdt_pairs = [t for t in data if 'USDT' in t.get('market', '')]
            return usdt_pairs
        except Exception as e:
            return {"error": str(e)}
    
    def get_futures_price(self, symbol):
        """Get price for futures/USDT pair"""
        try:
            tickers = self.get_ticker()
            
            if isinstance(tickers, dict) and "error" in tickers:
                return None
            
            # Try exact match first
            for ticker in tickers:
                if ticker.get('market') == symbol:
                    return float(ticker.get('last_price', 0))
            
            # Try with B- prefix (CoinDCX format)
            for ticker in tickers:
                market = ticker.get('market', '')
                if symbol in market or market.replace('B-', '') == symbol:
                    return float(ticker.get('last_price', 0))
            
            return None
        except Exception as e:
            print(f"Error getting futures price: {e}")
            return None
    
    def get_all_prices(self):
        """Get all prices as dictionary"""
        try:
            tickers = self.get_ticker()
            prices = {}
            
            if isinstance(tickers, list):
                for ticker in tickers:
                    market = ticker.get('market', '')
                    price = float(ticker.get('last_price', 0))
                    prices[market] = price
                    
                    # Also store without B- prefix
                    if market.startswith('B-'):
                        prices[market[2:]] = price
            
            return prices
        except Exception as e:
            return {}
    
    # ==========================================
    # PRIVATE ENDPOINTS
    # ==========================================
    
    def get_balances(self):
        return self._make_request("/exchange/v1/users/balances")
    
    def get_usdt_balance(self):
        """Get USDT balance specifically"""
        balances = self.get_balances()
        
        if isinstance(balances, list):
            for bal in balances:
                if bal.get('currency') == 'USDT':
                    return float(bal.get('balance', 0))
        
        return 0
    
    def get_active_orders(self, market=None):
        body = {}
        if market:
            body['market'] = market
        return self._make_request("/exchange/v1/orders/active_orders", body)
    
    # ==========================================
    # ORDER PLACEMENT
    # ==========================================
    
    def place_order(self, market, side, order_type, price=None, quantity=None, total_quantity=None):
        body = {
            'market': market,
            'side': side,
            'order_type': order_type,
        }
        
        if price:
            body['price_per_unit'] = price
        if quantity:
            body['quantity'] = quantity
        elif total_quantity:
            body['total_quantity'] = total_quantity
        
        print(f"📝 Placing order: {body}")
        return self._make_request("/exchange/v1/orders/create", body)
    
    def place_market_buy(self, market, usdt_amount):
        """Buy with USDT amount"""
        return self.place_order(
            market=market,
            side="buy",
            order_type="market_order",
            total_quantity=usdt_amount
        )
    
    def place_market_sell(self, market, quantity):
        """Sell quantity"""
        return self.place_order(
            market=market,
            side="sell",
            order_type="market_order",
            quantity=quantity
        )
    
    def place_limit_buy(self, market, price, quantity):
        return self.place_order(
            market=market,
            side="buy",
            order_type="limit_order",
            price=price,
            quantity=quantity
        )
    
    def place_limit_sell(self, market, price, quantity):
        return self.place_order(
            market=market,
            side="sell",
            order_type="limit_order",
            price=price,
            quantity=quantity
        )
    
    def cancel_order(self, order_id):
        body = {'id': order_id}
        return self._make_request("/exchange/v1/orders/cancel", body)
    
    def cancel_all_orders(self, market):
        body = {'market': market}
        return self._make_request("/exchange/v1/orders/cancel_all", body)
    
    # ==========================================
    # UTILITY FUNCTIONS
    # ==========================================
    
    def calculate_quantity(self, capital, price, leverage=1):
        """
        Calculate quantity from capital
        capital: Amount in USDT (e.g., 100)
        price: Current price
        leverage: Leverage multiplier
        """
        if price <= 0:
            return 0
        
        # Effective capital with leverage
        effective_capital = capital * leverage
        
        # Quantity = Capital / Price
        quantity = effective_capital / price
        
        return quantity


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":
    api = CoinDCXAPI()
    
    print("🔍 Testing CoinDCX API...")
    
    # Test spot
    btc_inr = api.get_price("BTCINR")
    print(f"BTC/INR: ₹{btc_inr:,.2f}" if btc_inr else "BTC/INR: Not found")
    
    # Test USDT pairs
    print("\n📊 USDT Pairs:")
    prices = api.get_all_prices()
    
    test_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'B-BTC_USDT', 'B-ETH_USDT']
    for pair in test_pairs:
        if pair in prices:
            print(f"  {pair}: ${prices[pair]:,.2f}")
    
    # Test auth
    print("\n🔑 Testing authentication...")
    balances = api.get_balances()
    if "error" not in str(balances).lower():
        print("✅ API keys valid!")
        usdt = api.get_usdt_balance()
        print(f"💰 USDT Balance: ${usdt:.2f}")
    else:
        print(f"❌ Auth failed: {balances}")