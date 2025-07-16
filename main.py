from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import yfinance as yf

app = FastAPI()

# CORS erlauben für dein Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Interne Aktien-Watchlist
watchlist = [
    "TKA.DE", "CSPX.L", "HMWO.L", "JNJ", "NVDA", "AAPL", "TSLA", "AMZN", "META", "PLTR"
]

@app.get("/")
def status():
    return {"status": "App läuft ✅", "überwachte Aktien": watchlist}

@app.post("/add")
async def add_ticker(request: Request):
    body = await request.json()
    ticker = body.get("ticker", "").upper()
    if ticker and ticker not in watchlist:
        watchlist.append(ticker)
    return {"watchlist": watchlist}

@app.get("/signal/{ticker}")
def aktien_signal(ticker: str):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if data.empty:
            return {"ticker": ticker, "signal": "Keine Daten", "preis": 0.0}

        preis = data["Close"].iloc[-1]
        ma5 = data["Close"].rolling(window=5).mean().iloc[-1]

        if preis > ma5:
            signal = "KAUFEN"
        elif preis < ma5:
            signal = "VERKAUFEN"
        else:
            signal = "HALTEN"

        return {"ticker": ticker, "signal": signal, "preis": round(preis, 2)}

    except Exception as e:
        return {"ticker": ticker, "signal": "Fehler", "error": str(e), "preis": 0.0}

# Statisches Frontend ausliefern
@app.get("/frontend.html")
def serve_frontend():
    path = os.path.join(os.path.dirname(__file__), "frontend.html")
    return FileResponse(path, media_type='text/html')


