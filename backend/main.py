from fastapi import FastAPI

app = FastAPI()

watchlist = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "NVDA"
]

@app.get("/")
def home():
    return {"status": "Options Bot Running"}

@app.get("/scan")
def scan():

    results = []

    for symbol in watchlist:
        results.append({
            "symbol": symbol,
            "strategy": "CSP",
            "strike": 210,
            "premium": 2.35,
            "roi": "2.4%"
        })

    return results
