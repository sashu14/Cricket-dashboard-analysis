"""
analytics.py — Pure analytical functions for IPL data.

All functions accept pandas DataFrames and return DataFrames or Series.
No Streamlit or Plotly imports — these are pure data-transformation utilities
that can be imported and tested independently.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Team name normalisation
# Maps historical franchise names / known typos to their current canonical
# form.  Defunct franchises with no successor (Deccan Chargers, Kochi Tuskers
# Kerala, Pune Warriors, Gujarat Lions) are intentionally kept as-is.
# ---------------------------------------------------------------------------
TEAM_ALIASES: dict[str, str] = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiant": "Rising Pune Supergiants",
}


def normalise_team_names(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Replace historical franchise aliases with current canonical names."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].replace(TEAM_ALIASES)
    return df


# ---------------------------------------------------------------------------
# Core analytics
# ---------------------------------------------------------------------------

def compute_win_rates(matches: pd.DataFrame) -> pd.Series:
    """Win-rate % per team, sorted descending. Excludes No Result/Draw/Tie."""
    if matches.empty or "winner" not in matches.columns:
        return pd.Series(dtype=float)
    valid = matches[~matches["winner"].isin(["No Result", "Draw", "Tie"])]
    win_counts = valid["winner"].value_counts()
    played = pd.concat([matches["team1"], matches["team2"]]).value_counts()
    return (win_counts / played * 100).dropna().sort_values(ascending=False)


def compute_toss_impact(matches: pd.DataFrame) -> pd.DataFrame:
    """Return [toss_decision, toss_match_winner, count] for sunburst chart."""
    required = {"toss_winner", "toss_decision", "winner"}
    if matches.empty or not required.issubset(matches.columns):
        return pd.DataFrame()
    df = matches.copy()
    df["toss_match_winner"] = (df["toss_winner"] == df["winner"]).map(
        {True: "Won Match", False: "Lost Match"}
    )
    return (
        df.dropna(subset=["toss_decision", "toss_match_winner"])
        .groupby(["toss_decision", "toss_match_winner"])
        .size()
        .reset_index(name="count")
    )


def compute_batsman_stats(deliveries: pd.DataFrame, min_balls: int = 50) -> pd.DataFrame:
    """Batsman totals + strike rate for players with >= min_balls faced."""
    if deliveries.empty or not {"batsman", "batsman_runs"}.issubset(deliveries.columns):
        return pd.DataFrame()
    stats = (
        deliveries.groupby("batsman")
        .agg(total_runs=("batsman_runs", "sum"), balls_faced=("batsman_runs", "count"))
        .reset_index()
    )
    stats = stats[stats["balls_faced"] > min_balls].copy()
    stats["strike_rate"] = (stats["total_runs"] / stats["balls_faced"] * 100).round(1)
    return stats


def compute_bowler_stats(deliveries: pd.DataFrame, min_balls: int = 60):
    """
    Bowler economy + wickets (or balls if wickets absent).
    Returns (DataFrame, y_col, y_label).
    """
    if deliveries.empty or "bowler" not in deliveries.columns:
        return pd.DataFrame(), "balls_bowled", "Balls Bowled"

    has_wickets = "is_wicket" in deliveries.columns
    agg = {"runs_conceded": ("total_runs", "sum"), "balls_bowled": ("total_runs", "count")}
    if has_wickets:
        agg["wickets"] = ("is_wicket", "sum")
    y_col = "wickets" if has_wickets else "balls_bowled"
    y_label = "Total Wickets" if has_wickets else "Balls Bowled (wickets data absent)"

    stats = deliveries.groupby("bowler").agg(**agg).reset_index()
    stats = stats[stats["balls_bowled"] > min_balls].copy()
    stats["overs"] = stats["balls_bowled"] / 6
    stats["economy"] = (stats["runs_conceded"] / stats["overs"]).round(2)
    return stats, y_col, y_label


def compute_venue_win_rates(matches: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """
    Win-rate % (bat-first vs field-first) for top N venues by match count.
    Returns DataFrame indexed by venue with columns:
        ['Bat First Win%', 'Field First Win%', 'Total Matches']
    Uses rates, not raw counts, for analytical correctness.
    """
    required = {"venue", "toss_winner", "toss_decision", "winner"}
    if matches.empty or not required.issubset(matches.columns):
        return pd.DataFrame()

    df = matches.copy()

    def bat_first_won(row):
        if pd.isna(row["winner"]) or row["winner"] in ["No Result", "Draw", "Tie"]:
            return None
        if row["toss_decision"] == "bat":
            return row["toss_winner"] == row["winner"]
        return row["toss_winner"] != row["winner"]

    df["bat_first_won"] = df.apply(bat_first_won, axis=1)
    df = df.dropna(subset=["bat_first_won"])

    grouped = df.groupby(["venue", "bat_first_won"]).size().unstack(fill_value=0)
    for col in [True, False]:
        if col not in grouped.columns:
            grouped[col] = 0

    grouped.rename(columns={True: "bat_wins", False: "field_wins"}, inplace=True)
    grouped["Total Matches"] = grouped["bat_wins"] + grouped["field_wins"]
    grouped = grouped.nlargest(top_n, "Total Matches")
    grouped["Bat First Win%"]   = (grouped["bat_wins"]   / grouped["Total Matches"] * 100).round(1)
    grouped["Field First Win%"] = (grouped["field_wins"] / grouped["Total Matches"] * 100).round(1)
    return grouped[["Bat First Win%", "Field First Win%", "Total Matches"]]


def compute_season_win_rates(matches: pd.DataFrame, win_rates: pd.Series, top_n: int = 5) -> pd.DataFrame:
    """Per-season win % for the top N overall teams."""
    if matches.empty or win_rates.empty:
        return pd.DataFrame()
    valid = matches[~matches["winner"].isin(["No Result", "Draw", "Tie"])].dropna(subset=["winner"])
    season_wins = valid.groupby(["season", "winner"]).size().reset_index(name="wins")
    p1 = valid.groupby(["season", "team1"]).size().reset_index(name="p1").rename(columns={"team1": "team"})
    p2 = valid.groupby(["season", "team2"]).size().reset_index(name="p2").rename(columns={"team2": "team"})
    played = pd.merge(p1, p2, on=["season", "team"], how="outer").fillna(0)
    played["total_played"] = played["p1"] + played["p2"]
    season_wins.rename(columns={"winner": "team"}, inplace=True)
    rates = pd.merge(played, season_wins, on=["season", "team"], how="left").fillna(0)
    rates["win_rate"] = (rates["wins"] / rates["total_played"] * 100).round(1)
    top_teams = win_rates.head(top_n).index.tolist()
    return rates[rates["team"].isin(top_teams)]


def compute_season_player_rankings(deliveries: pd.DataFrame, top_n: int = 5, min_balls: int = 30):
    """
    Per-season top batsmen and bowlers.
    Requires 'season' column in deliveries (merged upstream from matches).
    Returns (batsmen_df, bowlers_df).
    """
    if deliveries.empty or "season" not in deliveries.columns:
        return pd.DataFrame(), pd.DataFrame()

    # Batsmen
    bat = (
        deliveries.groupby(["season", "batsman"])
        .agg(runs=("batsman_runs", "sum"), balls=("batsman_runs", "count"))
        .reset_index()
    )
    bat = bat[bat["balls"] >= min_balls].copy()
    bat["strike_rate"] = (bat["runs"] / bat["balls"] * 100).round(1)
    bat["rank"] = bat.groupby("season")["runs"].rank(method="first", ascending=False).astype(int)
    bat_top = bat[bat["rank"] <= top_n].sort_values(["season", "rank"])

    # Bowlers
    agg = {"runs_given": ("total_runs", "sum"), "balls": ("total_runs", "count")}
    if "is_wicket" in deliveries.columns:
        agg["wickets"] = ("is_wicket", "sum")
    bowl = deliveries.groupby(["season", "bowler"]).agg(**agg).reset_index()
    bowl = bowl[bowl["balls"] >= min_balls].copy()
    bowl["overs"] = bowl["balls"] / 6
    bowl["economy"] = (bowl["runs_given"] / bowl["overs"]).round(2)
    rank_col = "wickets" if "wickets" in bowl.columns else "economy"
    ascending = rank_col == "economy"
    bowl["rank"] = bowl.groupby("season")[rank_col].rank(method="first", ascending=ascending).astype(int)
    bowl_top = bowl[bowl["rank"] <= top_n].sort_values(["season", "rank"])

    return bat_top, bowl_top
