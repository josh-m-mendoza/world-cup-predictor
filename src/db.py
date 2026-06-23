import sqlite3
from pathlib import Path
from config import DB_PATH

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id     INTEGER PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                country     TEXT,
                federation  TEXT
            );
                           
            CREATE TABLE IF NOT EXISTS tournaments (
                tournament_id   INTEGER PRIMARY kEY,
                name            TEXT NOT NULL,
                year            INTEGER,
                host_country    TEXT,
                stage           TEXT
            );
            
            CREATE TABLE IF NOT EXISTS matches (
                match_id        INTEGER PRIMARY KEY,
                tournament_id   INTGER REFERENCES tournaments(tournament_id),
                date            TEXT NOT NULL,
                home_team_id    INTEGER REFERENCES teams(team_id),
                away_team_id    INTEGER REFERENCES teams(team_id),
                home_goals      INTEGER,
                away_goals      INTEGER,
                result          TEXT,
                stage           TEXT,
                venue           TEXT
            );
                           
            CREATE TABLE IF NOT EXISTS match_stats (
                stat_id         INTEGER PRIMARY KEY,
                match_id        INTGER REFERENCES matches(match_id),
                team_id         INTEGER REFERENCES teams(team_id),
                possession      REAL,
                shots           INTEGER,
                shots_on_target INTEGER,
                xg              REAL,
                passes          INTEGER,
                pass_accuracy   REAL,
                yellow_cards    INTEGER,
                red_cards       INTEGER
            );
        """)
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()