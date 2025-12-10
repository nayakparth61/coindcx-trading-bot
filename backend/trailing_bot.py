"""
Trailing Stop Loss Bot - Enhanced
=================================
Features:
- Capital-based entry (not quantity)
- Take Profit support
- Auto trailing SL
- Futures/USDT pairs
"""

import time
import threading
import json
from datetime import datetime
from coindcx_api import CoinDCXAPI
from config import TRAILING_CONFIG, PRICE_CHECK_INTERVAL


class TrailingBot:
    
    def __init__(self, socketio=None):
        self.api = CoinDCXAPI()
        self.socketio = socketio
        self.active_trades = {}
        self.is_running = False
        self.monitor_thread = None
    
    def emit(self, event, data):
        """Send event to frontend"""
        try:
            if self.socketio:
                self.socketio.emit(event, data)
        except:
            pass
        print(f"[{event}] {json.dumps(data, default=str)[:200]}")
    
    def log(self, trade_id, message, log_type="info"):
        """Log trade event"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {"time": timestamp, "message": message, "type": log_type}
        
        if trade_id in self.active_trades:
            if "logs" not in self.active_trades[trade_id]:
                self.active_trades[trade_id]["logs"] = []
            self.active_trades[trade_id]["logs"].append(log_entry)
        
        self.emit("log", {"trade_id": trade_id, "log": log_entry})
        print(f"[{timestamp}] [{log_type.upper()}] {message}")
    
    # ==========================================
    # START TRADE - CAPITAL BASED
    # ==========================================
    
    def start_trade(self, trade_config):
        """
        Start a new trade with capital amount
        
        trade_config = {
            "coin": "BTCUSDT",
            "trade_type": "LONG" or "SHORT",
            "entry_type": "MARKET" or "LIMIT",
            "entry_price": 50000,      # For limit orders
            "capital": 100,            # USDT amount to trade
            "stop_loss": 49000,
            "take_profit": 52000,      # Optional TP
            "leverage": 10
        }
        """
        trade_id = f"trade_{int(time.time())}"
        
        try:
            coin = trade_config["coin"]
            trade_type = trade_config["trade_type"]
            entry_type = trade_config["entry_type"]
            capital = float(trade_config["capital"])
            stop_loss = float(trade_config["stop_loss"])
            take_profit = float(trade_config.get("take_profit", 0))
            leverage = float(trade_config.get("leverage", 1))
            
            self.log(trade_id, f"🚀 Starting {trade_type} on {coin} with ${capital}", "info")
            
            # Get current price
            current_price = self.api.get_futures_price(coin)
            if not current_price:
                # Try alternate format
                current_price = self.api.get_price(f"B-{coin.replace('USDT', '_USDT')}")
            
            if not current_price:
                return {"success": False, "error": f"Could not fetch price for {coin}"}
            
            self.log(trade_id, f"📊 Current price: ${current_price}", "info")
            
            # Entry price
            if entry_type == "MARKET":
                entry_price = current_price
            else:
                entry_price = float(trade_config["entry_price"])
            
            # Validate SL
            if trade_type == "LONG" and stop_loss >= entry_price:
                return {"success": False, "error": "For LONG, SL must be below entry"}
            if trade_type == "SHORT" and stop_loss <= entry_price:
                return {"success": False, "error": "For SHORT, SL must be above entry"}
            
            # Calculate quantity from capital
            quantity = self.api.calculate_quantity(capital, entry_price, leverage)
            
            self.log(trade_id, f"📦 Quantity calculated: {quantity:.6f}", "info")
            
            # Calculate risk
            risk_per_unit = abs(entry_price - stop_loss)
            risk_amount = risk_per_unit * quantity
            risk_percent = (risk_per_unit / entry_price) * 100 * leverage
            
            self.log(trade_id, f"⚠️ Risk: ${risk_amount:.2f} ({risk_percent:.2f}%)", "info")
            
            # Auto-calculate TP if not provided (at 2R)
            if take_profit <= 0:
                if trade_type == "LONG":
                    take_profit = entry_price + (risk_per_unit * 2)
                else:
                    take_profit = entry_price - (risk_per_unit * 2)
                self.log(trade_id, f"🎯 Auto TP set at 2R: ${take_profit:.2f}", "info")
            
            # Place order
            self.log(trade_id, f"📝 Placing {entry_type} order...", "info")
            
            # Determine market format
            market = coin
            if not market.startswith('B-'):
                # Try B- format for CoinDCX
                market_alt = f"B-{coin.replace('USDT', '_USDT')}"
            else:
                market_alt = coin
            
            if trade_type == "LONG":
                if entry_type == "MARKET":
                    order_result = self.api.place_market_buy(market, capital)
                    if "error" in str(order_result) or "message" in order_result:
                        # Try alternate format
                        order_result = self.api.place_market_buy(market_alt, capital)
                else:
                    order_result = self.api.place_limit_buy(market, entry_price, quantity)
            else:  # SHORT
                if entry_type == "MARKET":
                    order_result = self.api.place_market_sell(market, quantity)
                    if "error" in str(order_result) or "message" in order_result:
                        order_result = self.api.place_market_sell(market_alt, quantity)
                else:
                    order_result = self.api.place_limit_sell(market, entry_price, quantity)
            
            # Check result
            if "error" in str(order_result).lower():
                error_msg = str(order_result)
                self.log(trade_id, f"❌ Order failed: {error_msg}", "error")
                return {"success": False, "error": error_msg}
            
            order_id = "pending"
            if "orders" in order_result and len(order_result["orders"]) > 0:
                order_id = order_result["orders"][0].get("id", "unknown")
            
            self.log(trade_id, f"✅ Order placed! ID: {order_id}", "success")
            
            # Calculate trailing levels
            trailing_levels = self._calculate_levels(
                entry_price, stop_loss, risk_per_unit, quantity, leverage, trade_type
            )
            
            # Store trade
            self.active_trades[trade_id] = {
                "id": trade_id,
                "coin": coin,
                "trade_type": trade_type,
                "entry_price": entry_price,
                "capital": capital,
                "quantity": quantity,
                "stop_loss": stop_loss,
                "current_sl": stop_loss,
                "take_profit": take_profit,
                "leverage": leverage,
                "risk_per_unit": risk_per_unit,
                "risk_amount": risk_amount,
                "risk_percent": risk_percent,
                "trailing_levels": trailing_levels,
                "current_level": -1,
                "order_id": order_id,
                "status": "ACTIVE",
                "created_at": datetime.now().isoformat(),
                "logs": []
            }
            
            # Start monitoring
            if not self.is_running:
                self.start_monitoring()
            
            self.emit("trade_started", self.active_trades[trade_id])
            
            return {
                "success": True, 
                "trade_id": trade_id, 
                "trade": self.active_trades[trade_id]
            }
            
        except Exception as e:
            error_msg = str(e)
            self.log(trade_id, f"❌ Error: {error_msg}", "error")
            return {"success": False, "error": error_msg}
    
    def _calculate_levels(self, entry, sl, risk, quantity, leverage, trade_type):
        """Calculate all trailing SL levels"""
        levels = []
        is_long = trade_type == "LONG"
        
        for config in TRAILING_CONFIG:
            if is_long:
                target_price = entry + (risk * config["rr"])
                new_sl = entry + (risk * config["sl_move"]) if config["rr"] >= 1 else sl
            else:
                target_price = entry - (risk * config["rr"])
                new_sl = entry - (risk * config["sl_move"]) if config["rr"] >= 1 else sl
            
            profit_amount = risk * config["rr"] * quantity
            profit_percent = ((config["rr"] * risk) / entry) * 100 * leverage
            
            levels.append({
                "rr": config["rr"],
                "target_price": round(target_price, 2),
                "new_sl": round(new_sl, 2) if config["rr"] >= 1 else round(sl, 2),
                "action": config["action"],
                "book_percent": config["book_percent"],
                "profit_amount": round(profit_amount, 2),
                "profit_percent": round(profit_percent, 2),
                "reached": False
            })
        
        return levels
    
    # ==========================================
    # MONITORING
    # ==========================================
    
    def start_monitoring(self):
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔄 Price monitoring started")
    
    def stop_monitoring(self):
        self.is_running = False
        print("⏹️ Monitoring stopped")
    
    def _monitor_loop(self):
        while self.is_running:
            try:
                self._check_all_trades()
                time.sleep(PRICE_CHECK_INTERVAL)
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)
    
    def _check_all_trades(self):
        for trade_id, trade in list(self.active_trades.items()):
            if trade["status"] != "ACTIVE":
                continue
            try:
                self._check_trade(trade_id, trade)
            except Exception as e:
                print(f"Check error {trade_id}: {e}")
    
    def _check_trade(self, trade_id, trade):
        coin = trade["coin"]
        trade_type = trade["trade_type"]
        entry_price = trade["entry_price"]
        current_sl = trade["current_sl"]
        take_profit = trade["take_profit"]
        risk = trade["risk_per_unit"]
        levels = trade["trailing_levels"]
        current_level = trade["current_level"]
        
        # Get price
        current_price = self.api.get_futures_price(coin)
        if not current_price:
            current_price = self.api.get_price(f"B-{coin.replace('USDT', '_USDT')}")
        
        if not current_price:
            return
        
        is_long = trade_type == "LONG"
        
        # Calculate R:R
        if is_long:
            price_change = current_price - entry_price
        else:
            price_change = entry_price - current_price
        
        current_rr = price_change / risk if risk > 0 else 0
        
        # P/L
        pnl = price_change * trade["quantity"]
        pnl_percent = (price_change / entry_price) * 100 * trade["leverage"]
        
        # Emit update
        self.emit("price_update", {
            "trade_id": trade_id,
            "current_price": round(current_price, 2),
            "current_rr": round(current_rr, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
            "current_sl": current_sl,
            "take_profit": take_profit
        })
        
        # Check TP hit
        if take_profit > 0:
            if (is_long and current_price >= take_profit) or \
               (not is_long and current_price <= take_profit):
                self._handle_tp_hit(trade_id, current_price)
                return
        
        # Check SL hit
        if (is_long and current_price <= current_sl) or \
           (not is_long and current_price >= current_sl):
            self._handle_sl_hit(trade_id, current_price)
            return
        
        # Check trailing levels
        for i, level in enumerate(levels):
            if current_rr >= level["rr"] and i > current_level:
                self._handle_level_reached(trade_id, i, level, current_price)
    
    def _handle_level_reached(self, trade_id, level_index, level, current_price):
        trade = self.active_trades[trade_id]
        
        trade["current_level"] = level_index
        level["reached"] = True
        
        new_sl = level["new_sl"]
        is_long = trade["trade_type"] == "LONG"
        
        should_update = (is_long and new_sl > trade["current_sl"]) or \
                       (not is_long and new_sl < trade["current_sl"])
        
        if should_update:
            old_sl = trade["current_sl"]
            trade["current_sl"] = new_sl
            
            self.log(trade_id, 
                f"🎯 {level['rr']}R HIT! Trail SL: ${old_sl:.2f} → ${new_sl:.2f}", 
                "alert")
            
            self.emit("level_reached", {
                "trade_id": trade_id,
                "level": level,
                "new_sl": new_sl,
                "action": level["action"]
            })
        
        # Book profits
        if level["book_percent"] > 0:
            self._book_profit(trade_id, level)
    
    def _book_profit(self, trade_id, level):
        trade = self.active_trades[trade_id]
        
        book_percent = level["book_percent"]
        quantity_to_close = trade["quantity"] * (book_percent / 100) * 0.3
        
        if quantity_to_close < 0.00001:
            return
        
        self.log(trade_id, f"💰 Booking {book_percent}% profit...", "success")
        
        coin = trade["coin"]
        market = coin if coin.startswith('B-') else f"B-{coin.replace('USDT', '_USDT')}"
        
        try:
            if trade["trade_type"] == "LONG":
                result = self.api.place_market_sell(market, quantity_to_close)
            else:
                usdt = quantity_to_close * trade["entry_price"]
                result = self.api.place_market_buy(market, usdt)
            
            if "orders" in result:
                trade["quantity"] -= quantity_to_close
                self.log(trade_id, f"✅ Profit booked! Remaining: {trade['quantity']:.6f}", "success")
        except Exception as e:
            self.log(trade_id, f"⚠️ Booking failed: {e}", "error")
    
    def _handle_tp_hit(self, trade_id, price):
        trade = self.active_trades[trade_id]
        trade["status"] = "CLOSED_TP"
        
        pnl = abs(price - trade["entry_price"]) * trade["quantity"]
        
        self.log(trade_id, f"🎉 TAKE PROFIT HIT at ${price:.2f}! Profit: ${pnl:.2f}", "success")
        
        self.emit("trade_closed", {
            "trade_id": trade_id,
            "reason": "Take Profit Hit",
            "exit_price": price,
            "pnl": pnl
        })
    
    def _handle_sl_hit(self, trade_id, price):
        trade = self.active_trades[trade_id]
        trade["status"] = "CLOSED_SL"
        
        self.log(trade_id, f"⚠️ STOP LOSS HIT at ${price:.2f}", "error")
        
        self.emit("trade_closed", {
            "trade_id": trade_id,
            "reason": "Stop Loss Hit",
            "exit_price": price
        })
    
    def close_trade(self, trade_id):
        trade = self.active_trades.get(trade_id)
        if not trade:
            return {"success": False, "error": "Trade not found"}
        
        try:
            coin = trade["coin"]
            current_price = self.api.get_futures_price(coin) or trade["entry_price"]
            
            market = coin if coin.startswith('B-') else f"B-{coin.replace('USDT', '_USDT')}"
            
            if trade["trade_type"] == "LONG":
                result = self.api.place_market_sell(market, trade["quantity"])
            else:
                usdt = trade["quantity"] * current_price
                result = self.api.place_market_buy(market, usdt)
            
            trade["status"] = "CLOSED_MANUAL"
            
            self.log(trade_id, f"✅ Closed at ${current_price:.2f}", "success")
            
            self.emit("trade_closed", {
                "trade_id": trade_id,
                "reason": "Manual Close",
                "exit_price": current_price
            })
            
            return {"success": True, "exit_price": current_price}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_trade_status(self, trade_id):
        return self.active_trades.get(trade_id)
    
    def get_all_trades(self):
        return list(self.active_trades.values())


if __name__ == "__main__":
    bot = TrailingBot()
    print("✅ Bot module loaded!")