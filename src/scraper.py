import requests
import sqlite3
import time
from config import FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE_URL, REQUEST_DELAY, DB_PATH
from src.db import get_connection

HEADERS = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

def fetch(endpoint: str) -> dict:
    """Make a single GET requed to the football-data.org API"""
    url = f"{FOOTBALL_DATA_BASE_URL}/{endpoint}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status() # throws if 4xx / 5xx
    time.sleep(REQUEST_DELAY)
    return response.json()
     

def insert_team(conn: sqlite3.Connection, team: dict) -> int:
    """Insert a team if it doesn't exist, return it's team_id"""
    conn.execute("""
        INSERT OR IGNORE INTO teams (team_id, name, country)
        VALUES (:id, :name, :shortName)
    """,team)
    return team["id"]

def insert_match(conn: sqlite3.Connection, match: dict, tournament_id: int):
    """Parse a match dict from the API and insert into matches table"""
    home = match["homeTeam"]
    away = match["awayTeam"]
    score = match["score"]["fullTime"]

    home_goals = score["home"]
    away_goals = score["away"]

    if home_goals is None or away_goals is None:
        result = None # match not yet plyaed
    elif home_goals > away_goals:
        result = "home_win"
    elif away_goals > home_goals:
        result = "away_win"
    else:
        result = "draw"
    
    insert_team(conn, home)
    insert_team(conn, away)

    conn.execute("""
        INSERT OR IGNORE INTO matches
            (match_id, tournament_id, date, home_team_id, away_team_id,
                 home_goals, away_goals, result, stage, venue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,(match["id"],
        tournament_id,
        match["utcDate"][:10],
        home["id"],
        away["id"],
        home_goals,
        away_goals, 
        result, 
        match.get("stage"),
        match.get("venue"),))

def scrape_competition(competition_code:str):
    """Scrape all matches for a competition and store them in the DB.
    competition_code examples: WC (World Cup), EC (Euros), PL (Premier League)"""

    print(f"Fetching competition: {competition_code}")
    data = fetch(f"competitions/{competition_code}/matches")

    competition = data["competition"]
    tournament_id = competition["id"]

    conn = get_connection()
    with conn:
        # insert the tournament
        conn.execute("""
            INSERT OR IGNORE INTO tournaments (tournament_id, name, year)
            VALUES (?, ?, ?)
        """, (
            tournament_id, 
            competition["name"], 
            competition.get("currentSeason", {}).get("startDate", "")[:4],
        ))

        matches = data["matches"]
        print(f"Found {len(matches)} matches - inserting...")

        for match in matches:
            insert_match(conn, match, tournament_id)

    print(f"Done. {len(matches)} matches stored in {DB_PATH}")

if __name__ == "__main__":
    scrape_competition("WC")