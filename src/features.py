import sqlite3
from src.db import get_connection

def rolling_form(team_id: int, before_date: str, n: int = 5) -> dict:
    """
    Return the stats for team with team_id, of the last n games played before before_date
    
    Return format: {wins, draws, losses, points, form_score}"""
    conn = get_connection()

    ## SQL query to get the last n matches
    matches = conn.execute(
        """
            SELECT m.home_team_id, m.away_team_id, m.home_goals, m.away_goals, m.result
            FROM matches m
            WHERE (home_team_id = ? OR away_team_id = ?)
            AND date < ?
            ORDER BY date DESC
            LIMIT ?
        """,
        (team_id, team_id, before_date, n)
    ).fetchall()

    ## loop to figure out number of wins, losses
    team_info = {"wins": 0,
                 "draws": 0,
                 "losses": 0,
                 "points": 0,
                 "goals_for": 0,
                 "goals_against": 0,
                 "goal_difference": 0,
                 "form_score": 0}
    
    for match in matches:
        # gather the result
        
        # result is home_win, team is home -> win
        # result is home_win, team is away -> loss
        # result is away_win, team is away -> win
        # result is away_win, team is home -> loss
        is_home = match["home_team_id"] == team_id
        home_won = match["result"] == "home_win"

        if match["result"] == "draw":
            team_info["draws"] += 1
            team_info["points"] += 1
        elif is_home == home_won:
            # win
            team_info["wins"] += 1
            team_info["points"] += 3
        else:
            # loss
            team_info["losses"] += 1

        if is_home:
            goals_for = match["home_goals"]
            goals_against = match["away_goals"]
        else:
            goals_for = match["away_goals"]
            goals_against = match["home_goals"]

        team_info["goals_for"] += goals_for
        team_info["goals_against"] += goals_against

    wins = team_info["wins"]
    draws = team_info["draws"]

    games_played = len(matches)
    if games_played == 0:
        return {"wins": 0, "draws": 0, "losses": 0, "points": 0,
                "goals_for": 0, "goals_against": 0, "goal_difference": 0, "form_score": 0.0}
    
    team_info["form_score"] = round((wins * 3 + draws * 1) / (games_played*3), 2)
    team_info["goal_difference"] = team_info["goals_for"] - team_info["goals_against"]

    return team_info

def elo_rating(team_rating: float, opponent_rating: float, actual: float, k:int = 32) -> float:
    """Given team and opponent current ratings, team's old rating, and actual score, compute team's new elo rating"""
    
    expected = 1 / (1 + 10**((opponent_rating - team_rating)/400))
    new_rating = team_rating + k * (actual - expected)

    return new_rating


def compute_elo_ratings(k:int = 32,  initial: float = 1500.0) -> dict:
    """
    Process all matches in chronological order and return
    a dictionary of {team_id: current_elo} after all matches"""

    conn = get_connection()

    ratings = {} # running elos
    snapshots = {} # teams' ratings before the match was played / {match_id : {home_elo: float, away_elo: float}}
    
    # gather all matches 
    matches = conn.execute("""
                SELECT match_id, home_team_id, away_team_id, result
                FROM matches
                ORDER BY date
                """).fetchall()
    
    for match in matches:
        home_team_id = match["home_team_id"]
        away_team_id = match["away_team_id"]
        result = match["result"]
        match_id = match["match_id"]

        # elos going into a match
        home_elo = ratings.get(home_team_id, 1500.0)
        away_elo = ratings.get(away_team_id, 1500.0)

        snapshots[match_id] = {"home_elo": home_elo, 
                               "away_elo": away_elo}
        
        if result == "draw": #draw
            home_actual = 0.5
            away_actual = 0.5
        elif result == "home_win":
            home_actual = 1
            away_actual = 0
        else:
            home_actual = 0
            away_actual = 1

        # compute new elo ratings

        new_home_elo = elo_rating(home_elo, away_elo, home_actual, k)

        new_away_elo = elo_rating(away_elo, home_elo, away_actual, k)

        ratings[home_team_id] = new_home_elo
        ratings[away_team_id] = new_away_elo

    return snapshots, ratings


## temp test
if __name__ == "__main__":
    # Argentina is team_id 5
    result = rolling_form(5, "2022-11-20", n = 5)
    print(result)

    snapshots, ratings = compute_elo_ratings()

    #top 10 teams by current Elo
    conn = get_connection()
    top = sorted(ratings.items(), key=lambda x:x[1], reverse=True)[:10]

    for team_id, elo in top:
        row = conn.execute("SELECT name FROM teams WHERE team_id = ?", (team_id,)).fetchone()
        if row is None: 
            continue
        print(f"{row["name"]}: {round(elo,1)}")