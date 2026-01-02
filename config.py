import os

# ================= TELEGRAM =================
TELEGRAM_BOT_TOKEN = os.getenv("8571517277:AAFSulUpC4NIuxZFRrpLHSi9KvGkONFN4SU")
TELEGRAM_CHAT_ID  = os.getenv("7951298168")

# ================= BYBIT ====================
BYBIT_BASE = "https://api.bybit.com"

# ================= SCANNER ==================
TOP_N_COINS = 150
MIN_VOLUME_USDT = 10_000_000

KLINE_INTERVAL = "5"     # 5-minute candles
KLINE_LIMIT = 120

SCAN_INTERVAL_SECONDS = 60
MIN_HOLD_SECONDS = 60

# ================= SMART MONEY ==============
STRUCTURE_LOOKBACK = 20
LIQUIDITY_LOOKBACK = 10

ATR_MULTIPLIER = 1.5
MAX_TRADES = 5
