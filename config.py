from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
# Project root (wherever this file lives)
ROOT = Path(__file__).parent
DB_PATH = ROOT/ "data" / "world_cup.db"

# Scraping
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
FBREF_BASE_URL = "https://fbref.com/en"
REQUEST_DELAY = 1.0 # free tier: 10 calls/min

# Model
RANDOM_SEED = 42
TEST_SIZE = 0.2