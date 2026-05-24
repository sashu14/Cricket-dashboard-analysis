import streamlit as st
import pandas as pd

import analytics as an
import charts as ch

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IPL Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "background": "#0E1117",
    "primary":    "#00E5FF",
    "secondary":  "#00E676",
    "accent":     "#78909C",
    "text":       "#FAFAFA",
    "card_bg":    "#1E2127",
    "warning":    "#FF3D00",
}

st.markdown(f"""
    <style>
    .metric-card {{
        background-color: {COLORS['card_bg']};
        border-left: 5px solid {COLORS['primary']};
        padding: 20px; border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        margin-bottom: 20px; transition: transform 0.3s ease;
    }}
    .metric-card:hover {{ transform: translateY(-5px); }}
    .metric-value {{
        font-size: 2.5rem; font-weight: 800;
        color: {COLORS['primary']}; margin-top: 5px;
    }}
    .metric-label {{
        font-size: 0.9rem; color: {COLORS['accent']};
        text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;
    }}
    </style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    try:
        matches    = pd.read_csv("cleaned_matches.csv")
        deliveries = pd.read_csv("cleaned_deliveries.csv")
        # Normalise historical team name variants
        matches    = an.normalise_team_names(matches, ["team1", "team2", "toss_winner", "winner"])
        deliveries = an.normalise_team_names(deliveries, ["batting_team", "bowling_team"])
        # Attach season to deliveries for per-season player ranking
        if "id" in matches.columns and "match_id" in deliveries.columns and "season" in matches.columns:
            season_map = matches.set_index("id")["season"]
            deliveries["season"] = deliveries["match_id"].map(season_map)
        return matches, deliveries
    except FileNotFoundError:
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()


matches, deliveries = load_data()

if matches.empty or deliveries.empty:
    st.error("Data not found. Run `python ingest_json.py ipl_male_json.zip` first.")
    st.stop()

# ── Dynamic entity extraction (schema-agnostic) ───────────────────────────────
seasons = sorted(matches["season"].dropna().unique().tolist()) if "season" in matches.columns else []
teams   = sorted(pd.concat([matches.get("team1", pd.Series()), matches.get("team2", pd.Series())]).dropna().unique().tolist())
venues  = sorted(matches["venue"].dropna().unique().tolist()) if "venue" in matches.columns else []

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.title("🎛️ Dashboard Controls")
st.sidebar.markdown("Filter the dataset dynamically.")

sel_season = st.sidebar.multiselect("Select Season(s)", ["All"] + [str(s) for s in seasons], default="All")
sel_team   = st.sidebar.multiselect("Select Team(s)",   ["All"] + teams,   default="All")
sel_venue  = st.sidebar.multiselect("Select Venue(s)",  ["All"] + venues,  default="All")

fm = matches.copy()
if "All" not in sel_season and sel_season:
    fm = fm[fm["season"].astype(str).isin(sel_season)]
if "All" not in sel_team and sel_team:
    fm = fm[(fm["team1"].isin(sel_team)) | (fm["team2"].isin(sel_team))]
if "All" not in sel_venue and sel_venue:
    fm = fm[fm["venue"].isin(sel_venue)]

fd = deliveries.copy()
if "id" in fm.columns and "match_id" in fd.columns:
    fd = fd[fd["match_id"].isin(fm["id"].unique())]

# ── Compute analytics ─────────────────────────────────────────────────────────
win_rates    = an.compute_win_rates(fm)
toss_data    = an.compute_toss_impact(fm)
bat_stats    = an.compute_batsman_stats(fd)
bowl_stats, y_col, y_label = an.compute_bowler_stats(fd)
venue_rates  = an.compute_venue_win_rates(fm)
season_rates = an.compute_season_win_rates(fm, win_rates)

top_scorer     = bat_stats.sort_values("total_runs", ascending=False).iloc[0]["batsman"]  if not bat_stats.empty else "N/A"
top_scorer_val = int(bat_stats.sort_values("total_runs", ascending=False).iloc[0]["total_runs"]) if not bat_stats.empty else 0
top_team       = win_rates.index[0]   if not win_rates.empty else "N/A"
top_team_pct   = f"{win_rates.iloc[0]:.1f}%" if not win_rates.empty else "N/A"

# ── KPI cards ─────────────────────────────────────────────────────────────────
st.title("🏏 Interactive IPL Analytics")
st.markdown("A high-fidelity, fault-tolerant visualization platform for cricket analytics.")

c1, c2, c3 = st.columns(3)
for col, label, value in [
    (c1, "Total Matches", len(fm)),
    (c2, f"Top Win Rate ({top_team})", top_team_pct),
    (c3, f"Top Scorer ({top_scorer})", top_scorer_val),
]:
    col.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Row 1: Win rates + Toss impact ───────────────────────────────────────────
r1c1, r1c2 = st.columns(2)
with r1c1:
    st.subheader("Win Rates by Team")
    if not win_rates.empty:
        st.plotly_chart(ch.fig_win_rates(win_rates, COLORS), use_container_width=True)
    else:
        st.info("Not enough data.")

with r1c2:
    st.subheader("Toss Impact Analysis")
    if not toss_data.empty:
        st.plotly_chart(ch.fig_toss_sunburst(toss_data, COLORS), use_container_width=True)
    else:
        st.info("Toss data not available.")

st.markdown("---")

# ── Row 2: Batsmen + Bowlers ──────────────────────────────────────────────────
r2c1, r2c2 = st.columns(2)
with r2c1:
    st.subheader("Batsmen: Strike Rate vs Runs")
    if not bat_stats.empty:
        st.plotly_chart(ch.fig_batsman_scatter(bat_stats, COLORS), use_container_width=True)
    else:
        st.info("Delivery data not available.")

with r2c2:
    st.subheader("Bowlers: Economy vs Wickets")
    if not bowl_stats.empty:
        st.plotly_chart(ch.fig_bowler_scatter(bowl_stats, y_col, y_label, COLORS), use_container_width=True)
    else:
        st.info("Delivery data not available.")

st.markdown("---")

# ── Row 3: Venue win rates + Season trends ────────────────────────────────────
r3c1, r3c2 = st.columns(2)
with r3c1:
    st.subheader("Venue Trends — Bat vs Field First Win %")
    if not venue_rates.empty:
        st.plotly_chart(ch.fig_venue_win_rates(venue_rates, COLORS), use_container_width=True)
    else:
        st.info("Venue data not available.")

with r3c2:
    st.subheader("Win Rates Across Seasons")
    if not season_rates.empty:
        st.plotly_chart(ch.fig_season_trends(season_rates, COLORS), use_container_width=True)
    else:
        st.info("Season data not available.")

st.markdown("---")

# ── Per-season player rankings ────────────────────────────────────────────────
st.subheader("📅 Per-Season Player Rankings")
st.markdown("Top 5 batsmen and bowlers for each IPL season.")

bat_season, bowl_season = an.compute_season_player_rankings(fd)

if not bat_season.empty and not bowl_season.empty:
    available_seasons = sorted(bat_season["season"].dropna().unique().tolist(), reverse=True)
    sel_rank_season = st.selectbox(
        "Select Season", [str(int(s)) for s in available_seasons], key="season_rank"
    )
    s_val = float(sel_rank_season)

    ps1, ps2 = st.columns(2)
    with ps1:
        st.markdown(f"**Top Batsmen — {sel_rank_season}**")
        b_df = bat_season[bat_season["season"] == s_val][["batsman", "runs", "balls", "strike_rate", "rank"]]
        b_df.columns = ["Batsman", "Runs", "Balls", "Strike Rate", "Rank"]
        st.dataframe(b_df.set_index("Rank"), use_container_width=True)

    with ps2:
        st.markdown(f"**Top Bowlers — {sel_rank_season}**")
        cols = ["bowler", "wickets", "economy", "overs", "rank"] if "wickets" in bowl_season.columns \
               else ["bowler", "economy", "overs", "rank"]
        bw_df = bowl_season[bowl_season["season"] == s_val][cols].copy()
        bw_df.columns = [c.title() for c in cols[:-1]] + ["Rank"]
        st.dataframe(bw_df.set_index("Rank"), use_container_width=True)
else:
    st.info("Season player data not available for current filters.")

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#78909C;'>"
    "Powered by Streamlit & Plotly | Fault-Tolerant & Schema-Agnostic Design"
    "</div>",
    unsafe_allow_html=True,
)
