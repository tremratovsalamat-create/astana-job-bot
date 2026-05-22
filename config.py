import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

JOBS_PER_PAGE = 1
DEFAULT_CITY = "Астана"
MAX_PAGES = 3
MAX_DESCRIPTION_LENGTH = 400

DB_PATH = os.getenv("DB_PATH", "jobs_bot.db")

MAX_RESUME_SIZE_MB = 5
MAX_SAVED_JOBS = 100
MAX_RESUMES_PER_USER = 5
