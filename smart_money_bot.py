import requests, time, json, os
from datetime import datetime
from config import *

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# ================= UTIL =================

def load_json(p):
    try:
        return json.load(open(p)) if os.path.exists(p) else {}
    except:
        return {}

def save_json(p, d):
    json.dump(d, open(p, "w"), indent=2)

# ================= BOT =================

class SmartMoneyBot:

    def __init__(self):
        self.trades = load_json("trades.json")
        self.symbols = TOP_200_SYMBOLS
        print(f"[INIT] Symbols locked: {len(self.symbols)}", flush=True)

    # ================= SAFE API =================

    def get(self, url, params=None):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=8)
            return r.json() if r.status_code == 200 else None
        except:
            return None

    def klines(self, s, tf):
        d = self.get(f"{BYBIT_BASE}/v5/market/kline", {
            "category": "linear", "symbol": f"{s}USDT",
            "interval": tf, "limit": KLINE_LIMIT
        })
        return d["result"]["list"] if d and "result" in d else []

    def price(self, s):
        d = self.get(f"{BYBIT_BASE}/v5/market/tickers", {
            "category": "linear", "symbol": f"{s}USDT"
        })
        try:
            return float(d["result"]["list"][0]["lastPrice"])
        except:
            return None

    def funding(self, s):
        d = self.get(f"{BYBIT_BASE}/v5/market/funding/history", {
            "category": "linear", "symbol": f"{s}USDT", "limit": 1
        })
        try:
            return abs(float(d["result"]["list"][0]["fundingRate"]))
        except:
            return 0.0

    # ================= INDICATORS =================

    def atr(self, kl):
        try:
            tr = []
            for i in range(1, 15):
                h, l, pc = float(kl[i][2]), float(kl[i][3]), float(kl[i-1][4])
                tr.append(max(h-l, abs(h-pc), abs(l-pc)))
            return sum(tr)/len(tr)
        except:
            return None

    def trend(self, kl):
        try:
            h = [float(x[2]) for x in kl[-STRUCTURE_LOOKBACK:]]
            l = [float(x[3]) for x in kl[-STRUCTURE_LOOKBACK:]]
            c = float(kl[-1][4])
            if c > max(h): return "BULL"
            if c < min(l): return "BEAR"
            return "RANGE"
        except:
            return "RANGE"

    def bos(self, kl):
        try:
            h = [float(x[2]) for x in kl[-STRUCTURE_LOOKBACK:]]
            l = [float(x[3]) for x in kl[-STRUCTURE_LOOKBACK:]]
            c = float(kl[-1][4])
            if c > max(h): return "BUY"
            if c < min(l): return "SELL"
        except:
            pass
        return None

    def sweep(self, kl):
        try:
            h = [float(x[2]) for x in kl[-LIQUIDITY_LOOKBACK:]]
            l = [float(x[3]) for x in kl[-LIQUIDITY_LOOKBACK:]]
            c = float(kl[-1][4])
            if float(kl[-1][2]) > max(h[:-1]) and c < max(h[:-1]): return "SELL"
            if float(kl[-1][3]) < min(l[:-1]) and c > min(l[:-1]): return "BUY"
        except:
            pass
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

    # ================= MANAGER =================

    def manage_trades(self):
        for s in list(self.trades):
            t = self.trades[s]
            price = self.price(s)
            if price is None:
                continue

            # trailing SL
            if t["side"] == "BUY":
                t["sl"] = max(t["sl"], price - t["atr"] * TRAIL_ATR_MULT)
            else:
                t["sl"] = min(t["sl"], price + t["atr"] * TRAIL_ATR_MULT)

            # SL
            if (t["side"]=="BUY" and price<=t["sl"]) or (t["side"]=="SELL" and price>=t["sl"]):
                self.send(f"❌ SL HIT {s} @ {price:.4f}")
                del self.trades[s]
                continue

            # TP
            for tp in ["tp1","tp2","tp3"]:
                if not t["hit"][tp]:
                    level = t[tp]
                    if (t["side"]=="BUY" and price>=level) or (t["side"]=="SELL" and price<=level):
                        t["hit"][tp] = True
                        self.send(f"✅ {tp.upper()} HIT {s} @ {price:.4f}")
                        if tp=="tp3":
                            del self.trades[s]
                            break

        save_json("trades.json", self.trades)

    # ================= LOOP =================

    def run(self):
        print(f"[START] Bot live {datetime.now()}", flush=True)

        while True:
            try:
                print(f"[HEARTBEAT] {datetime.now()} | Trades={len(self.trades)}", flush=True)

                self.manage_trades()

                idx = int(time.time()/300) % (len(self.symbols)//SYMBOL_BATCH_SIZE)
                batch = self.symbols[idx*SYMBOL_BATCH_SIZE:(idx+1)*SYMBOL_BATCH_SIZE]

                for s in batch:
                    if s in self.trades:
                        continue

                    ltf = self.klines(s, LTF_INTERVAL)
                    h1  = self.klines(s, HTF_1H)
                    h4  = self.klines(s, HTF_4H)

                    if len(ltf)<50 or len(h1)<50 or len(h4)<50:
                        continue

                    t1, t4 = self.trend(h1), self.trend(h4)
                    if t1=="RANGE" and t4=="RANGE":
                        continue

                    sig = self.bos(ltf) or self.sweep(ltf)
                    if not sig:
                        continue

                    if sig=="BUY" and t1=="BEAR": continue
                    if sig=="SELL" and t1=="BULL": continue

                    if self.funding(s) > MAX_FUNDING_RATE:
                        continue

                    atr = self.atr(ltf)
                    if atr is None:
                        continue

                    price = float(ltf[-1][4])

                    self.trades[s] = {
                        "side": sig,
                        "atr": atr,
                        "sl": price - atr*ATR_MULTIPLIER if sig=="BUY" else price + atr*ATR_MULTIPLIER,
                        "tp1": price + atr*TP1_R if sig=="BUY" else price - atr*TP1_R,
                        "tp2": price + atr*TP2_R if sig=="BUY" else price - atr*TP2_R,
                        "tp3": price + atr*TP3_R if sig=="BUY" else price - atr*TP3_R,
                        "hit": {"tp1":False,"tp2":False,"tp3":False}
                    }

                    save_json("trades.json", self.trades)

                    self.send(
                        f"🚀 {sig} {s}USDT\n"
                        f"Entry: {price:.4f}\n"
                        f"TP1: {self.trades[s]['tp1']:.4f}\n"
                        f"TP2: {self.trades[s]['tp2']:.4f}\n"
                        f"TP3: {self.trades[s]['tp3']:.4f}\n"
                        f"SL: {self.trades[s]['sl']:.4f}"
                    )

            except Exception as e:
                print("🔥 LOOP ERROR:", e, flush=True)
                time.sleep(10)

            time.sleep(SCAN_INTERVAL_SECONDS)

# ================= START =================

if __name__ == "__main__":
    SmartMoneyBot().run()
