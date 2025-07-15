from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
from pydantic import BaseModel
import os

app = FastAPI()

# CORS für Frontend-Zugriff
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mail-Konfiguration (aus Umgebungsvariablen)
conf = ConnectionConfig(
    MAIL_USERNAME=os.environ.get("EMAIL_USER"),
    MAIL_PASSWORD=os.environ.get("EMAIL_PASS"),
    MAIL_FROM=os.environ.get("EMAIL_USER"),
    MAIL_PORT=int(os.environ.get("SMTP_PORT")),
    MAIL_SERVER=os.environ.get("SMTP_SERVER"),
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True
)
fm = FastMail(conf)

# Tickers – initial festgelegt
tracked_tickers = [
    "TKA.DE",       # ThyssenKrupp
    "CSPX.L",       # Amundi S&P 500 (Börse London)
    "HMWO.L",       # HSBC MSCI World
    "JNJ",          # Johnson & Johnson
    "NVDA", "AAPL", "TSLA", "AMZN", "META", "PLTR"
]

class AddTicker(BaseModel):
    ticker: str

@app.post("/add")
def add_ticker(t: AddTicker):
    if t.ticker.upper() not in tracked_tickers:
        tracked_tickers.append(t.ticker.upper())
        return {"message": f"{t.ticker} wurde zur Überwachung hinzugefügt."}
    return {"message": f"{t.ticker} wird bereits überwacht."}

def check_signals():
    for ticker in tracked_tickers:
        try:
            df = yf.download(ticker, period="1mo", interval="1d")
            close = df["Close"]
            sma5 = close.rolling(window=5).mean()
            sma20 = close.rolling(window=20).mean()

            if sma5.iloc[-1] > sma20.iloc[-1]:
                signal = "KAUFEN"
            elif sma5.iloc[-1] < sma20.iloc[-1]:
                signal = "VERKAUFEN"
            else:
                signal = "HALTEN"

            if signal != "HALTEN":
                send_email(ticker, close.iloc[-1], signal)

        except Exception as e:
            print(f"Fehler bei {ticker}: {e}")

def send_email(ticker, price, signal):
    message = MessageSchema(
        subject=f"{signal}-Signal für {ticker}",
        recipients=[os.environ.get("EMAIL_TARGET")],
        body=f"Aktie: {ticker}\nPreis: {price:.2f}\nSignal: {signal}",
        subtype="plain"
    )
    fm.send_message(message)

# Starte automatischen Scheduler alle 10 Minuten
scheduler = BackgroundScheduler()
scheduler.add_job(check_signals, "interval", minutes=10)
scheduler.start()

@app.get("/")
def root():
    return {"status": "Aktien-App läuft ✅", "überwachte Aktien": tracked_tickers}

@app.get("/signal/{ticker}")
def manual_check(ticker: str, background_tasks: BackgroundTasks):
    try:
        df = yf.download(ticker, period="1mo", interval="1d")
        close = df["Close"]
        sma5 = close.rolling(window=5).mean()
        sma20 = close.rolling(window=20).mean()

        if sma5.iloc[-1] > sma20.iloc[-1]:
            signal = "KAUFEN"
        elif sma5.iloc[-1] < sma20.iloc[-1]:
            signal = "VERKAUFEN"
        else:
            signal = "HALTEN"

        if signal != "HALTEN":
            background_tasks.add_task(send_email, ticker, close.iloc[-1], signal)

        return {"signal": signal, "preis": close.iloc[-1]}

    except Exception as e:
        return {"error": str(e)}
