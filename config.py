from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

# Project root (wherever this file lives)
ROOT = Path(__file__).parent

# Database
DB_PATH = ROOT/ "data" / "world_cup.db"

# Scraping
FBREF_BASE_URL = "https://fbref.com/en"
REQUEST_DELAY = 2.0 #seconds between requests, to be polite

# Model
RANDOM_SEED = 42
TEST_SIZE = 0.2