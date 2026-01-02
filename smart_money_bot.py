import requests, time, json, os
from datetime import datetime
from config import *

HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"application/json"}

# ================= UTIL =================

def load_json(p):
    if os.path.exists(p):
        try: return json.load(open(p))
        except: return {}
    return {}

def save_json(p,d):
    json.dump(d,open(p,"w"),indent=2)

# ================= BOT =================

class SmartMoneyBot:

    def __init__(self):
        self.trades = load_json("trades.json")
        self.symbols = TOP_200_SYMBOLS
        print(f"[INIT] Locked symbols: {len(self.symbols)}")

    # ================= BYBIT =================

    def klines(self,symbol,interval):
        r=requests.get(
            f"{BYBIT_BASE}/v5/market/kline",
            params={"category":"linear","symbol":f"{symbol}USDT","interval":interval,"limit":KLINE_LIMIT},
            headers=HEADERS,timeout=10
        )
        return r.json().get("result",{}).get("list",[]) if r.status_code==200 else []

    def price(self,symbol):
        r=requests.get(
            f"{BYBIT_BASE}/v5/market/tickers",
            params={"category":"linear","symbol":f"{symbol}USDT"},
            headers=HEADERS,timeout=5
        )
        if r.status_code!=200: return None
        return float(r.json()["result"]["list"][0]["lastPrice"])

    def funding(self,symbol):
        r=requests.get(
            f"{BYBIT_BASE}/v5/market/funding/history",
            params={"category":"linear","symbol":f"{symbol}USDT","limit":1},
            headers=HEADERS,timeout=5
        )
        if r.status_code!=200: return 0
        return float(r.json()["result"]["list"][0]["fundingRate"])

    # ================= INDICATORS =================

    def atr(self,kl):
        tr=[]
        for i in range(1,15):
            h,l,pc=float(kl[i][2]),float(kl[i][3]),float(kl[i-1][4])
            tr.append(max(h-l,abs(h-pc),abs(l-pc)))
        return sum(tr)/len(tr)

    def trend(self,kl):
        h=[float(x[2]) for x in kl]
        l=[float(x[3]) for x in kl]
        c=float(kl[-1][4])
        if c>max(h[-STRUCTURE_LOOKBACK:]): return "BULL"
        if c<min(l[-STRUCTURE_LOOKBACK:]): return "BEAR"
        return "RANGE"

    def bos(self,kl):
        h=[float(x[2]) for x in kl]
        l=[float(x[3]) for x in kl]
        c=float(kl[-1][4])
        if c>max(h[-STRUCTURE_LOOKBACK:]): return "BUY"
        if c<min(l[-STRUCTURE_LOOKBACK:]): return "SELL"
        return None

    def sweep(self,kl):
        h=[float(x[2]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        l=[float(x[3]) for x in kl[-LIQUIDITY_LOOKBACK:]]
        c=float(kl[-1][4])
        if float(kl[-1][2])>max(h[:-1]) and c<max(h[:-1]): return "SELL"
        if float(kl[-1][3])<min(l[:-1]) and c>min(l[:-1]): return "BUY"
        return None

    # ================= TELEGRAM =================

    def send(self,msg):
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id":TELEGRAM_CHAT_ID,"text":msg},
            timeout=5
        )

    # ================= TRADE MONITOR =================

    def manage_trades(self):
        for s,t in list(self.trades.items()):
            price=self.price(s)
            if price is None: continue

            side=t["side"]

            # trailing SL
            if side=="BUY":
                new_trail=price-t["atr"]*TRAIL_ATR_MULT
                if new_trail>t["trail"]:
                    t["trail"]=new_trail
            else:
                new_trail=price+t["atr"]*TRAIL_ATR_MULT
                if new_trail<t["trail"]:
                    t["trail"]=new_trail

            # SL hit
            if (side=="BUY" and price<=t["trail"]) or (side=="SELL" and price>=t["trail"]):
                self.send(f"❌ SL HIT {s}USDT @ {price:.4f}")
                del self.trades[s]
                continue

            # TP hits
            for tp in ["tp1","tp2","tp3"]:
                if not t["hit"][tp]:
                    level=t[tp]
                    if (side=="BUY" and price>=level) or (side=="SELL" and price<=level):
                        t["hit"][tp]=True
                        pct={"tp1":"30%","tp2":"30%","tp3":"40%"}[tp]
                        self.send(f"✅ {pct} TP HIT {s}USDT @ {price:.4f}")

                        if tp=="tp3":
                            del self.trades[s]
                            break

        save_json("trades.json",self.trades)

    # ================= LOOP =================

    def run(self):
        print(f"[{datetime.now()}] 🚀 Futures Bot Running")

        while True:
            try:
                self.manage_trades()

                for s in self.symbols:
                    if s in self.trades and time.time()-self.trades[s]["time"]<SYMBOL_LOCK_SECONDS:
                        continue

                    ltf=self.klines(s,LTF_INTERVAL)
                    h1 =self.klines(s,HTF_1H)
                    h4 =self.klines(s,HTF_4H)
                    if len(ltf)<50 or len(h1)<50 or len(h4)<50:
                        continue

                    t1,t4=self.trend(h1),self.trend(h4)
                    if t1=="RANGE" and t4=="RANGE":
                        continue

                    signal=self.bos(ltf) or self.sweep(ltf)
                    if not signal: continue
                    if signal=="BUY" and t1=="BEAR": continue
                    if signal=="SELL" and t1=="BULL": continue

                    fund=self.funding(s)
                    if abs(fund)>MAX_FUNDING_RATE:
                        continue

                    atr=self.atr(ltf)
                    price=float(ltf[-1][4])

                    tp1=price+atr*TP1_RATIO if signal=="BUY" else price-atr*TP1_RATIO
                    tp2=price+atr*TP2_RATIO if signal=="BUY" else price-atr*TP2_RATIO
                    tp3=price+atr*TP3_RATIO if signal=="BUY" else price-atr*TP3_RATIO
                    trail=price-atr*ATR_MULTIPLIER if signal=="BUY" else price+atr*ATR_MULTIPLIER

                    self.trades[s]={
                        "time":time.time(),
                        "side":signal,
                        "atr":atr,
                        "trail":trail,
                        "tp1":tp1,
                        "tp2":tp2,
                        "tp3":tp3,
                        "hit":{"tp1":False,"tp2":False,"tp3":False}
                    }
                    save_json("trades.json",self.trades)

                    self.send(
                        f"🚀 {signal} {s}USDT (Futures)\n"
                        f"HTF: 1H={t1} 4H={t4}\n"
                        f"Funding: {fund:.4%}\n"
                        f"Entry: {price:.4f}\n"
                        f"TP1 30%: {tp1:.4f}\n"
                        f"TP2 30%: {tp2:.4f}\n"
                        f"TP3 40%: {tp3:.4f}\n"
                        f"Initial SL: {trail:.4f}\n"
                        f"Trailing SL active\n"
                        f"Leverage: {DEFAULT_LEVERAGE}x"
                    )

            except Exception as e:
                print("Runtime error:",e)

            time.sleep(SCAN_INTERVAL_SECONDS)

# ================= START =================

if __name__=="__main__":
    SmartMoneyBot().run()
