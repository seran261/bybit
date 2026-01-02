HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}
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
        self.symbols = self.fetch_top_coins()
        self.clean_trades()

    # ================= SAFETY =================

    def clean_trades(self):
        for s in list(self.trades.keys()):
            if "side" not in self.trades[s]:
                del self.trades[s]
        save_json("trades.json", self.trades)

    # ================= BYBIT MARKET =================

    def fetch_top_coins(self):
        r = requests.get(
            f"{BYBIT_BASE}/v5/market/tickers",
            params={"category": "spot"},
            timeout=15
        )
        r.raise_for_status()

        data = r.json()["result"]["list"]

        coins = [
            x["symbol"].replace("USDT", "")
            for x in data
            if x["symbol"].endswith("USDT")
            and float(x.get("turnover24h", 0)) >= MIN_VOLUME_USDT
        ]

        return coins[:TOP_N_COINS]

    def klines(self, symbol):
        r = requests.get(
            f"{BYBIT_BASE}/v5/market/kline",
            params={
                "category": "spot",
                "symbol": f"{symbol}USDT",
                "interval": KLINE_INTERVAL,
                "limit": KLINE_LIMIT
            },
            timeout=10
        )
        r.raise_for_status()
        return r.json()["result"]["list"]

    def price(self, symbol):
        r = requests.get(
            f"{BYBIT_BASE}/v5/market/tickers",
            params={"category": "spot", "symbol": f"{symbol}USDT"},
            timeout=5
        )
        r.raise_for_status()
        return float(r.json()["result"]["list"][0]["lastPrice"])

    # ================= INDICATORS =================

    def atr(self, kl, length=14):
        tr = []
        for i in range(1, length):
            h = float(kl[i][2])
            l = float(kl[i][3])
            pc = float(kl[i - 1][4])
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(tr) / len(tr)

    def bos_choch(self, kl):
        highs = [float(x[2]) for x in kl]
        lows  = [float(x[3]) for x in kl]
        close = float(kl[-1][4])

        rh = max(highs[-STRUCTURE_LOOKBACK:])
        rl = min(lows[-STRUCTURE_LOOKBACK:])

        if close > rh:
            return "BOS_BUY"
        if close < rl:
            return "BOS_SELL"
        return None

    def liquidity_sweep(self, kl):
        highs = [float(x[2]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        lows  = [float(x[3]) for x in kl[-LIQUIDITY_LOOKBACK:]]

        last = kl[-1]
        wick_high = float(last[2])
        wick_low  = float(last[3])
        close     = float(last[4])

        if wick_high > max(highs[:-1]) and close < max(highs[:-1]):
            return "SWEEP_HIGH_SELL"
        if wick_low < min(lows[:-1]) and close > min(lows[:-1]):
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
        stat = self.stats.setdefault(symbol, {"wins": 0, "losses": 0})
        stat["wins" if win else "losses"] += 1
        del self.trades[symbol]
        save_json("stats.json", self.stats)

    def manage_trade(self, symbol):
        t = self.trades.get(symbol)
        if not t:
            return

        price = self.price(symbol)
        side = t["side"]

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

        if "tp2" not in t["hit"] and hit("tp2"):
            t["hit"].append("tp2")
            self.send(f"🥈 TP2 HIT {symbol}")

        if "tp3" not in t["hit"] and hit("tp3"):
            self.close_trade(symbol, True, "TP3 HIT")

    # ================= LOOP =================

    def run(self):
        print(f"[{datetime.now()}] Bybit Smart Money Bot Started")

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

