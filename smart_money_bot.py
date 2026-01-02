import requests
import time
import json
import os
from datetime import datetime
from config import *

# ================= GLOBAL HEADERS =================

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

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
        self.symbols = self.fetch_top_coins() or ["BTC", "ETH"]
        self.clean_trades()

    # ================= SAFETY =================

    def clean_trades(self):
        for s in list(self.trades.keys()):
            if not isinstance(self.trades[s], dict) or "side" not in self.trades[s]:
                del self.trades[s]
        save_json("trades.json", self.trades)

    # ================= BYBIT MARKET =================

    def fetch_top_coins(self):
        urls = [
            "https://api.bybit.com/v5/market/tickers",
            "https://api.bybit.com/spot/v3/public/quote/ticker/24hr"
        ]

        for url in urls:
            try:
                r = requests.get(
                    url,
                    params={"category": "spot"} if "v5" in url else {},
                    headers=HEADERS,
                    timeout=15
                )

                if r.status_code != 200:
                    continue

                data = r.json()

                if "result" in data:
                    items = data["result"]["list"]
                    coins = [
                        x["symbol"].replace("USDT", "")
                        for x in items
                        if x["symbol"].endswith("USDT")
                        and float(x.get("turnover24h", 0)) >= MIN_VOLUME_USDT
                    ]
                else:
                    coins = [
                        x["symbol"].replace("USDT", "")
                        for x in data
                        if x["symbol"].endswith("USDT")
                    ]

                if coins:
                    print(f"Loaded {len(coins)} symbols")
                    return coins[:TOP_N_COINS]

            except Exception as e:
                print("Symbol fetch error:", e)

        print("⚠ Using fallback symbols")
        return ["BTC", "ETH", "SOL", "BNB", "XRP"]

    def klines(self, symbol):
        r = requests.get(
            f"{BYBIT_BASE}/v5/market/kline",
            params={
                "category": "spot",
                "symbol": f"{symbol}USDT",
                "interval": KLINE_INTERVAL,
                "limit": KLINE_LIMIT
            },
            headers=HEADERS,
            timeout=10
        )
        if r.status_code != 200:
            return []
        return r.json().get("result", {}).get("list", [])

    def price(self, symbol):
        r = requests.get(
            f"{BYBIT_BASE}/v5/market/tickers",
            params={"category": "spot", "symbol": f"{symbol}USDT"},
            headers=HEADERS,
            timeout=5
        )
        if r.status_code != 200:
            return None
        return float(r.json()["result"]["list"][0]["lastPrice"])

    # ================= INDICATORS =================

    def atr(self, kl, length=14):
        if len(kl) < length + 1:
            return None

        tr = []
        for i in range(1, length):
            h = float(kl[i][2])
            l = float(kl[i][3])
            pc = float(kl[i - 1][4])
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(tr) / len(tr)

    def bos(self, kl):
        highs = [float(x[2]) for x in kl]
        lows  = [float(x[3]) for x in kl]
        close = float(kl[-1][4])

        if close > max(highs[-STRUCTURE_LOOKBACK:]):
            return "BOS_BUY"
        if close < min(lows[-STRUCTURE_LOOKBACK:]):
            return "BOS_SELL"
        return None

    def sweep(self, kl):
        highs = [float(x[2]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        lows  = [float(x[3]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        last = kl[-1]

        if float(last[2]) > max(highs[:-1]) and float(last[4]) < max(highs[:-1]):
            return "SWEEP_HIGH_SELL"
        if float(last[3]) < min(lows[:-1]) and float(last[4]) > min(lows[:-1]):
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
        if len(self.trades) >= MAX_TRADES or atr is None:
            return

        d = atr * ATR_MULTIPLIER

        self.trades[symbol] = {
            "side": side,
            "entry": price,
            "sl": price - d if side == "BUY" else price + d,
            "tp": price + 2*d if side == "BUY" else price - 2*d,
            "opened": time.time()
        }

        self.send(
            f"🚀 {side} {symbol}\n"
            f"Entry: {price:.4f}\n"
            f"TP: {self.trades[symbol]['tp']:.4f}\n"
            f"SL: {self.trades[symbol]['sl']:.4f}"
        )

    def manage_trade(self, symbol):
        t = self.trades.get(symbol)
        price = self.price(symbol)
        if not t or price is None:
            return

        if time.time() - t["opened"] < MIN_HOLD_SECONDS:
            return

        side = t["side"]

        if (side == "BUY" and price <= t["sl"]) or (side == "SELL" and price >= t["sl"]):
            self.send(f"❌ SL HIT {symbol}")
            del self.trades[symbol]
            return

        if (side == "BUY" and price >= t["tp"]) or (side == "SELL" and price <= t["tp"]):
            self.send(f"✅ TP HIT {symbol}")
            del self.trades[symbol]

    # ================= LOOP =================

    def run(self):
        print(f"[{datetime.now()}] Bybit Smart Money Bot Started")

        while True:
            try:
                for symbol in self.symbols:
                    if symbol in self.trades:
                        continue

                    kl = self.klines(symbol)
                    if len(kl) < 30:
                        continue

                    signal = self.bos(kl) or self.sweep(kl)
                    if not signal:
                        continue

                    side = "BUY" if "BUY" in signal else "SELL"
                    price = float(kl[-1][4])
                    atr = self.atr(kl)

                    self.send(f"📌 {signal} {symbol}")
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
