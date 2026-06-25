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

def compute_elo_ratings(k:int = 32,  initial: float = 15000.0) -> dict:
    """
    Process all matches in chronological order and return
    a dictionary of {team_id: current_elo} after all matches"""
    

## temp test
if __name__ == "__main__":
    # Argentina is team_id 5
    result = rolling_form(5, "2022-11-20", n = 5)
    print(result)