import os
from datetime import datetime, date
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

API_KEY = os.getenv("TRADIER_API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
commission = 1.0
min_dte = 3
max_dte = 15


def days_to_expiration(expiration_str: str) -> int:
    exp_date = datetime.strptime(expiration_str, "%Y-%m-%d").date()
    return (exp_date - date.today()).days


def midpoint(bid, ask):
    bid = float(bid or 0)
    ask = float(ask or 0)
    if bid > 0 and ask > 0:
        return round((bid + ask) / 2, 2)
    return round(bid, 2)


def get_quote(symbol: str):
    url = f"https://api.tradier.com/v1/markets/quotes?symbols={symbol}"
    r = requests.get(url, headers=headers, timeout=20)
    data = r.json()
    return float(data["quotes"]["quote"]["last"])


def get_expirations(symbol: str):
    url = f"https://api.tradier.com/v1/markets/options/expirations?symbol={symbol}&includeAllRoots=true"
    r = requests.get(url, headers=headers, timeout=20)
    data = r.json()
    return data["expirations"]["date"]


def get_chain(symbol: str, expiration: str):
    url = f"https://api.tradier.com/v1/markets/options/chains?symbol={symbol}&expiration={expiration}&greeks=false"
    r = requests.get(url, headers=headers, timeout=20)
    data = r.json()
    return data["options"]["option"]


def analyze_best_csp(symbol: str):
    stock_price = get_quote(symbol)
    expirations = get_expirations(symbol)

    best = None

    for expiration in expirations:
        dte = days_to_expiration(expiration)

        if dte < min_dte or dte > max_dte:
            continue

        options = get_chain(symbol, expiration)

        puts = [opt for opt in options if opt.get("option_type") == "put"]

        for opt in puts:
            strike = float(opt.get("strike") or 0)
            bid = float(opt.get("bid") or 0)
            ask = float(opt.get("ask") or 0)

            if strike <= 0:
                continue

            # CSP realista: put OTM o ligeramente ATM
            if strike > stock_price:
                continue

            # rango razonable: no demasiado lejos del precio
            strike_distance_pct = ((stock_price - strike) / stock_price) * 100
            if strike_distance_pct > 8:
                continue

            premium = midpoint(bid, ask)
            if premium <= 0:
                continue

            roi_flat_pct = (((premium * 100) - commission) / (strike * 100)) * 100
            break_even = round(strike - premium + (commission / 100), 2)
            protection_pct = ((stock_price - break_even) / stock_price) * 100

            candidate = {
                "symbol": symbol,
                "strategy": "CSP",
                "stock_price": round(stock_price, 2),
                "strike": round(strike, 2),
                "premium": round(premium, 2),
                "expiration": expiration,
                "dte": dte,
                "roi_flat_pct": round(roi_flat_pct, 2),
                "break_even": break_even,
                "protection_pct": round(protection_pct, 2),
                "distance_pct": round(strike_distance_pct, 2),
                "bid": round(bid, 2),
                "ask": round(ask, 2)
            }

            # score balanceado: ROI alto, strike cercano, DTE razonable
            score = roi_flat_pct - (strike_distance_pct * 0.35) - (dte * 0.03)

            if best is None or score > best["_score"]:
                candidate["_score"] = score
                best = candidate

    if best:
        best.pop("_score", None)

    return best


@app.get("/scan")
def scan():
    results = []

    for symbol in watchlist:
        try:
            item = analyze_best_csp(symbol)
            if item:
                results.append(item)
            else:
                results.append({
                    "symbol": symbol,
                    "error": "No valid CSP found in DTE range"
                })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "error": str(e)
            })

    valid_results = [r for r in results if "error" not in r]
    error_results = [r for r in results if "error" in r]

    valid_results.sort(key=lambda x: x["roi_flat_pct"], reverse=True)

    return JSONResponse(valid_results + error_results)


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Options Bot Dashboard</title>
  <style>
    :root{
      --bg:#0b1020;
      --panel:#121a2b;
      --panel-2:#17223a;
      --text:#eef3ff;
      --muted:#a9b4d0;
      --accent:#6ea8fe;
      --good:#22c55e;
      --warn:#f59e0b;
      --bad:#ef4444;
      --border:rgba(255,255,255,.08);
      --shadow:0 10px 30px rgba(0,0,0,.35);
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family:Inter,Segoe UI,Arial,sans-serif;
      background:linear-gradient(180deg,#0a0f1d,#10182b);
      color:var(--text);
    }
    .wrap{
      max-width:1400px;
      margin:0 auto;
      padding:24px;
    }
    .topbar{
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:16px;
      margin-bottom:20px;
      flex-wrap:wrap;
    }
    .title h1{
      margin:0;
      font-size:30px;
      font-weight:800;
      letter-spacing:.2px;
    }
    .title p{
      margin:6px 0 0;
      color:var(--muted);
      font-size:14px;
    }
    .actions{
      display:flex;
      gap:10px;
      flex-wrap:wrap;
    }
    .btn{
      border:1px solid var(--border);
      background:var(--panel);
      color:var(--text);
      padding:10px 14px;
      border-radius:12px;
      cursor:pointer;
      box-shadow:var(--shadow);
      font-weight:600;
    }
    .btn.primary{
      background:linear-gradient(135deg,#2563eb,#3b82f6);
      border:none;
    }
    .grid{
      display:grid;
      grid-template-columns:repeat(4,1fr);
      gap:16px;
      margin-bottom:20px;
    }
    .card{
      background:rgba(18,26,43,.92);
      border:1px solid var(--border);
      border-radius:18px;
      padding:18px;
      box-shadow:var(--shadow);
    }
    .metric-label{
      color:var(--muted);
      font-size:13px;
      margin-bottom:8px;
    }
    .metric-value{
      font-size:30px;
      font-weight:800;
    }
    .metric-sub{
      margin-top:8px;
      color:var(--muted);
      font-size:12px;
    }
    .table-card{
      background:rgba(18,26,43,.96);
      border:1px solid var(--border);
      border-radius:20px;
      box-shadow:var(--shadow);
      overflow:hidden;
    }
    .table-head{
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding:18px 20px;
      border-bottom:1px solid var(--border);
      flex-wrap:wrap;
    }
    .table-head h2{
      margin:0;
      font-size:20px;
    }
    .table-head p{
      margin:4px 0 0;
      color:var(--muted);
      font-size:13px;
    }
    .search{
      background:var(--panel-2);
      border:1px solid var(--border);
      color:var(--text);
      padding:10px 12px;
      border-radius:12px;
      min-width:240px;
      outline:none;
    }
    .table-wrap{
      overflow:auto;
    }
    table{
      width:100%;
      border-collapse:collapse;
      min-width:1100px;
    }
    th,td{
      padding:14px 16px;
      text-align:left;
      border-bottom:1px solid var(--border);
      font-size:14px;
    }
    th{
      color:#c8d4f0;
      background:rgba(255,255,255,.02);
      position:sticky;
      top:0;
      z-index:1;
    }
    tr:hover td{
      background:rgba(255,255,255,.02);
    }
    .pill{
      display:inline-block;
      padding:6px 10px;
      border-radius:999px;
      font-size:12px;
      font-weight:700;
      letter-spacing:.2px;
    }
    .pill.csp{
      background:rgba(34,197,94,.16);
      color:#86efac;
      border:1px solid rgba(34,197,94,.25);
    }
    .good{color:#86efac;font-weight:700}
    .warn{color:#fbbf24;font-weight:700}
    .muted{color:var(--muted)}
    .error{
      color:#fca5a5;
      font-weight:700;
    }
    .footer{
      margin-top:14px;
      color:var(--muted);
      font-size:12px;
    }
    .loader{
      display:none;
      margin-left:8px;
      width:16px;
      height:16px;
      border:2px solid rgba(255,255,255,.25);
      border-top-color:#fff;
      border-radius:50%;
      animation:spin 1s linear infinite;
    }
    .show{display:inline-block}
    @keyframes spin{to{transform:rotate(360deg)}}
    @media (max-width:1100px){
      .grid{grid-template-columns:repeat(2,1fr)}
    }
    @media (max-width:700px){
      .grid{grid-template-columns:1fr}
      .title h1{font-size:24px}
      .search{min-width:100%}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="title">
        <h1>Options Strategy Dashboard</h1>
        <p>Professional CSP scanner powered by Tradier</p>
      </div>
      <div class="actions">
        <button class="btn" onclick="loadData()">Refresh <span id="loader" class="loader"></span></button>
        <button class="btn primary" onclick="window.open('/scan','_blank')">Open JSON</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="metric-label">Symbols Scanned</div>
        <div class="metric-value" id="mSymbols">-</div>
        <div class="metric-sub">Watchlist coverage</div>
      </div>
      <div class="card">
        <div class="metric-label">Best ROI</div>
        <div class="metric-value" id="mBestRoi">-</div>
        <div class="metric-sub">Top CSP opportunity</div>
      </div>
      <div class="card">
        <div class="metric-label">Average DTE</div>
        <div class="metric-value" id="mAvgDte">-</div>
        <div class="metric-sub">Selected expirations</div>
      </div>
      <div class="card">
        <div class="metric-label">Average Protection</div>
        <div class="metric-value" id="mProtection">-</div>
        <div class="metric-sub">Distance to break-even</div>
      </div>
    </div>

    <div class="table-card">
      <div class="table-head">
        <div>
          <h2>Best CSP Opportunities</h2>
          <p>Filtered near ATM / OTM, ranked by ROI and strike quality</p>
        </div>
        <input id="search" class="search" placeholder="Filter by symbol..." oninput="renderTable()" />
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Stock Price</th>
              <th>Strike</th>
              <th>Premium</th>
              <th>DTE</th>
              <th>Expiration</th>
              <th>ROI Flat %</th>
              <th>Break Even</th>
              <th>Protection %</th>
              <th>Distance %</th>
              <th>Bid / Ask</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>

    <div class="footer" id="footerText">Loading live data...</div>
  </div>

  <script>
    let rawData = [];

    function fmtNum(v){
      return typeof v === 'number' ? v.toFixed(2) : v;
    }

    function metricCards(data){
      const valid = data.filter(x => !x.error);
      document.getElementById('mSymbols').textContent = valid.length;

      if(valid.length === 0){
        document.getElementById('mBestRoi').textContent = '-';
        document.getElementById('mAvgDte').textContent = '-';
        document.getElementById('mProtection').textContent = '-';
        return;
      }

      const bestRoi = Math.max(...valid.map(x => x.roi_flat_pct || 0));
      const avgDte = valid.reduce((a,b) => a + (b.dte || 0), 0) / valid.length;
      const avgProtection = valid.reduce((a,b) => a + (b.protection_pct || 0), 0) / valid.length;

      document.getElementById('mBestRoi').textContent = bestRoi.toFixed(2) + '%';
      document.getElementById('mAvgDte').textContent = avgDte.toFixed(1);
      document.getElementById('mProtection').textContent = avgProtection.toFixed(2) + '%';
    }

    function renderTable(){
      const q = document.getElementById('search').value.trim().toUpperCase();
      const tbody = document.getElementById('tbody');
      tbody.innerHTML = '';

      const filtered = rawData.filter(item => {
        if(!q) return true;
        return (item.symbol || '').toUpperCase().includes(q);
      });

      for(const item of filtered){
        const tr = document.createElement('tr');

        if(item.error){
          tr.innerHTML = `
            <td>${item.symbol}</td>
            <td colspan="11" class="error">${item.error}</td>
          `;
          tbody.appendChild(tr);
          continue;
        }

        const roiClass = item.roi_flat_pct >= 1 ? 'good' : 'warn';
        tr.innerHTML = `
          <td><strong>${item.symbol}</strong></td>
          <td><span class="pill csp">${item.strategy}</span></td>
          <td>$${fmtNum(item.stock_price)}</td>
          <td>$${fmtNum(item.strike)}</td>
          <td>$${fmtNum(item.premium)}</td>
          <td>${item.dte}</td>
          <td>${item.expiration}</td>
          <td class="${roiClass}">${fmtNum(item.roi_flat_pct)}%</td>
          <td>$${fmtNum(item.break_even)}</td>
          <td>${fmtNum(item.protection_pct)}%</td>
          <td>${fmtNum(item.distance_pct)}%</td>
          <td class="muted">${fmtNum(item.bid)} / ${fmtNum(item.ask)}</td>
        `;
        tbody.appendChild(tr);
      }

      document.getElementById('footerText').textContent =
        `Rows shown: ${filtered.length} | Updated from live Tradier data`;
    }

    async function loadData(){
      const loader = document.getElementById('loader');
      loader.classList.add('show');

      try{
        const res = await fetch('/scan');
        const data = await res.json();
        rawData = data;
        metricCards(data);
        renderTable();
      }catch(err){
        document.getElementById('footerText').textContent = 'Error loading data';
      }finally{
        loader.classList.remove('show');
      }
    }

    loadData();
  </script>
</body>
</html>
"""
