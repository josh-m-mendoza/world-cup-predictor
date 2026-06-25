import requests
import sqlite3
import time
from config import FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE_URL, REQUEST_DELAY, DB_PATH
from src.db import get_connection
# for the past world cup games
import csv

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

    existing = conn.execute(
        "SELECT team_id FROM teams WHERE name = ?", (team["name"],)
    ).fetchone()

    if existing: return existing["team_id"]

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
    
    home_id = insert_team(conn, home)
    away_id = insert_team(conn, away)

    conn.execute("""
        INSERT OR IGNORE INTO matches
            (match_id, tournament_id, date, home_team_id, away_team_id,
                 home_goals, away_goals, result, stage, venue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,(match["id"],
        tournament_id,
        match["utcDate"][:10],
        home_id,
        away_id,
        home_goals,
        away_goals, 
        result, 
        match.get("stage"),
        match.get("venue"),))

def scrape_competition(competition_code:str, year: int = None):
    """Scrape all matches for a competition and store them in the DB.
    competition_code examples: WC (World Cup), EC (Euros), PL (Premier League)"""

    print(f"Fetching competition: {competition_code}")
    data = fetch(f"competitions/{competition_code}/matches")

    competition = data["competition"]
    tournament_id = competition["id"]
    
    year_str = competition.get("currentSeason",{}).get("startDate", "")[:4]
    resolved_year = year or (int(year_str) if year_str else None)

    conn = get_connection()
    with conn:
        # insert the tournament
        existing = conn.execute("""
            SELECT tournament_id FROM tournaments
            WHERE name = ? AND year = ?
        """, (competition["name"], resolved_year)).fetchone()
        if existing:
            tournament_id = existing["tournament_id"]
        else:
            conn.execute("""
                INSERT INTO tournaments (tournament_id, name, year)
                VALUES (?, ?, ?)
                ON CONFLICT(tournament_id) DO UPDATE SET year = excluded.year
            """, (
                tournament_id, 
                competition["name"], 
                resolved_year,
            ))

        matches = data["matches"]
        print(f"Found {len(matches)} matches - inserting...")

        for match in matches:
            insert_match(conn, match, tournament_id)

    print(f"Done. {len(matches)} matches stored in {DB_PATH}")

def get_or_create_tournament(conn, name: str, year:int) -> int:
    """Look up a tournament by name+year, insert if missing, return its id."""
    row = conn.execute("""
        SELECT tournament_id FROM tournaments
        WHERE name = ? AND year = ?
    """, (name,year)).fetchone()
    
    if row: return row["tournament_id"]
    
    cursor = conn.execute("""
        INSERT INTO tournaments (name, year) VALUES (?, ?)
    """, (name, year))
    return cursor.lastrowid

def get_world_cup_year(match_date: str, tournament_name: str) -> int:
    """ Derive the World Cup tournament year from a match date.
        World Cups: 2010, 2014, 2018, 2022, 2026... """
    
    world_cup_years = [2010, 2014, 2018, 2022, 2026]
    match_year = int(match_date[:4])

    # find nearest WC year at or before match year
    current_wc = world_cup_years[0]
    for wc_year in world_cup_years:
        if match_year >= wc_year:
            current_wc = wc_year

    if "qualification" in tournament_name.lower():
        idx = world_cup_years.index(current_wc)
        if idx + 1 < len(world_cup_years):
            return world_cup_years[idx + 1]
        
    return current_wc

def load_historical_csv(filepath: str, from_year: int = 2010, to_year: int = None, elo_seed_only: bool = False):
    """
    Load internation results fromo CSV into the DB
    filters to matches from from_year onwards by default"""

    conn = get_connection()
    inserted = 0
    skipped = 0

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        with conn:
            for row in reader:
                year = int(row["date"][:4])
                if year < from_year:
                    continue

                if to_year and year >= to_year:
                    continue

                # only keep World Cup matches for now
                if "FIFA World Cup" not in row["tournament"]:
                    continue
                wc_year = get_world_cup_year(row["date"], row["tournament"])
                if wc_year == 2026:
                    continue

                home_name = row["home_team"]
                away_name = row["away_team"]
                home_goals = row["home_score"]
                away_goals = row["away_score"]

                if home_goals == "NA" or away_goals == "NA":
                    continue
                else:
                    home_goals = int(home_goals)
                    away_goals = int(away_goals)
                
                if home_goals > away_goals:
                    result = "home_win"
                elif home_goals < away_goals:
                    result = "away_win"
                else: 
                    result = "draw"

                # don't have ids so insert teams by name lookup

                conn.execute("""
                    INSERT OR IGNORE INTO teams (name) VALUES (?)
                """, (home_name,))

                conn.execute("""
                    INSERT OR IGNORE INTO teams (name) VALUES (?)
                """, (away_name,))

                # lookup auto-assigned team IDs
                home_id = conn.execute("SELECT team_id FROM teams WHERE name = ?", (home_name,)).fetchone()["team_id"]

                away_id = conn.execute("SELECT team_id FROM teams WHERE name = ?", (away_name,)).fetchone()["team_id"]

                wc_year = get_world_cup_year(row["date"], row["tournament"])
                if elo_seed_only:
                    tournament_id = get_or_create_tournament(conn, "Elo Seed Data", wc_year)
                else:
                    tournament_id = get_or_create_tournament(conn, row["tournament"], wc_year)

                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO matches
                            (tournament_id, date, home_team_id, away_team_id,
                            home_goals, away_goals, result, stage, elo_seed_only)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)
                    """, (
                        tournament_id,
                        row["date"],
                        home_id,
                        away_id, 
                        home_goals,
                        away_goals,
                        result,
                        row["tournament"],
                        1 if elo_seed_only else 0,
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
        print(f"Done. {inserted} matches inserted, {skipped} skipped.")


if __name__ == "__main__":
    from src.db import init_db
    init_db()

    print("--- Loading Elo seed data (1990-2009) ---")
    load_historical_csv("data/raw/results.csv", from_year=1990, to_year=2010, elo_seed_only=True)

    print("--- Loading historical CSV ---")
    load_historical_csv("data/raw/results.csv", from_year=2010)

    print("---Scraping 2026 WC data from API ---")
    scrape_competition("WC", year = 2026)