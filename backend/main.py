import os
import requests
from fastapi import FastAPI

app = FastAPI()

API_KEY = os.getenv("TRADIER_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

watchlist = ["AAPL","MSFT","GOOGL","AMZN","META","TSLA","NVDA"]

@app.get("/")
def home():
    return {"status": "Options Bot Running"}

@app.get("/scan")
def scan():

    results = []

    for symbol in watchlist:

        url = f"https://api.tradier.com/v1/markets/quotes?symbols={symbol}"

        r = requests.get(url, headers=headers)
        data = r.json()

        price = data["quotes"]["quote"]["last"]

        results.append({
            "symbol": symbol,
            "price": price
        })

    return results
