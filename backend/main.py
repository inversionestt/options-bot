from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Options Bot Running"}

@app.get("/scan")
def scan():
    return {
        "symbol": "AAPL",
        "strategy": "CSP",
        "strike": 210,
        "premium": 2.35,
        "roi": "2.4%"
    }
