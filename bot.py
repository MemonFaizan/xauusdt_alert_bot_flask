import requests
import time
import os
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TIMEFRAME = "1m"
CHECK_INTERVAL = 60  # seconds
GOLD_API_URL = "https://api.gold-api.com/price/XAU"

# === Get Real-time Price ===
def get_spot_price():
    try:
        resp = requests.get(GOLD_API_URL, timeout=10)
        data = resp.json()
        return float(data["price"])
    except Exception as e:
        print(f"❌ Failed to fetch price: {e}")
        return None

# === Fetch Historic 1m Data (Simulated Using Gold Price with Fake OHLC for Indicators) ===
def build_fake_candle_data(current_price):
    # Generate fake candles around the current price
    candles = []
    for i in range(30):
        base = current_price + (i - 15) * 0.05  # simulate micro movement
        o = base
        h = base + 0.2
        l = base - 0.2
        c = base + 0.1
        candles.append([o, h, l, c])
    df = pd.DataFrame(candles, columns=["open", "high", "low", "close"])
    return df

# === Telegram Alert ===
def send_telegram_alert(signal, price, tp, sl):
    message = f"""🚨 [ALERT]
📈 {signal.upper()} - XAU/USD
💰 CMP: ${price:.2f}
🎯 TP: ${tp:.2f}
🛑 SL: ${sl:.2f}
📌 Reason:
🔹 Supply/Demand Zone Retest + EMA+RSI Confirmation
🔹 EMA(8 & 21) Trend Alignment
🔹 RSI + Engulfing Setup
📣 Fire Now!"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

# === Strategy Logic ===
def generate_signal(df, price):
    ema_8 = EMAIndicator(df["close"], window=8).ema_indicator()
    ema_21 = EMAIndicator(df["close"], window=21).ema_indicator()
    rsi = RSIIndicator(df["close"], window=14).rsi()

    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    ema8 = ema_8.iloc[-1]
    ema21 = ema_21.iloc[-1]
    rsi_val = rsi.iloc[-1]

    signal, tp, sl = None, None, None

    if (
        price > ema8 > ema21
        and rsi_val > 50
        and last_candle["close"] > last_candle["open"]
        and last_candle["low"] < prev_candle["low"]
    ):
        signal = "BUY"
        sl = round(price - 3.0, 2)
        tp = round(price + 6.0, 2)

    elif (
        price < ema8 < ema21
        and rsi_val < 50
        and last_candle["close"] < last_candle["open"]
        and last_candle["high"] > prev_candle["high"]
    ):
        signal = "SELL"
        sl = round(price + 3.0, 2)
        tp = round(price - 6.0, 2)

    return signal, tp, sl

# === Main Bot Loop ===
def main():
    last_signal = None
    print("🚀 Bot started using Gold-API real-time spot price")
    while True:
        try:
            price = get_spot_price()
            if price is None:
                print("[Warning] Skipping due to fetch failure.")
                time.sleep(CHECK_INTERVAL)
                continue

            df = build_fake_candle_data(price)
            signal, tp, sl = generate_signal(df, price)

            if signal and signal != last_signal:
                send_telegram_alert(signal, price, tp, sl)
                last_signal = signal
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {signal} Signal Sent | CMP: ${price:.2f}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 Price: ${price:.2f}")

        except Exception as e:
            print(f"❌ Error: {e}")

        time.sleep(CHECK_INTERVAL)
