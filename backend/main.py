import os
import requests
from fastapi import FastAPI

app = FastAPI()

API_KEY = os.getenv("TRADIER_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
commission = 1.0


@app.get("/")
def home():
    return {"status": "Options Bot Running"}


@app.get("/scan")
def scan():
    results = []

    for symbol in watchlist:
        exp_url = f"https://api.tradier.com/v1/markets/options/expirations?symbol={symbol}"
        exp_resp = requests.get(exp_url, headers=headers)
        exp_data = exp_resp.json()

        expirations = exp_data["expirations"]["date"]
        expiration = expirations[0]

        chain_url = f"https://api.tradier.com/v1/markets/options/chains?symbol={symbol}&expiration={expiration}"
        chain_resp = requests.get(chain_url, headers=headers)
        chain_data = chain_resp.json()

        options = chain_data["options"]["option"]

        puts = [opt for opt in options if opt["option_type"] == "put" and opt["bid"] is not None]

        valid_puts = []
        for opt in puts:
            bid = float(opt["bid"] or 0)
            strike = float(opt["strike"] or 0)

            if bid > 0 and strike > 0:
                roi_flat_pct = ((bid * 100) - commission) / (strike * 100) * 100

                valid_puts.append({
                    "symbol": symbol,
                    "strategy": "CSP",
                    "strike": strike,
                    "premium": bid,
                    "expiration": expiration,
                    "roi_flat_pct": round(roi_flat_pct, 2)
                })

        valid_puts = sorted(valid_puts, key=lambda x: x["roi_flat_pct"], reverse=True)

        if valid_puts:
            results.append(valid_puts[0])

    return results
