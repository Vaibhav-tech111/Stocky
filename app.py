import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
import time

app = Flask(__name__)

# Simple cache to avoid getting blocked and to speed up requests
cache = {}
CACHE_DURATION_SECONDS = 10 # 10 second cache is aggressive but good for real-time feel

def get_stock_price(ticker):
    # Check cache first
    if ticker in cache and time.time() - cache[ticker]['timestamp'] < CACHE_DURATION_SECONDS:
        return cache[ticker]['price']

    try:
        url = f"https://finance.yahoo.com/quote/{ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5) # Added timeout
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the price element. This is the most direct way.
        price_element = soup.find('fin-streamer', {'data-symbol': ticker.upper(), 'data-field': 'regularMarketPrice'})
        
        if price_element:
            price = price_element.text.strip()
            # Update cache
            cache[ticker] = {'price': price, 'timestamp': time.time()}
            return price
        else:
            return None # Could not find the price element

    except requests.exceptions.RequestException:
        return None # Network or request error
    except Exception:
        return None # Any other parsing error

@app.route('/price')
def price():
    ticker = request.args.get('ticker')
    if not ticker:
        return jsonify({"error": "Ticker parameter is missing. Example: /price?ticker=AAPL"}), 400

    price = get_stock_price(ticker)
    if price:
        return jsonify({"ticker": ticker.upper(), "price": price})
    else:
        return jsonify({"error": f"Could not retrieve price for ticker: {ticker}"}), 404

if __name__ == '__main__':
    app.run(debug=True)
