import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
import time
import os
import re
import json # <-- JSON library import kar lijiye

app = Flask(__name__)

cache = {}
CACHE_DURATION_SECONDS = 10

def get_stock_price(ticker):
    # Check cache first
    if ticker in cache and time.time() - cache[ticker]['timestamp'] < CACHE_DURATION_SECONDS:
        return cache[ticker]['price']

    try:
        url = f"https://finance.yahoo.com/quote/{ticker}"
        # Enhanced headers to look exactly like a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://finance.yahoo.com/',
            'Connection': 'keep-alive',
        }
        response = requests.get(url, headers=headers, timeout=7)
        response.raise_for_status()

        # --- NEW STEALTH METHOD: Scrape the embedded JSON data ---
        # This is the most reliable way.
        json_match = re.search(r'root\.App\.main = ({.*?});', response.text)
        if json_match:
            json_str = json_match.group(1)
            data = json.loads(json_str)
            
            # Navigate the JSON path to the price
            price = data['context']['dispatcher']['stores']['QuoteSummaryStore']['price']['regularMarketPrice']['fmt']
            
            if price:
                cache[ticker] = {'price': price, 'timestamp': time.time()}
                return price

        # --- FALLBACK METHOD: Old HTML scraping (if JSON fails) ---
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.find('fin-streamer', {'data-symbol': ticker.upper(), 'data-field': 'regularMarketPrice'})
        
        if price_element:
            price = price_element.text.strip()
            cache[ticker] = {'price': price, 'timestamp': time.time()}
            return price

        # If both methods fail
        return None

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError):
        # Network error, or JSON structure changed, or key not found in JSON
        return None
    except Exception:
        return None

@app.route('/price')
def price():
    ticker = request.args.get('ticker')
    if not ticker:
        return jsonify({"error": "Ticker parameter is missing. Example: /price?ticker=AAPL"}), 400

    price_data = get_stock_price(ticker)
    if price_data:
        return jsonify({"ticker": ticker.upper(), "price": price_data})
    else:
        return jsonify({"error": f"Could not retrieve price for ticker: {ticker}. Enemy defenses may have been upgraded again."}), 404

# YEH hisse waisa ka waisa hai
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
