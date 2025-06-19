from tradingview_ta import TA_Handler, Interval
import time
import datetime
import requests
from bs4 import BeautifulSoup
import schedule
import threading

# === Konfigurasi Pair dan Telegram ===
symbol_name = "XAUUSD"
symbol = "GOLD"
exchange = "TVC"
screener = "cfd"
interval = Interval.INTERVAL_1_DAY

TELEGRAM_TOKEN = "7706295683:AAGyO1rBAC9_jmv3EaALMmpL2-NzkeSj7zo"
TELEGRAM_CHAT_ID = "-1002734745692"  # Chat ID grup kamu

# === Fungsi Kirim Telegram ===
def kirim_telegram(pesan):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": pesan,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=data)
    except Exception as e:
        print("❌ Gagal kirim Telegram:", e)

# === Ambil dan Analisis Sentimen Berita ===
def get_market_sentiment():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        headlines = []

        # Sumber 1: Investing
        try:
            r1 = requests.get("https://www.investing.com/news/commodities-news", headers=headers)
            s1 = BeautifulSoup(r1.text, "html.parser")
            headlines += [item.get_text(strip=True) for item in s1.select("article h3")[:3]]
        except: pass

        # Sumber 2: MarketWatch
        try:
            r2 = requests.get("https://www.marketwatch.com/investing/future/gold", headers=headers)
            s2 = BeautifulSoup(r2.text, "html.parser")
            headlines += [item.get_text(strip=True) for item in s2.select("h3.article__headline")[:2]]
        except: pass

        # Sumber 3: Reuters
        try:
            r3 = requests.get("https://www.reuters.com/markets/commodities/", headers=headers)
            s3 = BeautifulSoup(r3.text, "html.parser")
            headlines += [item.get_text(strip=True) for item in s3.select("h3.story-title, h2.story-title")[:3]]
        except: pass

        combined_text = " ".join(headlines).lower()

        bullish_keywords = ["gold rises", "gold up", "bullish", "inflation", "safe haven", "war", "conflict", "geopolitical"]
        bearish_keywords = ["gold falls", "gold down", "bearish", "rate hike", "hawkish", "interest rate"]

        matched_bullish = [word for word in bullish_keywords if word in combined_text]
        matched_bearish = [word for word in bearish_keywords if word in combined_text]

        if matched_bullish and not matched_bearish:
            sentiment = "BULLISH"
            reason = f"Berita positif: {', '.join(matched_bullish)}"
        elif matched_bearish and not matched_bullish:
            sentiment = "BEARISH"
            reason = f"Berita negatif: {', '.join(matched_bearish)}"
        elif matched_bullish and matched_bearish:
            sentiment = "NEUTRAL"
            reason = f"Berita campuran: positif ({', '.join(matched_bullish)}) & negatif ({', '.join(matched_bearish)})"
        else:
            sentiment = "NEUTRAL"
            reason = "Tidak ditemukan kata kunci signifikan."

        return sentiment, headlines, reason

    except Exception as e:
        return "UNKNOWN", [f"Error ambil berita: {e}"], str(e)

# === Fungsi Entry/Exit Risk-Reward ===
def smart_entry_stop(recommendation, indicators):
    close = indicators.get("close", 0)
    ema20 = indicators.get("EMA20", 0)
    rsi = indicators.get("RSI", 50)

    trend = "UP" if close > ema20 else "DOWN"
    sl_pct = 0.01
    tp_pct = 0.02

    if recommendation == "BUY":
        entry = close
        tp = entry * (1 + tp_pct)
        sl = entry * (1 - sl_pct)
    elif recommendation == "SELL":
        entry = close
        tp = entry * (1 - tp_pct)
        sl = entry * (1 + sl_pct)
    else:
        entry = tp = sl = close

    return entry, tp, sl, trend, rsi

# === Fungsi Ambil Sinyal Utama ===
def get_signal():
    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener=screener,
            interval=interval
        )

        analysis = handler.get_analysis()
        summary = analysis.summary
        indicators = analysis.indicators
        recommendation = summary['RECOMMENDATION']

        entry, tp, sl, trend, rsi = smart_entry_stop(recommendation, indicators)
        sentiment, news, reason = get_market_sentiment()

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        pesan = f"""📌 *Sinyal Trading {symbol_name}*
⏰ {now}
📊 Sinyal: *{recommendation}*
📈 Tren: {trend} | RSI: {rsi:.2f}
📰 Sentimen: {sentiment}
📋 Alasan: {reason}
"""
        for i, h in enumerate(news):
            pesan += f"{i+1}. {h}\n"

        if recommendation in ["BUY", "SELL"]:
            pesan += f"""
✅ Entry: *{recommendation}* di {entry:.2f}
🎯 Take Profit (2%): {tp:.2f}
⛔ Stop Loss (1%): {sl:.2f}
"""

        if sentiment == recommendation:
            pesan += "\n🧠 *Sinyal & berita SELARAS* ✅"
        elif sentiment in ["BULLISH", "BEARISH"] and sentiment != recommendation:
            pesan += "\n⚠️ *Sinyal dan berita bertentangan* ⚠️"

        print(pesan)
        kirim_telegram(pesan)

    except Exception as e:
        print("❌ Gagal ambil data:", e)

# === Jadwal Eksekusi Setiap 5 Jam Mulai Pukul 07:00 ===
def start_schedule():
    times = ["07:00", "12:00", "17:00", "22:00", "03:00"]
    for t in times:
        schedule.every().day.at(t).do(get_signal)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    print("🔁 Mulai testing setiap 60 detik...\n")
    while True:
        get_signal()
        time.sleep(180)  # Ganti waktu sesuai kebutuhan
