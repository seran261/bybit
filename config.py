import os

# =============== TELEGRAM =================
TELEGRAM_BOT_TOKEN = os.getenv("8571517277:AAFSulUpC4NIuxZFRrpLHSi9KvGkONFN4SU")
TELEGRAM_CHAT_ID  = os.getenv("7951298168")

# =============== BYBIT ====================
BYBIT_BASE = "https://api.bybit.com"

# =============== SYMBOLS ==================
# 🔒 LOCKED TOP 100 USDT PERPETUALS
TOP_100_SYMBOLS = [
    "BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","DOT","LINK",
    "MATIC","OP","ARB","ATOM","LTC","BCH","ETC","FIL","APT","NEAR",
    "SUI","ICP","INJ","AAVE","UNI","PEPE","TRX","EOS","XLM","NEO",
    "ALGO","FTM","GALA","DYDX","SNX","RUNE","KAVA","CAKE","COMP","CRV",
    "MASK","LDO","GMX","1000SHIB","WOO","ENS","YFI","IMX","ZEC","MINA",
    "RNDR","BLUR","CFX","HOOK","STX","KLAY","LRC","FLOW","SAND","MANA",
    "CHZ","OCEAN","ANKR","QTUM","BAT","COTI","IOTA","CELR","ROSE",
    "HNT","WAVES","SKL","KNC","BAL","BAND","FLUX","API3","STORJ",
    "ONE","RVN","HOT","ICX","DASH","ZEN","ONT","AR"
]

# =============== TIMEFRAMES ===============
LTF_INTERVAL = "5"     # 5m entries
HTF_1H = "60"
HTF_4H = "240"
KLINE_LIMIT = 200

# =============== LOGIC ====================
SCAN_INTERVAL_SECONDS = 60
MIN_HOLD_SECONDS = 60

STRUCTURE_LOOKBACK = 20
LIQUIDITY_LOOKBACK = 10

ATR_MULTIPLIER = 1.5
MAX_TRADES = 3
