# IPL Analytics Dashboard 🏏

> **Live demo:** https://cricket-dashboard-analysis-9m4vmw4u7g4tkqtuvzpfas.streamlit.app/

An end-to-end, fault-tolerant analytics dashboard for the Indian Premier League built entirely on the official [Cricsheet](https://cricsheet.org/) IPL JSON dataset. A single ingestion pipeline reads 1,235 match files directly from a zip archive, transforms them into clean tabular CSVs, and feeds six interactive Plotly visualisations served by Streamlit.

---

## Table of Contents
1. [Features](#features)
2. [Dataset — download & placement](#dataset--download--placement)
3. [Quick start](#quick-start)
4. [Project structure](#project-structure)
5. [Visualisations](#visualisations)
6. [Fault tolerance](#fault-tolerance)
7. [Dependencies & licences](#dependencies--licences)

---

## Features

| Capability | Detail |
|---|---|
| **Real IPL data** | 1,235 matches · 293,764 deliveries · 18 seasons (2007–2026) · 19 teams |
| **Fault-tolerant pipeline** | 0 files skipped across 1,235 JSON inputs; graceful fallback on every edge case |
| **Schema-agnostic** | No hardcoded team/player/venue names; all entities extracted dynamically |
| **Interactive filters** | Sidebar multi-selects for Season, Team, and Venue — all six charts update reactively |
| **6 visualisations** | Win rates · Toss impact · Batsman scatter · Bowler scatter · Venue heatmap · Season trends |
| **Premium UI** | Custom dark-mode theme, neon colour palette, animated KPI cards via Streamlit + Plotly |

---

## Dataset — download & placement

> ⚠️ **Data is not bundled in this archive** (submission size limit). Follow these steps exactly.

### Step 1 — Download

Go to **https://cricsheet.org/downloads/** and download:

```
ipl_male_json.zip   (~89 MB)
```

Direct URL: `https://cricsheet.org/downloads/ipl_male_json.zip`

### Step 2 — Place the file

Copy the downloaded zip into the **project root** (the same folder as `app.py`):

```
Cricket-dashboard-analysis/
├── app.py
├── ingest_json.py
├── ipl_male_json.zip   ← place it here
├── pipeline.py
└── ...
```

### Step 3 — Run ingestion

```bash
python ingest_json.py ipl_male_json.zip
```

This creates two files in the project root:
- `cleaned_matches.csv` — one row per match (1,235 rows)
- `cleaned_deliveries.csv` — one row per delivery (293,764 rows)

Ingestion completes in **under 5 seconds** on a standard laptop.

---

## Quick start

### Prerequisites

- Python **3.8 or later**
- pip

### 1. Clone the repository

```bash
git clone https://github.com/sashu14/Cricket-dashboard-analysis.git
cd Cricket-dashboard-analysis
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download data and run ingestion

Follow the [Dataset section](#dataset--download--placement) above.

### 4. Launch the dashboard

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

> The app caches the CSVs in memory for 1 hour (`@st.cache_data(ttl=3600)`). Pass `--server.port 8502` if 8501 is in use.

---

## Project structure

```
Cricket-dashboard-analysis/
├── app.py                  # Streamlit dashboard — 6 charts + KPI cards + sidebar filters
├── ingest_json.py          # Fault-tolerant JSON → CSV pipeline (primary, used for real data)
├── pipeline.py             # CSV cleaning & validation pipeline (secondary, for pre-existing CSVs)
├── requirements.txt        # Python runtime dependencies
├── README.md               # This file
├── REPORT.md               # Design decisions, fault tolerance, observations
└── LICENSE                 # MIT Licence
```

> `cleaned_matches.csv` and `cleaned_deliveries.csv` are generated outputs — not committed to source control.

---

## Visualisations

| Chart | Type | What it shows |
|---|---|---|
| **KPI Cards** | Custom HTML/CSS | Total matches · Top win-rate team · Top run scorer |
| **Win Rates by Team** | Bar chart | Overall win % per team across selected filters |
| **Toss Impact Analysis** | Sunburst | Toss decision (bat/field) → match outcome (W/L) |
| **Batsmen: Strike Rate vs Runs** | Scatter | Volume vs efficiency for players with ≥ 50 balls faced |
| **Bowlers: Economy vs Wickets** | Scatter | Economy rate vs wickets for bowlers with ≥ 60 balls |
| **Venue Trends (Bat vs Field)** | Heatmap | Bat-first vs field-first win counts at top 12 venues |
| **Win Rates Across Seasons** | Line chart | Per-season win % for the top 5 overall teams |

All charts use Plotly — hover for tooltips, click legend to isolate teams, drag to zoom.

---

## Fault tolerance

| Failure scenario | Handling |
|---|---|
| Missing zip / source file | Logged via `logging`, empty DataFrame returned — app shows informative error, does not crash |
| Invalid / corrupt JSON | `json.JSONDecodeError` caught per file; file skipped, pipeline continues |
| Missing `winner` field | Defaults to `"No Result"` via `.get()`; filtered from win-rate calculations |
| Missing `wickets` key | `is_wicket` = 0; dashboard falls back to Economy vs Balls Bowled axis |
| Malformed numeric fields | `pd.to_numeric(errors='coerce').fillna(0)` — strings coerced safely |
| Fully NaN rows | `dropna(how='all')` applied after ingestion |
| Division by zero (strike rate) | Players with `balls_faced < 50` excluded from scatter |
| Division by zero (bowling avg) | Bowling Average abandoned; Economy Rate used instead |
| Empty dataset after filters | Streamlit `st.stop()` called with informative message |

---

## Dependencies & licences

| Package | Version | Licence |
|---|---|---|
| `streamlit` | ≥ 1.30 | Apache 2.0 |
| `plotly` | ≥ 5.0 | MIT |
| `pandas` | ≥ 1.5 | BSD-3-Clause |
| `numpy` | ≥ 1.23 | BSD-3-Clause |

All dependencies use permissive licences compatible with the **MIT Licence** applied to this project. No proprietary or copyleft dependencies are used. No external paid APIs are called — the entire solution runs locally with zero operational cost.
