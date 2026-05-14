import os
from dotenv import load_dotenv

load_dotenv()

# ─── Bot Settings ───────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")          # Set in .env file
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))       # Your Telegram user ID (optional)

# ─── Search Settings ────────────────────────────────────────────
JOBS_PER_PAGE = 1                                 # Show 1 job at a time (swipe style)
DEFAULT_CITY = "Астана"                           # Default search city
MAX_PAGES = 3                                     # Pages to parse from hh.kz per search
MAX_DESCRIPTION_LENGTH = 400                      # Chars to show in preview

# ─── Database ───────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "jobs_bot.db")

# ─── Limits ─────────────────────────────────────────────────────
MAX_RESUME_SIZE_MB = 5
MAX_SAVED_JOBS = 100
MAX_RESUMES_PER_USER = 5
