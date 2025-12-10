"""
CoinDCX Trading Bot - Main Server (FIXED)
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os

from coindcx_api import CoinDCXAPI
from trailing_bot import TrailingBot
from config import SERVER_HOST, SERVER_PORT, DEBUG_MODE

# Initialize
app = Flask(__name__, static_folder='../frontend')
CORS(app)

# FIXED: Use 'threading' instead of 'eventlet'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

api = CoinDCXAPI()
bot = TrailingBot(socketio)

print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🤖 CoinDCX Auto Trading Bot                                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")


# ==========================================
# STATIC FILES
# ==========================================

@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)


# ==========================================
# API - MARKET DATA
# ==========================================

@app.route('/api/ticker', methods=['GET'])
def get_ticker():
    return jsonify(api.get_ticker())

@app.route('/api/price/<market>', methods=['GET'])
def get_price(market):
    price = api.get_price(market)
    return jsonify({"market": market, "price": price})


# ==========================================
# API - ACCOUNT
# ==========================================

@app.route('/api/balances', methods=['GET'])
def get_balances():
    return jsonify(api.get_balances())


# ==========================================
# API - BOT
# ==========================================

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    try:
        data = request.json
        result = bot.start_trade(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bot/stop/<trade_id>', methods=['POST'])
def stop_bot(trade_id):
    result = bot.close_trade(trade_id)
    return jsonify(result)

@app.route('/api/bot/status/<trade_id>', methods=['GET'])
def get_status(trade_id):
    trade = bot.get_trade_status(trade_id)
    if trade:
        return jsonify(trade)
    return jsonify({"error": "Trade not found"}), 404

@app.route('/api/bot/trades', methods=['GET'])
def get_trades():
    return jsonify(bot.get_all_trades())


# ==========================================
# API - TEST
# ==========================================

@app.route('/api/test', methods=['GET'])
def test_connection():
    try:
        price = api.get_price("BTCINR")
        balances = api.get_balances()
        auth_ok = "error" not in str(balances).lower() and "message" not in str(balances).lower()
        
        return jsonify({
            "status": "ok",
            "btc_price": price,
            "auth_status": "authenticated" if auth_ok else "failed",
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ==========================================
# WEBSOCKET
# ==========================================

@socketio.on('connect')
def handle_connect():
    print(f"📱 Client connected")
    emit('connected', {'status': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"📱 Client disconnected")


# ==========================================
# START
# ==========================================

if __name__ == '__main__':
    import socket
    
    # Get local IP
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🚀 Server starting...                                       ║
║                                                               ║
║   📍 Local:  http://localhost:{SERVER_PORT}                        ║
║   📱 Phone:  http://{local_ip}:{SERVER_PORT}                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    # Test connection
    print("🔍 Testing CoinDCX connection...")
    test_price = api.get_price("BTCINR")
    if test_price:
        print(f"✅ Connected! BTC: ₹{test_price:,.2f}")
    else:
        print("⚠️ Could not fetch price")
    
    print("\n🔑 Testing API keys...")
    balances = api.get_balances()
    if "error" not in str(balances).lower() and "message" not in str(balances).lower():
        print("✅ API keys valid!")
    else:
        print("❌ API authentication failed!")
        print(f"   Check your keys in config.py")
    
    print("\n" + "="*60)
    print("🤖 Bot ready! Open the URL above on your phone.")
    print("="*60 + "\n")
    
    # Run with threading mode (compatible with all Python versions)
    socketio.run(app, host=SERVER_HOST, port=SERVER_PORT, debug=False, allow_unsafe_werkzeug=True)