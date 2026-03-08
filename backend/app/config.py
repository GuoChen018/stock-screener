import os
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
SCAN_HOUR = int(os.getenv("SCAN_HOUR", "16"))
SCAN_MINUTE = int(os.getenv("SCAN_MINUTE", "30"))
MIN_MARKET_CAP = int(os.getenv("MIN_MARKET_CAP", "500000000"))
MIN_AVG_VOLUME = int(os.getenv("MIN_AVG_VOLUME", "100000"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stock_screener.db")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")
