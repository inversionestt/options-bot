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

        # obtener expirations
        exp_url = f"https://api.tradier.com/v1/markets/options/expirations?symbol={symbol}"
        r = requests.get(exp_url, headers=headers)
        expirations = r.json()["expirations"]["date"]

        # usar la primera expiration
        expiration = expirations[0]

        chain_url = f"https://api.tradier.com/v1/markets/options/chains?symbol={symbol}&expiration={expiration}"

        r = requests.get(chain_url, headers=headers)
        data = r.json()

        options = data["options"]["option"][:5]

        for opt in options:

            results.append({
                "symbol": symbol,
                "type": opt["option_type"],
                "strike": opt["strike"],
                "bid": opt["bid"],
                "ask": opt["ask"],
                "expiration": expiration
            })

    return results
    return results
