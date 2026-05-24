"""
ingest_json.py — Fault-tolerant JSON ingestion pipeline for Cricsheet IPL data.

Reads all JSON files from a zip archive (or directory), parses the Cricsheet
JSON schema, and produces two clean CSVs:
  - cleaned_matches.csv  (one row per match)
  - cleaned_deliveries.csv  (one row per delivery)

Design decisions:
  - Schema-agnostic: no hardcoded team/player/venue names
  - Fault-tolerant: bad JSON files are logged and skipped, never crash the app
  - Graceful fallback: optional fields (player_of_match, city, outcome by type)
    handled via .get() with safe defaults
"""

import json
import logging
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ingest_json.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _safe_get(d: dict, *keys, default=None):
    """Safely traverse nested dict keys; return default if any key is missing."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
        if cur is None:
            return default
    return cur


def parse_match(match_id: str, data: dict) -> tuple[dict | None, list[dict]]:
    """
    Parse one Cricsheet JSON file into:
      - match_row  : dict representing one row in matches table
      - deliveries : list of dicts, one per delivery
    Returns (None, []) on unrecoverable parse errors.
    """
    try:
        info = data.get("info", {})
        innings_list = data.get("innings", [])

        teams = info.get("teams", [])
        if len(teams) < 2:
            log.warning(f"[{match_id}] Less than 2 teams found — skipping.")
            return None, []

        outcome = info.get("outcome", {})
        winner = _safe_get(outcome, "winner", default="No Result")

        # Outcome 'by' can be runs or wickets
        by = outcome.get("by", {})
        win_by_runs = by.get("runs", np.nan)
        win_by_wickets = by.get("wickets", np.nan)

        toss = info.get("toss", {})
        dates = info.get("dates", [])
        date = dates[0] if dates else None

        pom = info.get("player_of_match", [])
        player_of_match = pom[0] if pom else "Unknown"

        season = info.get("season")
        # Some older files store season as "2007/08" — normalise to int start year
        if isinstance(season, str) and "/" in season:
            season = int(season.split("/")[0])
        else:
            try:
                season = int(season)
            except (TypeError, ValueError):
                season = np.nan

        match_row = {
            "id": match_id,
            "season": season,
            "date": date,
            "venue": info.get("venue", "Unknown"),
            "city": info.get("city", "Unknown"),
            "team1": teams[0],
            "team2": teams[1],
            "toss_winner": toss.get("winner"),
            "toss_decision": toss.get("decision"),
            "winner": winner,
            "win_by_runs": win_by_runs,
            "win_by_wickets": win_by_wickets,
            "player_of_match": player_of_match,
            "match_number": _safe_get(info, "event", "match_number", default=np.nan),
            "match_type": info.get("match_type", "T20"),
        }

        # ── Deliveries ───────────────────────────────────────────────────────
        deliveries = []
        for inning_idx, inning in enumerate(innings_list):
            batting_team = inning.get("team", f"team_{inning_idx + 1}")
            bowling_team = (
                teams[1] if batting_team == teams[0] else teams[0]
            )

            for over_obj in inning.get("overs", []):
                over_num = over_obj.get("over", 0)
                for ball_idx, delivery in enumerate(over_obj.get("deliveries", [])):
                    runs = delivery.get("runs", {})
                    extras = delivery.get("extras", {})
                    wickets = delivery.get("wickets", [])

                    # Fault-tolerant numeric coercion
                    def safe_int(v):
                        try:
                            return int(v)
                        except (TypeError, ValueError):
                            return 0

                    batsman_runs = safe_int(runs.get("batter", 0))
                    extra_runs   = safe_int(runs.get("extras", 0))
                    total_runs   = safe_int(runs.get("total", 0))
                    is_wicket    = 1 if wickets else 0
                    player_out   = wickets[0].get("player_out", "") if wickets else ""
                    dismissal    = wickets[0].get("kind", "") if wickets else ""

                    deliveries.append({
                        "match_id":     match_id,
                        "inning":       inning_idx + 1,
                        "batting_team": batting_team,
                        "bowling_team": bowling_team,
                        "over":         over_num,
                        "ball":         ball_idx + 1,
                        "batsman":      delivery.get("batter", ""),
                        "non_striker":  delivery.get("non_striker", ""),
                        "bowler":       delivery.get("bowler", ""),
                        "batsman_runs": batsman_runs,
                        "extra_runs":   extra_runs,
                        "total_runs":   total_runs,
                        "is_wicket":    is_wicket,
                        "player_dismissed": player_out,
                        "dismissal_kind":   dismissal,
                        "extras_type":  ",".join(extras.keys()) if extras else "",
                    })

        return match_row, deliveries

    except Exception as exc:
        log.error(f"[{match_id}] Unexpected error during parse: {exc}")
        return None, []


# ── Main ingestion ────────────────────────────────────────────────────────────
def ingest(zip_path: str, output_dir: str = ".") -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ingest all JSON files from the given zip.
    Returns (matches_df, deliveries_df).
    """
    zip_path = Path(zip_path)
    if not zip_path.exists():
        log.error(f"Zip file not found: {zip_path}")
        return pd.DataFrame(), pd.DataFrame()

    all_matches = []
    all_deliveries = []
    processed = 0
    skipped = 0

    log.info(f"Opening {zip_path} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        json_names = [n for n in zf.namelist() if n.endswith(".json")]
        total = len(json_names)
        log.info(f"Found {total} JSON files.")

        for name in json_names:
            match_id = Path(name).stem  # e.g. "1082591"
            try:
                with zf.open(name) as f:
                    raw = f.read()
                    # Fault tolerance: skip blank or unreadable files
                    if not raw.strip():
                        log.warning(f"[{match_id}] Empty file — skipping.")
                        skipped += 1
                        continue
                    data = json.loads(raw)
            except json.JSONDecodeError as e:
                log.error(f"[{match_id}] JSON decode error: {e} — skipping.")
                skipped += 1
                continue
            except Exception as e:
                log.error(f"[{match_id}] Failed to open: {e} — skipping.")
                skipped += 1
                continue

            match_row, deliveries = parse_match(match_id, data)
            if match_row is None:
                skipped += 1
                continue

            all_matches.append(match_row)
            all_deliveries.extend(deliveries)
            processed += 1

            if processed % 100 == 0:
                log.info(f"  Processed {processed}/{total} files ...")

    log.info(f"Ingestion complete. Processed: {processed}, Skipped: {skipped}")

    # ── Build DataFrames ──────────────────────────────────────────────────────
    matches_df = pd.DataFrame(all_matches)
    deliveries_df = pd.DataFrame(all_deliveries)

    if matches_df.empty:
        log.error("No matches were successfully parsed.")
        return pd.DataFrame(), pd.DataFrame()

    # ── Type enforcement ──────────────────────────────────────────────────────
    for col in ["win_by_runs", "win_by_wickets", "season", "match_number"]:
        if col in matches_df.columns:
            matches_df[col] = pd.to_numeric(matches_df[col], errors="coerce")

    for col in ["batsman_runs", "extra_runs", "total_runs", "is_wicket",
                "over", "ball", "inning"]:
        if col in deliveries_df.columns:
            deliveries_df[col] = pd.to_numeric(deliveries_df[col], errors="coerce").fillna(0).astype(int)

    # ── Sort & save ───────────────────────────────────────────────────────────
    if "date" in matches_df.columns:
        matches_df["date"] = pd.to_datetime(matches_df["date"], errors="coerce")
        matches_df.sort_values("date", inplace=True)

    out_matches = os.path.join(output_dir, "cleaned_matches.csv")
    out_deliveries = os.path.join(output_dir, "cleaned_deliveries.csv")

    matches_df.to_csv(out_matches, index=False)
    deliveries_df.to_csv(out_deliveries, index=False)

    log.info(f"Saved {len(matches_df)} matches → {out_matches}")
    log.info(f"Saved {len(deliveries_df)} deliveries → {out_deliveries}")

    return matches_df, deliveries_df


if __name__ == "__main__":
    import sys
    zip_file = sys.argv[1] if len(sys.argv) > 1 else "frontend/ipl_male_json.zip"
    ingest(zip_file, output_dir=".")
