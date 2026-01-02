import requests
import time
import json
import os
from datetime import datetime
from config import *

# ================= FILE UTILS =================

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ================= BOT =================

class SmartMoneyBot:

    def __init__(self):
        self.trades = load_json("trades.json")
        self.stats = load_json("stats.json")
        self.symbols = self.fetch_top_200()
        self.clean_trades()

    # ================= SAFETY =================

    def clean_trades(self):
        for s in list(self.trades.keys()):
            t = self.trades[s]
            if not isinstance(t, dict) or "side" not in t:
                del self.trades[s]
        save_json("trades.json", self.trades)

    # ================= MARKET =================

    def fetch_top_200(self):
        r = requests.get(f"{BINANCE_SPOT_BASE}/ticker/24hr", timeout=15)
        r.raise_for_status()
        data = r.json()

        coins = [
            x["symbol"].replace("USDT", "")
            for x in data
            if x["symbol"].endswith("USDT")
            and float(x["quoteVolume"]) >= MIN_VOLUME_USDT
            and not any(b in x["symbol"] for b in ["UP", "DOWN", "BULL", "BEAR"])
        ]

        return coins[:TOP_N_COINS]

    def klines(self, symbol):
        r = requests.get(
            f"{BINANCE_SPOT_BASE}/klines",
            params={"symbol": f"{symbol}USDT", "interval": KLINE_INTERVAL, "limit": KLINE_LIMIT},
            timeout=10
        )
        r.raise_for_status()
        return r.json()

    def price(self, symbol):
        r = requests.get(
            f"{BINANCE_SPOT_BASE}/ticker/price",
            params={"symbol": f"{symbol}USDT"},
            timeout=5
        )
        r.raise_for_status()
        return float(r.json()["price"])

    def atr(self, kl, length=14):
        tr = []
        for i in range(1, length):
            h = float(kl[i][2])
            l = float(kl[i][3])
            pc = float(kl[i - 1][4])
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(tr) / len(tr)

    # ================= SMART MONEY =================

    def bos_choch(self, kl):
        highs = [float(x[2]) for x in kl]
        lows = [float(x[3]) for x in kl]
        close = float(kl[-1][4])

        rh = max(highs[-STRUCTURE_LOOKBACK:])
        rl = min(lows[-STRUCTURE_LOOKBACK:])
        ph = max(highs[-STRUCTURE_LOOKBACK-1:-1])
        pl = min(lows[-STRUCTURE_LOOKBACK-1:-1])

        if close > rh:
            return "BOS_BUY"
        if close < rl:
            return "BOS_SELL"
        if close > ph:
            return "CHOCH_BUY"
        if close < pl:
            return "CHOCH_SELL"
        return None

    def liquidity_sweep(self, kl):
        highs = [float(x[2]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        lows = [float(x[3]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        last = kl[-1]

        eqh = max(highs[:-1])
        eql = min(lows[:-1])

        wick_high = float(last[2])
        wick_low = float(last[3])
        close = float(last[4])

        if wick_high > eqh and close < eqh:
            return "SWEEP_HIGH_SELL"
        if wick_low < eql and close > eql:
            return "SWEEP_LOW_BUY"
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

    # ================= TRADING =================

    def open_trade(self, symbol, side, price, atr):
        if len(self.trades) >= MAX_TRADES:
            return

        d = atr * ATR_MULTIPLIER

        self.trades[symbol] = {
            "side": side,
            "entry": price,
            "sl": price - d if side == "BUY" else price + d,
            "tp1": price + d if side == "BUY" else price - d,
            "tp2": price + 2*d if side == "BUY" else price - 2*d,
            "tp3": price + 3*d if side == "BUY" else price - 3*d,
            "opened": time.time(),
            "hit": []
        }

        self.send(
            f"🚀 {side} {symbol}\n"
            f"Entry: {price:.4f}\n"
            f"TP1: {self.trades[symbol]['tp1']:.4f}\n"
            f"TP2: {self.trades[symbol]['tp2']:.4f}\n"
            f"TP3: {self.trades[symbol]['tp3']:.4f}\n"
            f"SL: {self.trades[symbol]['sl']:.4f}"
        )

    def close_trade(self, symbol, win, reason):
        self.send(f"{'✅' if win else '❌'} {reason} {symbol}")
        s = self.stats.setdefault(symbol, {"wins": 0, "losses": 0})
        s["wins" if win else "losses"] += 1
        del self.trades[symbol]
        save_json("stats.json", self.stats)

    def manage_trade(self, symbol):
        t = self.trades.get(symbol)
        if not t or "side" not in t:
            self.trades.pop(symbol, None)
            return

        side = t["side"]
        price = self.price(symbol)

        if time.time() - t["opened"] < MIN_HOLD_SECONDS:
            return

        def hit(tp): 
            return price >= t[tp] if side == "BUY" else price <= t[tp]

        if (side == "BUY" and price <= t["sl"]) or (side == "SELL" and price >= t["sl"]):
            self.close_trade(symbol, False, "SL HIT")
            return

        if "tp1" not in t["hit"] and hit("tp1"):
            t["hit"].append("tp1")
            self.send(f"🥇 TP1 HIT {symbol}")

        if "tp1" in t["hit"] and "tp2" not in t["hit"] and hit("tp2"):
            t["hit"].append("tp2")
            self.send(f"🥈 TP2 HIT {symbol}")

        if "tp2" in t["hit"] and hit("tp3"):
            self.close_trade(symbol, True, "TP3 HIT")

    # ================= LOOP =================

    def run(self):
        print(f"[{datetime.now()}] Bot started")

        while True:
            try:
                for symbol in self.symbols:
                    if symbol in self.trades:
                        continue

                    kl = self.klines(symbol)
                    bos = self.bos_choch(kl)
                    sweep = self.liquidity_sweep(kl)

                    if not bos and not sweep:
                        continue

                    side = "BUY" if (
                        (bos and "BUY" in bos) or sweep == "SWEEP_LOW_BUY"
                    ) else "SELL"

                    price = float(kl[-1][4])
                    atr = self.atr(kl)

                    self.send(f"📌 {bos or sweep} {symbol}")
                    self.open_trade(symbol, side, price, atr)

                for symbol in list(self.trades.keys()):
                    self.manage_trade(symbol)

                save_json("trades.json", self.trades)

            except Exception as e:
                print("Runtime error:", e)

            time.sleep(SCAN_INTERVAL_SECONDS)

# ================= START =================

if __name__ == "__main__":
    SmartMoneyBot().run()
