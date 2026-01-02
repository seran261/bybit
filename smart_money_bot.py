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
        print(f"[INIT] Locked symbols: {len(self.symbols)}")

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
        if len(kl) < 20:
            return None
        tr = []
        for i in range(1, 15):
            h = float(kl[i][2])
            l = float(kl[i][3])
            pc = float(kl[i-1][4])
            tr.append(max(h-l, abs(h-pc), abs(l-pc)))
        return sum(tr) / len(tr)

    def htf_trend(self, kl):
        highs = [float(x[2]) for x in kl]
        lows  = [float(x[3]) for x in kl]
        close = float(kl[-1][4])

        if close > max(highs[-STRUCTURE_LOOKBACK:]):
            return "BULL"
        if close < min(lows[-STRUCTURE_LOOKBACK:]):
            return "BEAR"
        return "RANGE"

    def bos(self, kl):
        highs = [float(x[2]) for x in kl]
        lows  = [float(x[3]) for x in kl]
        close = float(kl[-1][4])

        if close > max(highs[-STRUCTURE_LOOKBACK:]):
            return "BUY"
        if close < min(lows[-STRUCTURE_LOOKBACK:]):
            return "SELL"
        return None

    def sweep(self, kl):
        highs = [float(x[2]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        lows  = [float(x[3]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        last = kl[-1]
        close = float(last[4])

        if float(last[2]) > max(highs[:-1]) and close < max(highs[:-1]):
            return "SELL"
        if float(last[3]) < min(lows[:-1]) and close > min(lows[:-1]):
            return "BUY"
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
        print(f"[{datetime.now()}] 🚀 Bybit Futures Smart Money Bot Started")

        while True:
            try:
                for sym in self.symbols:

                    # 🔒 symbol lock
                    if sym in self.trades and time.time() - self.trades[sym] < SYMBOL_LOCK_SECONDS:
                        continue

                    ltf = self.klines(sym, LTF_INTERVAL)
                    htf1 = self.klines(sym, HTF_1H)
                    htf4 = self.klines(sym, HTF_4H)

                    if len(ltf) < 50 or len(htf1) < 50 or len(htf4) < 50:
                        continue

                    t1 = self.htf_trend(htf1)
                    t4 = self.htf_trend(htf4)

                    # 🧠 relaxed HTF filter
                    if t1 == "RANGE" and t4 == "RANGE":
                        continue

                    signal = self.bos(ltf) or self.sweep(ltf)
                    if not signal:
                        continue

                    # direction alignment
                    if signal == "BUY" and t1 == "BEAR":
                        continue
                    if signal == "SELL" and t1 == "BULL":
                        continue

                    atr = self.atr(ltf)
                    if atr is None:
                        continue

                    price = float(ltf[-1][4])
                    sl = price - atr * ATR_MULTIPLIER if signal == "BUY" else price + atr * ATR_MULTIPLIER
                    tp = price + atr * 2 if signal == "BUY" else price - atr * 2

                    # DEBUG LOG
                    print(f"{sym} | HTF1={t1} HTF4={t4} | SIGNAL={signal}")

                    self.trades[sym] = time.time()
                    save_json("trades.json", self.trades)

                    self.send(
                        f"🚀 {signal} {sym}USDT (Futures)\n"
                        f"HTF Bias: 1H={t1}, 4H={t4}\n"
                        f"Entry: {price:.4f}\n"
                        f"TP: {tp:.4f}\n"
                        f"SL: {sl:.4f}"
                    )

                # cleanup old locks
                for s in list(self.trades):
                    if time.time() - self.trades[s] > SYMBOL_LOCK_SECONDS:
                        del self.trades[s]

            except Exception as e:
                print("Runtime error:", e)

            time.sleep(SCAN_INTERVAL_SECONDS)

# ================= START =================

if __name__ == "__main__":
    SmartMoneyBot().run()
