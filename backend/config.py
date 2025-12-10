"""
CoinDCX Futures Trading Bot - Configuration
============================================
"""

# =============================================
# 🔑 YOUR COINDCX API KEYS
# =============================================

API_KEY = "e998372062e1bea070f03c856f807bbe5c5fd57418d279e0"
API_SECRET = "198bfc592645f8e9b0da5279ebcf99e600942d0cb0fb81611b4ded9ef733b901"

# =============================================
# ⚙️ BOT SETTINGS
# =============================================

PRICE_CHECK_INTERVAL = 2  # seconds

# Available Futures Pairs
FUTURES_PAIRS = [
    {"symbol": "BTCUSDT", "name": "Bitcoin", "icon": "₿"},
    {"symbol": "ETHUSDT", "name": "Ethereum", "icon": "Ξ"},
    {"symbol": "SOLUSDT", "name": "Solana", "icon": "◎"},
    {"symbol": "XRPUSDT", "name": "XRP", "icon": "✕"},
    {"symbol": "DOGEUSDT", "name": "Dogecoin", "icon": "Ð"},
    {"symbol": "MATICUSDT", "name": "Polygon", "icon": "⬡"},
    {"symbol": "ADAUSDT", "name": "Cardano", "icon": "₳"},
    {"symbol": "AVAXUSDT", "name": "Avalanche", "icon": "🔺"},
]

# Trailing SL Configuration
TRAILING_CONFIG = [
    {"rr": 0.5,  "sl_move": 0,    "action": "Watch closely",                "book_percent": 0},
    {"rr": 1.0,  "sl_move": 0,    "action": "Move SL to Entry (Breakeven)", "book_percent": 0},
    {"rr": 1.5,  "sl_move": 1.0,  "action": "Book 25% profit",              "book_percent": 25},
    {"rr": 2.0,  "sl_move": 1.0,  "action": "Book 50%, Trail SL to 1:1",    "book_percent": 50},
    {"rr": 2.5,  "sl_move": 1.5,  "action": "Trail SL to 1.5R",             "book_percent": 50},
    {"rr": 3.0,  "sl_move": 1.5,  "action": "Book more profits",            "book_percent": 65},
    {"rr": 3.5,  "sl_move": 2.0,  "action": "Trail SL to 2.0R",             "book_percent": 75},
    {"rr": 4.0,  "sl_move": 2.0,  "action": "Near final target",            "book_percent": 85},
    {"rr": 5.0,  "sl_move": 3.0,  "action": "FINAL - Full exit",            "book_percent": 100},
]

# =============================================
# 🌐 SERVER SETTINGS
# =============================================

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000
DEBUG_MODE = False