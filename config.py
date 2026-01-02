import os
# ================= TELEGRAM =================
TELEGRAM_BOT_TOKEN = os.getenv("8571517277:AAFSulUpC4NIuxZFRrpLHSi9KvGkONFN4SU")
TELEGRAM_CHAT_ID  = os.getenv("7951298168")
# ================= BYBIT ====================
BYBIT_BASE = "https://api.bybit.com"

# ================= SYMBOLS ==================
# 🔒 LOCKED TOP 200 USDT PERPETUALS
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
    "TIA","PYTH","SEI","JTO","ORDI","WIF","BONK","MEME","BOME",
    "PIXEL","STRK","AEVO","ENA","ETHFI","OMNI","ZRO","TON",
    "POL","NOT","BRETT","POPCAT","MEW","MYRO","SLERF","MOG",
    "TURBO","PEOPLE","GM","PORTAL","ALT","DYM","ONDO","TAO",
    "KAS","RNDR","FET","AGIX","OCEAN","NMR","ILV","SSV","TRB",
    "LOOM","ACE","ARKM","XAI","CYBER","C98","BAKE","BEL","LINA",
    "CTK","DAR","MDT","NKN","PERP","POND","RLC","SLP","STMX",
    "SUPER","SUSHI","TLM","UMA","XVS","YGG","ZRX"
]

# ================= TIMEFRAMES ===============
LTF_INTERVAL = "5"
HTF_1H = "60"
HTF_4H = "240"
KLINE_LIMIT = 200

# ================= RISK =====================
ATR_MULTIPLIER = 1.5
TRAIL_ATR_MULT = 1.0

TP1_RATIO = 1.0   # 30%
TP2_RATIO = 2.0   # 30%
TP3_RATIO = 3.0   # 40%

DEFAULT_LEVERAGE = 10
MAX_FUNDING_RATE = 0.02

# ================= LOGIC ====================
SCAN_INTERVAL_SECONDS = 30
STRUCTURE_LOOKBACK = 20
LIQUIDITY_LOOKBACK = 10
SYMBOL_LOCK_SECONDS = 900
MAX_TRADES = 5

# ================= BYBIT ====================
BYBIT_BASE = "https://api.bybit.com"

# ================= SYMBOLS ==================
TOP_100_SYMBOLS = [
    "BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","DOT","LINK",
    "MATIC","OP","ARB","ATOM","LTC","BCH","ETC","FIL","APT","NEAR",
    "SUI","ICP","INJ","AAVE","UNI","PEPE","TRX","EOS","XLM","NEO",
    "ALGO","FTM","GALA","DYDX","SNX","RUNE","KAVA","CAKE","COMP","CRV",
    "MASK","LDO","GMX","1000SHIB","WOO","ENS","YFI","IMX","ZEC","MINA",
    "RNDR","BLUR","CFX","STX","KLAY","FLOW","SAND","MANA","CHZ","OCEAN",
    "ANKR","QTUM","BAT","COTI","IOTA","CELR","ROSE","WAVES","KNC",
    "BAND","FLUX","API3","STORJ","ONE","RVN","HOT","ICX","DASH","ZEN"
]

# ================= TIMEFRAMES ===============
LTF_INTERVAL = "5"      # entries
HTF_1H = "60"
HTF_4H = "240"
KLINE_LIMIT = 200

# ================= RISK =====================
ACCOUNT_RISK_PCT = 1.0     # % risk per trade
DEFAULT_LEVERAGE = 10

ATR_MULTIPLIER = 1.5
TRAIL_ATR_MULT = 1.0

TP1_RATIO = 1.0   # 30%
TP2_RATIO = 2.0   # 30%
TP3_RATIO = 3.0   # 40%

# ================= LOGIC ====================
SCAN_INTERVAL_SECONDS = 60
STRUCTURE_LOOKBACK = 20
LIQUIDITY_LOOKBACK = 10
SYMBOL_LOCK_SECONDS = 600
MAX_TRADES = 3

# ================= FUNDING ==================
MAX_FUNDING_RATE = 0.02   # 0.02% (skip extreme bias)



