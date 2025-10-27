import yfinance as yf
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import threading
import re
import urllib.request
import json

app = Flask(__name__)
limiter = Limiter(app, key_func=get_remote_address, default_limits=["20 per minute"])
cache = {}
cache_lock = threading.Lock()
CACHE_DURATION = 60

# ===== TIER 1: yfinance (Primary) =====
def fetch_yfinance(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d", interval="1m")
        if not hist.empty:
            return f"{float(hist['Close'].iloc[-1]):.2f}"
        info = stock.info
        price = info.get('regularMarketPrice') or info.get('currentPrice')
        return f"{float(price):.2f}" if price else None
    except Exception as e:
        print(f"[YF_FAIL] {ticker}: {str(e)[:80]}")
        return None

# ===== TIER 2: Yahoo Finance Public JSON (Direct HTTP) =====
def fetch_yahoo_direct(ticker):
    try:
        # 🔥 FIXED: Removed extra space in URL (critical bug!)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            # Safely navigate nested structure
            result = data.get('chart', {}).get('result')
            if result and len(result) > 0:
                price = result[0].get('meta', {}).get('regularMarketPrice')
                if price is not None:
                    return f"{float(price):.2f}"
    except Exception as e:
        print(f"[YAHOO_DIRECT_FAIL] {ticker}: {str(e)[:80]}")
        return None

# ===== Unified Fetcher (Only Tier 1 + Tier 2) =====
def get_stock_price(ticker):
    if not re.fullmatch(r'^[A-Z][A-Z0-9]{0,4}(\.[A-Z]{1,2})?$', ticker):
        return None

    with cache_lock:
        if ticker in cache and time.time() - cache[ticker]['timestamp'] < CACHE_DURATION:
            return cache[ticker]['price']

    # Try Tier 1 → Tier 2
    price = fetch_yfinance(ticker) or fetch_yahoo_direct(ticker)
    
    if price:
        with cache_lock:
            cache[ticker] = {'price': price, 'timestamp': time.time()}
    return price

# ===== Routes =====
@app.route('/price')
@limiter.limit("5 per minute")
def price():
    ticker = request.args.get('ticker', '').strip().upper()
    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400
    price_data = get_stock_price(ticker)
    if price_data:
        return jsonify({"ticker": ticker, "price": price_data})
    return jsonify({"error": "Data unavailable"}), 404

@app.route('/health')
def health():
    return jsonify({"status": "ghost_online"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
