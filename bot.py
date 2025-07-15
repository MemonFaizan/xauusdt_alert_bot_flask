import requests
import pandas as pd
import time
import csv
import os
from datetime import datetime
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
import warnings
from dotenv import load_dotenv
warnings.filterwarnings("ignore")
load_dotenv()
API_KEY = os.getenv("API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TIMEFRAME = "5min"
CHECK_INTERVAL = 60  # in seconds
CSV_FILE = "gold_sniper_alerts.csv"

# === INIT CSV ===
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Sr. No", "Timestamp", "Signal", "Price", "Timeframe",
                "TP", "SL", "Risk:Reward", "Point Diff"
            ])

# === GET CANDLE DATA ===
def get_candle_data(interval="5min"):
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={interval}&apikey={API_KEY}&outputsize=100"
    response = requests.get(url)
    data = response.json()
    if "values" in data:
        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        df = df.astype(float).sort_index()
        return df
    else:
        raise ValueError("Failed to retrieve candle data")

# === TELEGRAM ALERT ===
def send_telegram_alert(signal, price, tp, sl, timeframe):
    message = f"""🚨 [ALERT - {datetime.now().strftime("%I:%M %p")}]
📈 {signal.upper()} - XAU/USD
💰 CMP: ₹{price:.2f}
🎯 TP: ₹{tp:.2f}
🛑 SL: ₹{sl:.2f}
⏱️ Timeframe: {timeframe}
📌 Reason:
🔹 Supply/Demand Zone Retest + EMA+RSI Confirmation
🔹 EMA(8 & 21) Trend Alignment
🔹 RSI + Engulfing Setup
📣 Fire Now!"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': message})

# === LOG TO CSV ===
def log_to_csv(index, timestamp, signal, price, tp, sl, timeframe):
    rr = round(abs(tp - price) / abs(price - sl), 2) if price != sl else "∞"
    points = round(tp - price, 2) if signal == "BUY" else round(price - tp, 2)
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            index, timestamp, signal, round(price, 2), timeframe,
            round(tp, 2), round(sl, 2), rr, points
        ])

# === ZONE DETECTION ===
def detect_zones(df, zone_type='demand', threshold=2):
    zones = []
    for i in range(2, len(df) - 3):
        if zone_type == 'demand':
            if all(df['close'].iloc[j] > df['open'].iloc[j] for j in range(i, i+3)):
                change = df['close'].iloc[i+2] - df['open'].iloc[i]
                if change >= threshold:
                    zone_low = min(df['low'].iloc[i:i+3])
                    zone_high = max(df['high'].iloc[i:i+3])
                    zones.append((zone_low, zone_high))
        elif zone_type == 'supply':
            if all(df['close'].iloc[j] < df['open'].iloc[j] for j in range(i, i+3)):
                change = df['open'].iloc[i] - df['close'].iloc[i+2]
                if change >= threshold:
                    zone_low = min(df['low'].iloc[i:i+3])
                    zone_high = max(df['high'].iloc[i:i+3])
                    zones.append((zone_low, zone_high))
    return zones[-2:]

# === SIGNAL LOGIC (Improved Accuracy) ===
def check_supply_demand_alert(df, demand_zones, supply_zones):
    ema_8 = EMAIndicator(df['close'], 8).ema_indicator()
    ema_21 = EMAIndicator(df['close'], 21).ema_indicator()
    rsi = RSIIndicator(df['close'], 14).rsi()

    candle = df.iloc[-1]
    prev = df.iloc[-2]
    price = candle['close']

    signal = None
    sl, tp = None, None

    for low, high in demand_zones:
        if low <= price <= high:
            if (price > ema_8.iloc[-1] > ema_21.iloc[-1] and
                rsi.iloc[-1] > 45 and
                candle['close'] > candle['open'] and
                candle['low'] < prev['low']):
                signal = 'BUY'
                sl = low - 0.5
                tp = price + (high - low) * 2
                break

    for low, high in supply_zones:
        if low <= price <= high:
            if (price < ema_8.iloc[-1] < ema_21.iloc[-1] and
                rsi.iloc[-1] < 55 and
                candle['close'] < candle['open'] and
                candle['high'] > prev['high']):
                signal = 'SELL'
                sl = high + 0.5
                tp = price - (high - low) * 2
                break

    return signal, price, tp, sl

# === MAIN LOOP ===
def main():
    signal_count = 1
    last_signal = None
    init_csv()

    while True:
        try:
            df_5m = get_candle_data("5min")
            df_15m = get_candle_data("15min")

            demand_zones = detect_zones(df_15m, "demand")
            supply_zones = detect_zones(df_15m, "supply")

            signal, price, tp, sl = check_supply_demand_alert(df_5m, demand_zones, supply_zones)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if signal and signal != last_signal:
                send_telegram_alert(signal, price, tp, sl, TIMEFRAME)
                log_to_csv(signal_count, now, signal, price, tp, sl, TIMEFRAME)
                last_signal = signal
                signal_count += 1
                print(f"[{now}] ✅ Signal sent: {signal} @ {price:.2f}")
            else:
                print(f"[{now}] No signal | Price: {price:.2f}")

        except Exception as e:
            print(f"❌ Error: {e}")

        time.sleep(CHECK_INTERVAL)

# === START BOT ===
if __name__ == "__main__":
    main()
