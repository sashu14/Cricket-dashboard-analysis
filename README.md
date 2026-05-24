# IPL Analytics Dashboard 🏏

An end-to-end, fault-tolerant analytics dashboard for the Indian Premier League built on the official [Cricsheet](https://cricsheet.org/) IPL dataset. The pipeline ingests 1,235 real match JSON files, transforms them into clean tabular data, and serves 6 interactive visualizations via Streamlit.

---

## 🌟 Features

- **Real Cricsheet Data** — 1,235 IPL matches (2007–2026), 293,764 ball-by-ball deliveries, 18 seasons, 19 teams
- **Fault-Tolerant JSON Pipeline** — handles malformed JSON, missing fields, type errors, and empty files without crashing
- **Schema-Agnostic Design** — no hardcoded team/player/venue names; all entities extracted dynamically
- **6 Interactive Visualizations** — win rates, toss impact, venue heatmap, batsman scatter, bowler scatter, seasonal trends
- **Global Filters** — sidebar filters for Season, Team, and Venue update all charts reactively

---

## 📊 Dataset

| Property | Value |
|---|---|
| **Source** | [Cricsheet IPL JSON](https://cricsheet.org/downloads/) — `ipl_male_json.zip` |
| **Format** | Cricsheet JSON (one file per match) |
| **Matches** | 1,235 |
| **Deliveries** | 293,764 |
| **Seasons** | 2007–2026 (18 seasons) |
| **Teams** | 19 (incl. defunct franchises: Deccan Chargers, Kochi Tuskers, Pune Warriors) |
| **Wickets recorded** | 14,601 |

> The zip file is not committed to this repository due to its size (~89 MB).
> Download it from https://cricsheet.org/downloads/ and run `python ingest_json.py` to regenerate the CSVs.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Dashboard | Python 3.8+, Streamlit |
| Visualizations | Plotly (interactive charts) |
| Data Processing | Pandas, NumPy |
| Ingestion Pipeline | Python `zipfile`, `json`, `logging` |

---

## 🛡️ Fault Tolerance

| Scenario | Handling |
|---|---|
| Missing JSON file | Logged, skipped — pipeline continues |
| Invalid JSON (decode error) | Caught via `json.JSONDecodeError`, file skipped |
| Missing `winner` / outcome fields | Defaults to `"No Result"` via `.get()` |
| Missing `is_wicket` / wickets data | Dashboard falls back to plotting balls bowled |
| Malformed numeric fields | `pd.to_numeric(errors='coerce').fillna(0)` |
| Fully NaN rows | Dropped via `dropna(how='all')` |
| Division-by-zero (strike rate) | Players with `balls_faced < 50` filtered out |

---

## 🚀 Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate clean data from Cricsheet JSON
```bash
# Download ipl_male_json.zip from https://cricsheet.org/downloads/
# Then run:
python ingest_json.py ipl_male_json.zip
```
This creates `cleaned_matches.csv` and `cleaned_deliveries.csv`.

> **Skip this step** — pre-built CSVs from the real Cricsheet dataset are already committed to this repo.

### 3. Launch the dashboard
```bash
streamlit run app.py
```
Open **http://localhost:8501** in your browser.

---

## 📁 Project Structure

```
Cricket-dashboard-analysis/
├── app.py                  # Streamlit dashboard (6 charts + KPI cards)
├── ingest_json.py          # Fault-tolerant JSON → CSV pipeline
├── pipeline.py             # CSV cleaning & validation pipeline
├── cleaned_matches.csv     # 1,235 real IPL matches (2007–2026)
├── cleaned_deliveries.csv  # 293,764 real ball-by-ball deliveries
├── requirements.txt        # Python dependencies
├── REPORT.md               # Design decisions, adaptations & observations
└── README.md
```

---

## 📜 License

This project is open-sourced under the MIT License. See `LICENSE` for details.
