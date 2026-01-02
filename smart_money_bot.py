import requests, time, json, os
from datetime import datetime
from config import *

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# ================= FILE UTILS =================

def load_json(p):
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except:
            return {}
    return {}

def save_json(p, d):
    json.dump(d, open(p, "w"), indent=2)

# ================= BOT =================

class SmartMoneyBot:

    def __init__(self):
        self.trades = load_json("trades.json")
        self.symbols = TOP_100_SYMBOLS
        print(f"🔒 Locked symbols: {len(self.symbols)}")

    # ================= BYBIT FUTURES =================

    def klines(self, symbol, interval):
        r = requests.get(
            f"{BYBIT_BASE}/v5/market/kline",
            params={
                "category": "linear",
                "symbol": f"{symbol}USDT",
                "interval": interval,
                "limit": KLINE_LIMIT
            },
            headers=HEADERS,
            timeout=10
        )
        if r.status_code != 200:
            return []
        return r.json().get("result", {}).get("list", [])

    # ================= INDICATORS =================

    def atr(self, kl):
        tr = []
        for i in range(1, 15):
            h, l, pc = float(kl[i][2]), float(kl[i][3]), float(kl[i-1][4])
            tr.append(max(h-l, abs(h-pc), abs(l-pc)))
        return sum(tr)/len(tr)

    def trend(self, kl):
        close = float(kl[-1][4])
        highs = [float(x[2]) for x in kl[-50:]]
        lows  = [float(x[3]) for x in kl[-50:]]
        if close > sum(highs)/len(highs): return "BULL"
        if close < sum(lows)/len(lows):   return "BEAR"
        return "RANGE"

    def bos(self, kl):
        highs = [float(x[2]) for x in kl]
        lows  = [float(x[3]) for x in kl]
        close = float(kl[-1][4])
        if close > max(highs[-STRUCTURE_LOOKBACK:]): return "BUY"
        if close < min(lows[-STRUCTURE_LOOKBACK:]):  return "SELL"
        return None

    def sweep(self, kl):
        h = [float(x[2]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        l = [float(x[3]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        c = float(kl[-1][4])
        if float(kl[-1][2]) > max(h[:-1]) and c < max(h[:-1]): return "SELL"
        if float(kl[-1][3]) < min(l[:-1]) and c > min(l[:-1]): return "BUY"
        return None

    # ================= TELEGRAM =================

    def send(self, msg):
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
                timeout=5
            )
        except:
            pass

    # ================= LOOP =================

    def run(self):
        print(f"[{datetime.now()}] 🚀 Bybit Futures Bot Started")

        while True:
            try:
                for s in self.symbols:
                    if s in self.trades: continue

                    ltf = self.klines(s, LTF_INTERVAL)
                    htf1 = self.klines(s, HTF_1H)
                    htf4 = self.klines(s, HTF_4H)

                    if len(ltf)<50 or len(htf1)<50 or len(htf4)<50:
                        continue

                    # 🧠 HTF CONFIRMATION
                    t1, t4 = self.trend(htf1), self.trend(htf4)
                    if t1 != t4 or t1 == "RANGE":
                        continue

                    signal = self.bos(ltf) or self.sweep(ltf)
                    if not signal: continue

                    if (signal=="BUY" and t1!="BULL") or (signal=="SELL" and t1!="BEAR"):
                        continue

                    price = float(ltf[-1][4])
                    atr = self.atr(ltf)
                    sl = price - atr*ATR_MULTIPLIER if signal=="BUY" else price + atr*ATR_MULTIPLIER
                    tp = price + atr*2 if signal=="BUY" else price - atr*2

                    self.trades[s] = time.time()
                    self.send(
                        f"🚀 {signal} {s}USDT\n"
                        f"HTF: {t1} (1H/4H)\n"
                        f"Entry: {price:.4f}\n"
                        f"TP: {tp:.4f}\n"
                        f"SL: {sl:.4f}"
                    )

                # unlock old trades
                for k in list(self.trades):
                    if time.time() - self.trades[k] > 1800:
                        del self.trades[k]

            except Exception as e:
                print("Runtime error:", e)

            time.sleep(SCAN_INTERVAL_SECONDS)

# ================= START =================

if __name__ == "__main__":
    SmartMoneyBot().run()
