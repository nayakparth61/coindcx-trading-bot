"""
CoinDCX Trading Bot - Server
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

from coindcx_api import CoinDCXAPI
from trailing_bot import TrailingBot

# Get PORT from Railway (important!)
PORT = int(os.environ.get("PORT", 5000))

app = Flask(__name__, static_folder='../frontend')
CORS(app)

api = CoinDCXAPI()
bot = TrailingBot()

print("🤖 CoinDCX Trading Bot Starting...")

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
# API ENDPOINTS
# ==========================================

@app.route('/api/ticker', methods=['GET'])
def get_ticker():
    return jsonify(api.get_ticker())

@app.route('/api/price/<market>', methods=['GET'])
def get_price(market):
    price = api.get_price(market)
    return jsonify({"market": market, "price": price})

@app.route('/api/balances', methods=['GET'])
def get_balances():
    return jsonify(api.get_balances())

@app.route('/api/bot/start', methods=['POST'])
def start_bot_api():
    try:
        data = request.json
        result = bot.start_trade(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bot/stop/<trade_id>', methods=['POST'])
def stop_bot_api(trade_id):
    result = bot.close_trade(trade_id)
    return jsonify(result)

@app.route('/api/bot/trades', methods=['GET'])
def get_trades():
    return jsonify(bot.get_all_trades())

@app.route('/api/bot/status/<trade_id>', methods=['GET'])
def get_status(trade_id):
    trade = bot.get_trade_status(trade_id)
    if trade:
        return jsonify(trade)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/test', methods=['GET'])
def test_api():
    try:
        price = api.get_price("BTCINR")
        return jsonify({"status": "ok", "btc_price": price})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

# ==========================================
# START SERVER
# ==========================================

if __name__ == '__main__':
    print(f"🚀 Server starting on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
