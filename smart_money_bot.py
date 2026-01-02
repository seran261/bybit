import requests, time, json, hmac, hashlib
from datetime import datetime
from config import *

HEADERS = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

# ================= HELPERS =================

def now_ms():
    return str(int(time.time() * 1000))

def sign(payload: str):
    return hmac.new(
        BYBIT_API_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

def bybit_public(path, params=None):
    try:
        r = requests.get(BYBIT_BASE + path, params=params, headers=HEADERS, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print("Public API error:", e)
        return None

def bybit_private(method, path, body=None):
    body = body or {}
    ts = now_ms()
    recv = "5000"
    payload = ts + BYBIT_API_KEY + recv + json.dumps(body)
    sig = sign(payload)

    headers = {
        **HEADERS,
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": sig,
        "X-BAPI-TIMESTAMP": ts,
        "X-BAPI-RECV-WINDOW": recv
    }

    try:
        r = requests.request(method, BYBIT_BASE + path, json=body, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        print("Private API error:", e)
        return None

def safe_klines(resp):
    if not resp:
        return []
    r = resp.get("result", {})
    return r.get("list", []) if isinstance(r, dict) else []

# ================= BOT =================

class SmartMoneyBot:

    def __init__(self):
        self.active = set()
        self.symbols = TOP_200_SYMBOLS
        self.send("✅ BOT STARTED SUCCESSFULLY\nBybit Smart Money Bot is LIVE 🚀")
        print(f"[INIT] Symbols loaded: {len(self.symbols)}", flush=True)

    # ---------- TELEGRAM ----------

    def send(self, msg):
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
                timeout=5
            )
            print("Telegram:", r.text)
        except Exception as e:
            print("Telegram error:", e)

    # ---------- MARKET ----------

    def klines(self, s, tf):
        return safe_klines(bybit_public("/v5/market/kline", {
            "category": "linear",
            "symbol": f"{s}USDT",
            "interval": tf,
            "limit": KLINE_LIMIT
        }))

    def funding(self, s):
        d = bybit_public("/v5/market/funding/history", {
            "category": "linear", "symbol": f"{s}USDT", "limit": 1
        })
        try:
            return abs(float(d["result"]["list"][0]["fundingRate"]))
        except:
            return 0.0

    def position_open(self, s):
        r = bybit_private("GET", "/v5/position/list", {
            "category": "linear",
            "symbol": f"{s}USDT"
        })
        try:
            return float(r["result"]["list"][0]["size"]) != 0
        except:
            return False

    # ---------- LOGIC ----------

    def atr(self, kl):
        if len(kl) < 20:
            return None
        tr = []
        for i in range(len(kl) - 14, len(kl)):
            h = float(kl[i][2])
            l = float(kl[i][3])
            pc = float(kl[i - 1][4])
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(tr) / len(tr)

    def trend(self, kl):
        if len(kl) < STRUCTURE_LOOKBACK:
            return "RANGE"
        highs = [float(x[2]) for x in kl[-STRUCTURE_LOOKBACK:]]
        lows = [float(x[3]) for x in kl[-STRUCTURE_LOOKBACK:]]
        close = float(kl[-1][4])
        if close > max(highs): return "BULL"
        if close < min(lows): return "BEAR"
        return "RANGE"

    def signal(self, kl):
        if len(kl) < STRUCTURE_LOOKBACK:
            return None
        highs = [float(x[2]) for x in kl[-STRUCTURE_LOOKBACK:]]
        lows = [float(x[3]) for x in kl[-STRUCTURE_LOOKBACK:]]
        close = float(kl[-1][4])
        if close > max(highs): return "BUY"
        if close < min(lows): return "SELL"
        return None

    # ---------- EXECUTION ----------

    def set_leverage(self, s):
        bybit_private("POST", "/v5/position/set-leverage", {
            "category": "linear",
            "symbol": f"{s}USDT",
            "buyLeverage": str(LEVERAGE),
            "sellLeverage": str(LEVERAGE)
        })

    def market(self, s, side, qty):
        bybit_private("POST", "/v5/order/create", {
            "category": "linear",
            "symbol": f"{s}USDT",
            "side": "Buy" if side == "BUY" else "Sell",
            "orderType": "Market",
            "qty": str(qty),
            "positionIdx": 0
        })

    def limit_reduce(self, s, side, qty, price):
        bybit_private("POST", "/v5/order/create", {
            "category": "linear",
            "symbol": f"{s}USDT",
            "side": "Sell" if side == "BUY" else "Buy",
            "orderType": "Limit",
            "qty": str(round(qty, 3)),
            "price": str(round(price, 4)),
            "reduceOnly": True,
            "timeInForce": "GTC",
            "positionIdx": 0
        })

    def set_sl(self, s, price):
        bybit_private("POST", "/v5/position/trading-stop", {
            "category": "linear",
            "symbol": f"{s}USDT",
            "stopLoss": str(round(price, 4)),
            "slTriggerBy": "LastPrice",
            "positionIdx": 0
        })

    # ---------- LOOP ----------

    def run(self):
        print("[START] Bot running", flush=True)

        while True:
            try:
                # Clean finished trades
                for s in list(self.active):
                    if not self.position_open(s):
                        self.active.remove(s)

                self.send("💓 Bot heartbeat OK")

                batch_count = max(1, len(self.symbols) // SYMBOL_BATCH_SIZE)
                idx = int(time.time() / 300) % batch_count
                batch = self.symbols[idx * SYMBOL_BATCH_SIZE:(idx + 1) * SYMBOL_BATCH_SIZE]

                for s in batch:
                    if s in self.active:
                        continue

                    ltf = self.klines(s, LTF_INTERVAL)
                    h1 = self.klines(s, HTF_1H)
                    h4 = self.klines(s, HTF_4H)

                    if len(ltf) < 50 or len(h1) < 50 or len(h4) < 50:
                        continue

                    if self.funding(s) > MAX_FUNDING_RATE:
                        continue

                    sig = self.signal(ltf)
                    if not sig:
                        continue

                    atr = self.atr(ltf)
                    if not atr:
                        continue

                    price = float(ltf[-1][4])
                    qty = max(round((RISK_USDT_PER_TRADE * LEVERAGE) / price, 3), 0.01)

                    self.set_leverage(s)
                    self.market(s, sig, qty)
                    time.sleep(1)

                    sl = price - atr * ATR_MULTIPLIER if sig == "BUY" else price + atr * ATR_MULTIPLIER
                    tp1 = price + atr * TP1_R if sig == "BUY" else price - atr * TP1_R
                    tp2 = price + atr * TP2_R if sig == "BUY" else price - atr * TP2_R
                    tp3 = price + atr * TP3_R if sig == "BUY" else price - atr * TP3_R

                    self.set_sl(s, sl)
                    self.limit_reduce(s, sig, qty * 0.3, tp1)
                    self.limit_reduce(s, sig, qty * 0.3, tp2)
                    self.limit_reduce(s, sig, qty * 0.4, tp3)

                    self.active.add(s)

                    self.send(
                        f"🔥 LIVE TRADE {sig} {s}USDT\n"
                        f"Entry: {price:.4f}\n"
                        f"TP1: {tp1:.4f}\nTP2: {tp2:.4f}\nTP3: {tp3:.4f}\nSL: {sl:.4f}"
                    )

            except Exception as e:
                print("🔥 LOOP ERROR:", e, flush=True)
                self.send(f"❌ BOT ERROR: {e}")
                time.sleep(10)

            time.sleep(SCAN_INTERVAL_SECONDS)

# ================= START =================

if __name__ == "__main__":
    SmartMoneyBot().run()
