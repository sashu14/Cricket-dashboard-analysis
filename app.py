import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration & Theming (v2.0 - Real Cricsheet Data) ---
st.set_page_config(
    page_title="IPL Analytics Dashboard", 
    page_icon="🏏",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Custom color palette tailored for a premium Dark Mode aesthetic
COLORS = {
    "background": "#0E1117",
    "primary": "#00E5FF",    # Neon Blue
    "secondary": "#00E676",  # Emerald Green
    "accent": "#78909C",     # Slate Grey
    "text": "#FAFAFA",
    "card_bg": "#1E2127",
    "warning": "#FF3D00"
}

# Injecting Custom CSS for visually impressive KPI Metric Cards
st.markdown(f"""
    <style>
    .metric-card {{
        background-color: {COLORS['card_bg']};
        border-left: 5px solid {COLORS['primary']};
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }}
    .metric-card:hover {{
        transform: translateY(-5px);
    }}
    .metric-value {{
        font-size: 2.5rem;
        font-weight: 800;
        color: {COLORS['primary']};
        margin-top: 5px;
    }}
    .metric-label {{
        font-size: 0.9rem;
        color: {COLORS['accent']};
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }}
    </style>
""", unsafe_allow_html=True)

# --- Data Loading (with Fault Tolerance) ---
@st.cache_data(ttl=3600)
def load_data():
    try:
        matches = pd.read_csv("cleaned_matches.csv")
        deliveries = pd.read_csv("cleaned_deliveries.csv")
        return matches, deliveries
    except FileNotFoundError:
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

matches, deliveries = load_data()

if matches.empty or deliveries.empty:
    st.error("Data not found. Please run `python pipeline.py` first to generate the cleaned datasets.")
    st.stop()

# --- Schema Generalization (Dynamic Entity Extraction) ---
# We avoid hardcoding any team, venue, or season.
seasons = sorted(matches['season'].dropna().unique().tolist()) if 'season' in matches.columns else []
teams = sorted(pd.concat([matches.get('team1', pd.Series()), matches.get('team2', pd.Series())]).dropna().unique().tolist())
venues = sorted(matches['venue'].dropna().unique().tolist()) if 'venue' in matches.columns else []

# --- Global Filters (Sidebar) ---
st.sidebar.title("🎛️ Dashboard Controls")
st.sidebar.markdown("Filter the dataset dynamically.")

selected_season = st.sidebar.multiselect("Select Season(s)", ["All"] + seasons, default="All")
selected_team = st.sidebar.multiselect("Select Team(s)", ["All"] + teams, default="All")
selected_venue = st.sidebar.multiselect("Select Venue(s)", ["All"] + venues, default="All")

# Apply Filters
filtered_matches = matches.copy()

if "All" not in selected_season and selected_season:
    filtered_matches = filtered_matches[filtered_matches['season'].isin(selected_season)]
if "All" not in selected_team and selected_team:
    filtered_matches = filtered_matches[(filtered_matches['team1'].isin(selected_team)) | (filtered_matches['team2'].isin(selected_team))]
if "All" not in selected_venue and selected_venue:
    filtered_matches = filtered_matches[filtered_matches['venue'].isin(selected_venue)]

# Filter deliveries based on the filtered matches
filtered_deliveries = deliveries.copy()
if 'id' in filtered_matches.columns and 'match_id' in filtered_deliveries.columns:
    valid_match_ids = filtered_matches['id'].unique()
    filtered_deliveries = filtered_deliveries[filtered_deliveries['match_id'].isin(valid_match_ids)]

# --- Top-Level KPIs ---
st.title("🏏 Interactive IPL Analytics")
st.markdown("A high-fidelity, fault-tolerant visualization platform for cricket analytics.")

col1, col2, col3 = st.columns(3)

# 1. Total Matches
total_matches = len(filtered_matches)

# 2. Highest Win Rate Calculation
if total_matches > 0 and 'winner' in filtered_matches.columns:
    # Filter out draws/no results
    valid_results = filtered_matches[~filtered_matches['winner'].isin(['No Result', 'Draw', 'Tie'])]
    win_counts = valid_results['winner'].value_counts()
    
    # Calculate total matches played by each team in the current filter scope
    matches_played = pd.concat([filtered_matches['team1'], filtered_matches['team2']]).value_counts()
    
    # Compute win rates
    win_rates = (win_counts / matches_played * 100).dropna().sort_values(ascending=False)
    
    highest_win_rate_team = win_rates.index[0] if not win_rates.empty else "N/A"
    highest_win_rate_val = f"{win_rates.iloc[0]:.1f}%" if not win_rates.empty else "N/A"
else:
    win_rates = pd.Series(dtype=float)
    highest_win_rate_team, highest_win_rate_val = "N/A", "N/A"

# 3. Top Run Scorer Calculation
if not filtered_deliveries.empty and 'batsman' in filtered_deliveries.columns and 'batsman_runs' in filtered_deliveries.columns:
    batsman_runs = filtered_deliveries.groupby('batsman')['batsman_runs'].sum().sort_values(ascending=False)
    top_scorer = batsman_runs.index[0] if not batsman_runs.empty else "N/A"
    top_scorer_runs = int(batsman_runs.iloc[0]) if not batsman_runs.empty else 0
else:
    top_scorer, top_scorer_runs = "N/A", 0

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Matches</div>
            <div class="metric-value">{total_matches}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Top Win Rate ({highest_win_rate_team})</div>
            <div class="metric-value">{highest_win_rate_val}</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Top Scorer ({top_scorer})</div>
            <div class="metric-value">{top_scorer_runs}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- Visualizations ---
row1_col1, row1_col2 = st.columns(2)

# Chart 1: Win Rates by Team
with row1_col1:
    st.subheader("Win Rates by Team")
    if not win_rates.empty:
        fig_win_rates = px.bar(
            x=win_rates.index, 
            y=win_rates.values,
            labels={'x': 'Team', 'y': 'Win Rate (%)'},
            color_discrete_sequence=[COLORS['primary']]
        )
        fig_win_rates.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            xaxis_title=None,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_win_rates, use_container_width=True)
    else:
        st.info("Not enough data to compute win rates.")

# Chart 2: Toss Impact Analysis (Sunburst)
with row1_col2:
    st.subheader("Toss Impact Analysis")
    if 'toss_winner' in filtered_matches.columns and 'toss_decision' in filtered_matches.columns and 'winner' in filtered_matches.columns:
        filtered_matches['toss_match_winner'] = filtered_matches['toss_winner'] == filtered_matches['winner']
        filtered_matches['toss_match_winner'] = filtered_matches['toss_match_winner'].map({True: 'Won Match', False: 'Lost Match'})
        
        toss_data = filtered_matches.dropna(subset=['toss_decision', 'toss_match_winner']).groupby(['toss_decision', 'toss_match_winner']).size().reset_index(name='count')
        
        fig_toss = px.sunburst(
            toss_data, 
            path=['toss_decision', 'toss_match_winner'], 
            values='count',
            color='toss_match_winner',
            color_discrete_map={'Won Match': COLORS['secondary'], 'Lost Match': COLORS['accent']}
        )
        fig_toss.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_toss, use_container_width=True)
    else:
        st.info("Toss data not available.")

st.markdown("---")

row2_col1, row2_col2 = st.columns(2)

# Chart 3: Player Stats - Strike Rate vs Runs
with row2_col1:
    st.subheader("Batsmen: Strike Rate vs Runs")
    if not filtered_deliveries.empty and 'batsman' in filtered_deliveries.columns and 'batsman_runs' in filtered_deliveries.columns:
        batsman_stats = filtered_deliveries.groupby('batsman').agg(
            total_runs=('batsman_runs', 'sum'),
            balls_faced=('batsman_runs', 'count')
        ).reset_index()
        
        # Filter noise (e.g., batsmen who faced very few balls)
        batsman_stats = batsman_stats[batsman_stats['balls_faced'] > 50]
        batsman_stats['strike_rate'] = (batsman_stats['total_runs'] / batsman_stats['balls_faced']) * 100
        
        fig_bat = px.scatter(
            batsman_stats, x='strike_rate', y='total_runs', 
            hover_name='batsman',
            hover_data={'strike_rate': ':.1f', 'total_runs': True, 'balls_faced': True},
            labels={'strike_rate': 'Strike Rate', 'total_runs': 'Total Runs'},
            color_discrete_sequence=[COLORS['primary']],
            size='total_runs', size_max=25, opacity=0.7
        )
        fig_bat.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_bat, use_container_width=True)
    else:
        st.info("Delivery data not available for batsmen.")

# Chart 4: Venue-Wise Trends (Heatmap)
with row2_col2:
    st.subheader("Venue Trends (Bat vs Field First)")
    if 'venue' in filtered_matches.columns and 'toss_decision' in filtered_matches.columns and 'toss_winner' in filtered_matches.columns and 'winner' in filtered_matches.columns:
        def bat_first_won(row):
            if pd.isna(row['winner']) or row['winner'] in ['No Result', 'Draw', 'Tie']:
                return None
            if row['toss_decision'] == 'bat':
                return row['toss_winner'] == row['winner']
            else:
                return row['toss_winner'] != row['winner']
                
        filtered_matches['bat_first_won'] = filtered_matches.apply(bat_first_won, axis=1)
        
        # Drop rows where result is none/draw
        venue_data = filtered_matches.dropna(subset=['bat_first_won'])
        
        venue_stats = venue_data.groupby(['venue', 'bat_first_won']).size().unstack(fill_value=0)
        
        if True in venue_stats.columns and False in venue_stats.columns:
            venue_stats.rename(columns={True: 'Bat First Won', False: 'Field First Won'}, inplace=True)
            
            # Select top venues by total matches to keep the heatmap clean
            venue_stats['total'] = venue_stats.get('Bat First Won', 0) + venue_stats.get('Field First Won', 0)
            venue_stats = venue_stats.sort_values(by='total', ascending=False).head(12)
            venue_stats.drop(columns=['total'], inplace=True)
            
            fig_venue = px.imshow(
                venue_stats.T,
                labels=dict(x="Venue", y="Outcome", color="Wins"),
                color_continuous_scale=[COLORS['card_bg'], COLORS['primary']],
                aspect="auto",
                text_auto=True
            )
            fig_venue.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color=COLORS['text']),
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig_venue, use_container_width=True)
        else:
            st.info("Not enough variations in match outcomes to plot heatmap.")
    else:
        st.info("Venue data not available.")

st.markdown("---")

row3_col1, row3_col2 = st.columns(2)

# Chart 5: Bowler Stats - Economy vs Wickets (or Balls Bowled)
with row3_col1:
    st.subheader("Bowlers: Economy vs Wickets")
    if not filtered_deliveries.empty and 'bowler' in filtered_deliveries.columns and 'total_runs' in filtered_deliveries.columns:
        # Adaptation: If 'is_wicket' is missing (which happens in some datasets), we count balls bowled instead.
        if 'is_wicket' in filtered_deliveries.columns:
            bowler_stats = filtered_deliveries.groupby('bowler').agg(
                runs_conceded=('total_runs', 'sum'),
                balls_bowled=('total_runs', 'count'),
                wickets=('is_wicket', 'sum')
            ).reset_index()
            y_col = 'wickets'
            y_label = 'Total Wickets'
        else:
            bowler_stats = filtered_deliveries.groupby('bowler').agg(
                runs_conceded=('total_runs', 'sum'),
                balls_bowled=('total_runs', 'count')
            ).reset_index()
            y_col = 'balls_bowled'
            y_label = 'Balls Bowled (Wickets data missing)'
            
        bowler_stats = bowler_stats[bowler_stats['balls_bowled'] > 60] # Filter min 10 overs
        bowler_stats['overs'] = bowler_stats['balls_bowled'] / 6
        bowler_stats['economy'] = bowler_stats['runs_conceded'] / bowler_stats['overs']
        
        fig_bowl = px.scatter(
            bowler_stats, x='economy', y=y_col, 
            hover_name='bowler',
            hover_data={'economy': ':.2f', y_col: True, 'overs': ':.1f'},
            labels={'economy': 'Economy Rate', y_col: y_label},
            color_discrete_sequence=[COLORS['secondary']],
            size='balls_bowled', size_max=25, opacity=0.7
        )
        fig_bowl.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_bowl, use_container_width=True)
    else:
        st.info("Delivery data not available for bowlers.")

# Chart 6: Win Rates Across Seasons
with row3_col2:
    st.subheader("Win Rates Across Seasons")
    if 'season' in filtered_matches.columns and 'winner' in filtered_matches.columns:
        valid_matches = filtered_matches.dropna(subset=['winner'])
        valid_matches = valid_matches[~valid_matches['winner'].isin(['No Result', 'Draw', 'Tie'])]
        
        # Calculate win rate per season per team
        season_wins = valid_matches.groupby(['season', 'winner']).size().reset_index(name='wins')
        season_played1 = valid_matches.groupby(['season', 'team1']).size().reset_index(name='played1')
        season_played2 = valid_matches.groupby(['season', 'team2']).size().reset_index(name='played2')
        
        season_played1.rename(columns={'team1': 'team'}, inplace=True)
        season_played2.rename(columns={'team2': 'team'}, inplace=True)
        
        # Combine matches played
        season_played = pd.merge(season_played1, season_played2, on=['season', 'team'], how='outer').fillna(0)
        season_played['total_played'] = season_played['played1'] + season_played['played2']
        
        season_wins.rename(columns={'winner': 'team'}, inplace=True)
        
        season_rates = pd.merge(season_played, season_wins, on=['season', 'team'], how='left').fillna(0)
        season_rates['win_rate'] = (season_rates['wins'] / season_rates['total_played']) * 100
        
        # Get top 5 teams overall to avoid cluttered line chart
        top_teams = win_rates.head(5).index.tolist() if not win_rates.empty else []
        season_rates_top = season_rates[season_rates['team'].isin(top_teams)]
        
        fig_season = px.line(
            season_rates_top, x='season', y='win_rate', color='team',
            markers=True,
            labels={'season': 'Season', 'win_rate': 'Win Rate (%)', 'team': 'Team'},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_season.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_season, use_container_width=True)
    else:
        st.info("Season data not available.")


st.markdown("---")
st.markdown("<div style='text-align: center; color: #78909C;'>Powered by Streamlit & Plotly | Fault-Tolerant & Schema-Agnostic Design</div>", unsafe_allow_html=True)
