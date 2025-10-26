import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
import time
import os # <-- IMPORT KAR LIJIYE

app = Flask(__name__)

cache = {}
CACHE_DURATION_SECONDS = 10

def get_stock_price(ticker):
    if ticker in cache and time.time() - cache[ticker]['timestamp'] < CACHE_DURATION_SECONDS:
        return cache[ticker]['price']

    try:
        url = f"https://finance.yahoo.com/quote/{ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        price_element = soup.find('fin-streamer', {'data-symbol': ticker.upper(), 'data-field': 'regularMarketPrice'})
        
        if price_element:
            price = price_element.text.strip()
            cache[ticker] = {'price': price, 'timestamp': time.time()}
            return price
        else:
            return None

    except requests.exceptions.RequestException:
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
        return jsonify({"error": f"Could not retrieve price for ticker: {ticker}"}), 404

# YEH HAI WOH NAYA, MAHATVAPURN CODE
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
