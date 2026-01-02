import os

# ================= TELEGRAM =================
TELEGRAM_BOT_TOKEN = os.getenv("8571517277:AAFSulUpC4NIuxZFRrpLHSi9KvGkONFN4SU")
TELEGRAM_CHAT_ID  = os.getenv("7951298168")

# ================= BYBIT ====================
BYBIT_BASE = os.getenv("BYBIT_BASE", "https://api.bybit.com")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# ================= SYMBOLS ==================
TOP_200_SYMBOLS = [
    "BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","DOT","LINK",
    "MATIC","OP","ARB","ATOM","LTC","BCH","ETC","FIL","APT","NEAR",
    "SUI","ICP","INJ","AAVE","UNI","PEPE","TRX","EOS","XLM","NEO",
    "ALGO","FTM","GALA","DYDX","SNX","RUNE","KAVA","CAKE","COMP","CRV",
    "MASK","LDO","GMX","1000SHIB","WOO","ENS","YFI","IMX","ZEC","MINA",
    "RNDR","BLUR","CFX","STX","KLAY","FLOW","SAND","MANA","CHZ","OCEAN",
    "ANKR","QTUM","BAT","COTI","IOTA","CELR","ROSE","WAVES","KNC",
    "BAND","FLUX","API3","STORJ","ONE","RVN","HOT","ICX","DASH","ZEN",
    "ONT","ZIL","AR","MTL","SKL","CTSI","SXP","RSR","REEF","CKB",
    "DENT","T","HIGH","GAL","ID","MAGIC","PHB","HOOK","RDNT",
    "TIA","PYTH","SEI","JTO","ORDI","WIF","BONK","MEME","BOME"
]

# ================= SCANNING =================
SYMBOL_BATCH_SIZE = 40
SCAN_INTERVAL_SECONDS = 45

# ================= TIMEFRAMES ===============
LTF_INTERVAL = "5"
HTF_1H = "60"
HTF_4H = "240"
KLINE_LIMIT = 150

# ================= RISK =====================
LEVERAGE = 10
RISK_USDT_PER_TRADE = 10

ATR_MULTIPLIER = 1.5
TRAIL_ATR_MULT = 1.0

TP1_R = 1.0
TP2_R = 2.0
TP3_R = 3.0

MAX_FUNDING_RATE = 0.02
STRUCTURE_LOOKBACK = 20
LIQUIDITY_LOOKBACK = 10
