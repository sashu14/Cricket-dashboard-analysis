"""
tests/test_pipeline.py — Unit tests for the IPL data pipeline.

Run with:
    python -m pytest tests/ -v

Covers: _safe_get, parse_match (valid, missing winner, <2 teams, wickets,
missing overs, season string), team normalisation, compute_win_rates,
compute_venue_win_rates.
"""

import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingest_json import _safe_get, parse_match
from analytics import (
    TEAM_ALIASES,
    normalise_team_names,
    compute_win_rates,
    compute_venue_win_rates,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _delivery(batter="Batter A", bowler="Bowler B", runs=4, wicket=False):
    d = {
        "batter": batter,
        "bowler": bowler,
        "non_striker": "Batter C",
        "runs": {"batter": runs, "extras": 0, "total": runs},
    }
    if wicket:
        d["wickets"] = [{"kind": "caught", "player_out": batter}]
    return d


def _match(winner="Team A", toss_winner="Team A", toss_decision="field", season=2023):
    return {
        "info": {
            "teams": ["Team A", "Team B"],
            "dates": ["2023-04-01"],
            "venue": "Test Ground",
            "city": "Test City",
            "season": season,
            "toss": {"winner": toss_winner, "decision": toss_decision},
            "outcome": {"winner": winner, "by": {"runs": 10}},
            "player_of_match": ["Batter A"],
            "event": {"name": "Test League", "match_number": 1},
            "match_type": "T20",
        },
        "innings": [
            {
                "team": "Team A",
                "overs": [{"over": 0, "deliveries": [_delivery()]}],
            }
        ],
    }


# ── _safe_get ─────────────────────────────────────────────────────────────────

class TestSafeGet:
    def test_normal_nested_access(self):
        assert _safe_get({"a": {"b": 42}}, "a", "b") == 42

    def test_missing_key_returns_default(self):
        assert _safe_get({"a": {}}, "a", "b", default="N/A") == "N/A"

    def test_empty_dict(self):
        assert _safe_get({}, "x", default=0) == 0

    def test_non_dict_intermediate_returns_default(self):
        assert _safe_get({"a": "string"}, "a", "b", default="fb") == "fb"

    def test_none_value_returns_default(self):
        assert _safe_get({"a": None}, "a", default="d") == "d"


# ── parse_match ───────────────────────────────────────────────────────────────

class TestParseMatch:
    def test_valid_match_parses_correctly(self):
        row, deliveries = parse_match("m001", _match())
        assert row is not None
        assert row["team1"] == "Team A"
        assert row["team2"] == "Team B"
        assert row["winner"] == "Team A"
        assert len(deliveries) == 1
        assert deliveries[0]["batsman_runs"] == 4

    def test_missing_winner_defaults_to_no_result(self):
        data = _match()
        data["info"]["outcome"] = {}
        row, _ = parse_match("m002", data)
        assert row["winner"] == "No Result"

    def test_fewer_than_two_teams_returns_none(self):
        data = _match()
        data["info"]["teams"] = ["Only One"]
        row, deliveries = parse_match("m003", data)
        assert row is None
        assert deliveries == []

    def test_wicket_delivery_sets_flag(self):
        data = _match()
        data["innings"][0]["overs"][0]["deliveries"].append(_delivery(wicket=True))
        _, deliveries = parse_match("m004", data)
        wickets = [d for d in deliveries if d["is_wicket"] == 1]
        assert len(wickets) == 1
        assert wickets[0]["dismissal_kind"] == "caught"

    def test_missing_overs_key_gives_zero_deliveries(self):
        data = _match()
        data["innings"][0] = {"team": "Team A"}   # no 'overs'
        row, deliveries = parse_match("m005", data)
        assert row is not None     # match row still parsed
        assert len(deliveries) == 0

    def test_season_string_normalised_to_int(self):
        data = _match(season="2007/08")
        row, _ = parse_match("m006", data)
        assert row["season"] == 2007

    def test_malformed_runs_defaults_to_zero(self):
        data = _match()
        data["innings"][0]["overs"][0]["deliveries"][0]["runs"]["batter"] = "bad"
        row, deliveries = parse_match("m007", data)
        assert row is not None
        assert deliveries[0]["batsman_runs"] == 0


# ── normalise_team_names ──────────────────────────────────────────────────────

class TestNormaliseTeamNames:
    def test_known_aliases_replaced(self):
        df = pd.DataFrame({
            "team1": ["Royal Challengers Bangalore"],
            "team2": ["Delhi Daredevils"],
        })
        out = normalise_team_names(df, ["team1", "team2"])
        assert out.loc[0, "team1"] == "Royal Challengers Bengaluru"
        assert out.loc[0, "team2"] == "Delhi Capitals"

    def test_kings_xi_to_punjab_kings(self):
        df = pd.DataFrame({"team1": ["Kings XI Punjab"]})
        out = normalise_team_names(df, ["team1"])
        assert out.loc[0, "team1"] == "Punjab Kings"

    def test_unknown_team_unchanged(self):
        df = pd.DataFrame({"team1": ["Kolkata Knight Riders"]})
        out = normalise_team_names(df, ["team1"])
        assert out.loc[0, "team1"] == "Kolkata Knight Riders"

    def test_missing_column_ignored_gracefully(self):
        df = pd.DataFrame({"team1": ["Mumbai Indians"]})
        out = normalise_team_names(df, ["team1", "nonexistent"])
        assert list(out.columns) == ["team1"]

    def test_original_dataframe_not_mutated(self):
        df = pd.DataFrame({"team1": ["Kings XI Punjab"]})
        _ = normalise_team_names(df, ["team1"])
        assert df.loc[0, "team1"] == "Kings XI Punjab"   # original unchanged


# ── compute_win_rates ─────────────────────────────────────────────────────────

class TestComputeWinRates:
    def _matches(self):
        return pd.DataFrame({
            "team1":  ["A", "A", "B", "A"],
            "team2":  ["B", "B", "A", "C"],
            "winner": ["A", "A", "B", "No Result"],
        })

    def test_rates_computed_correctly(self):
        rates = compute_win_rates(self._matches())
        # A: 2 wins / 4 played (team1 + team2 counts) = 50.0 %
        assert abs(rates["A"] - 50.0) < 0.1

    def test_no_result_excluded_from_index(self):
        rates = compute_win_rates(self._matches())
        assert "No Result" not in rates.index

    def test_empty_input_returns_empty_series(self):
        assert compute_win_rates(pd.DataFrame()).empty

    def test_result_sorted_descending(self):
        rates = compute_win_rates(self._matches())
        assert list(rates) == sorted(rates, reverse=True)


# ── compute_venue_win_rates ───────────────────────────────────────────────────

class TestComputeVenueWinRates:
    def _matches(self):
        # V1 row 2: toss_winner=B chose field, winner=B → field-first win
        return pd.DataFrame({
            "venue":         ["V1", "V1", "V1", "V2", "V2"],
            "toss_winner":   ["A",  "A",  "B",  "A",  "B"],
            "toss_decision": ["bat","bat","field","field","bat"],
            "winner":        ["A",  "A",  "B",  "A",  "B"],
        })

    def test_returns_rate_columns_not_counts(self):
        rates = compute_venue_win_rates(self._matches(), top_n=2)
        assert "Bat First Win%" in rates.columns
        assert "Field First Win%" in rates.columns

    def test_percentages_sum_to_100(self):
        rates = compute_venue_win_rates(self._matches(), top_n=2)
        for _, row in rates.iterrows():
            assert abs(row["Bat First Win%"] + row["Field First Win%"] - 100.0) < 0.1

    def test_v1_bat_first_win_rate(self):
        rates = compute_venue_win_rates(self._matches(), top_n=2)
        # V1: rows 0,1 → A bats first and wins (bat_wins=2)
        # V1: row 2  → B chose field and wins (field_wins=1)
        # → Bat First Win% = 66.7%, Field First Win% = 33.3%
        assert abs(rates.loc["V1", "Bat First Win%"] - 66.7) < 0.1
        assert abs(rates.loc["V1", "Field First Win%"] - 33.3) < 0.1

    def test_empty_input_returns_empty(self):
        assert compute_venue_win_rates(pd.DataFrame()).empty
