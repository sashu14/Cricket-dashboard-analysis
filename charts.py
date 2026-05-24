"""
charts.py — Plotly figure factory for the IPL Analytics Dashboard.

All functions accept pre-computed DataFrames/Series and a COLORS dict,
returning a plotly Figure. No Streamlit imports — fully testable in isolation.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def _base_layout(colors: dict, **kwargs) -> dict:
    """Shared dark-mode layout applied to every chart."""
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"]),
        margin=dict(l=0, r=0, t=30, b=0),
        **kwargs,
    )


def fig_win_rates(win_rates: pd.Series, colors: dict) -> go.Figure:
    fig = px.bar(
        x=win_rates.index,
        y=win_rates.values,
        labels={"x": "Team", "y": "Win Rate (%)"},
        color_discrete_sequence=[colors["primary"]],
    )
    fig.update_layout(**_base_layout(colors, xaxis_title=None))
    return fig


def fig_toss_sunburst(toss_data: pd.DataFrame, colors: dict) -> go.Figure:
    fig = px.sunburst(
        toss_data,
        path=["toss_decision", "toss_match_winner"],
        values="count",
        color="toss_match_winner",
        color_discrete_map={
            "Won Match": colors["secondary"],
            "Lost Match": colors["accent"],
        },
    )
    fig.update_layout(**_base_layout(colors))
    return fig


def fig_batsman_scatter(stats: pd.DataFrame, colors: dict) -> go.Figure:
    fig = px.scatter(
        stats,
        x="strike_rate",
        y="total_runs",
        hover_name="batsman",
        hover_data={"strike_rate": ":.1f", "total_runs": True, "balls_faced": True},
        labels={"strike_rate": "Strike Rate", "total_runs": "Total Runs"},
        color_discrete_sequence=[colors["primary"]],
        size="total_runs",
        size_max=25,
        opacity=0.7,
    )
    fig.update_layout(**_base_layout(colors))
    return fig


def fig_bowler_scatter(
    stats: pd.DataFrame, y_col: str, y_label: str, colors: dict
) -> go.Figure:
    fig = px.scatter(
        stats,
        x="economy",
        y=y_col,
        hover_name="bowler",
        hover_data={"economy": ":.2f", y_col: True, "overs": ":.1f"},
        labels={"economy": "Economy Rate", y_col: y_label},
        color_discrete_sequence=[colors["secondary"]],
        size="balls_bowled",
        size_max=25,
        opacity=0.7,
    )
    fig.update_layout(**_base_layout(colors))
    return fig


def fig_venue_win_rates(venue_rates: pd.DataFrame, colors: dict) -> go.Figure:
    """
    Grouped bar chart showing Bat First Win% vs Field First Win% per venue.
    Uses win-rate percentages rather than raw counts for analytical correctness.
    """
    fig = go.Figure()
    fig.add_bar(
        name="Bat First Win%",
        x=venue_rates.index,
        y=venue_rates["Bat First Win%"],
        marker_color=colors["primary"],
        hovertemplate="%{x}<br>Bat First: %{y:.1f}%<extra></extra>",
    )
    fig.add_bar(
        name="Field First Win%",
        x=venue_rates.index,
        y=venue_rates["Field First Win%"],
        marker_color=colors["secondary"],
        hovertemplate="%{x}<br>Field First: %{y:.1f}%<extra></extra>",
    )
    fig.update_layout(
        **_base_layout(
            colors,
            barmode="group",
            xaxis_tickangle=-35,
            yaxis_title="Win Rate (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
    )
    return fig


def fig_season_trends(season_rates: pd.DataFrame, colors: dict) -> go.Figure:
    fig = px.line(
        season_rates,
        x="season",
        y="win_rate",
        color="team",
        markers=True,
        labels={"season": "Season", "win_rate": "Win Rate (%)", "team": "Team"},
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_layout(
        **_base_layout(
            colors,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
    )
    return fig
