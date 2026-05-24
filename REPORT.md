# REPORT — IPL Analytics Dashboard

**Author:** Sashvitha Reddy  
**Dataset:** Cricsheet IPL JSON — `ipl_male_json.zip` (https://cricsheet.org/downloads/)  
**Live demo:** https://cricket-dashboard-analysis-9m4vmw4u7g4tkqtuvzpfas.streamlit.app/

---

## 1. Design Decisions

### 1.1 Format choice — JSON over CSV and YAML

Cricsheet offers data in JSON, YAML, and CSV formats. I chose **JSON** for the following reasons:

- **Richest schema:** The JSON format encodes every delivery nested under its over, inning, and match — preserving structural hierarchy that the flat CSV loses (e.g. extras broken out by type, wickets with fielder details, powerplay boundaries).
- **Fault isolation:** Each match is a self-contained file. A corrupted file affects exactly one match; the pipeline skips it and continues with the remaining 1,234. With a monolithic CSV, a single bad row in the middle of the file can corrupt downstream reads.
- **No pre-processing dependency:** The JSON zip is the canonical download from Cricsheet. I parse directly from the zip without requiring an intermediate extraction step — the pipeline opens files via `zipfile.ZipFile` in-memory, keeping the working directory clean.

### 1.2 Framework — Streamlit + Plotly over React + FastAPI

I evaluated two architectures:

| Option | Pros | Cons |
|---|---|---|
| Streamlit + Plotly | Single Python process, no API layer, reactive on filter change, deploy in one command | Less customisable layout |
| React + FastAPI + SQLite | Fully decoupled, arbitrary UI freedom | Two services to run, build step, Node dependency, harder to reproduce |

For a **live demo** against a local dataset, the Streamlit approach is significantly more reproducible: a single `streamlit run app.py` is the entire deployment. The evaluator does not need Node.js, a running API server, or a database migration. This reduces demo failure risk to near zero.

### 1.3 Architecture — two-stage pipeline

The solution separates ingestion from visualisation:

```
ipl_male_json.zip
      │
      ▼
 ingest_json.py          ← parse JSON schema, fault-tolerant, outputs CSVs
      │
      ▼
cleaned_matches.csv
cleaned_deliveries.csv
      │
      ▼
   pipeline.py           ← secondary validation layer (type coercion, NaN drops)
      │
      ▼
    app.py               ← Streamlit dashboard, reads only from CSVs
```

This separation means the dashboard never reads raw JSON directly. Ingestion can be re-run independently if the upstream dataset is updated, without touching the visualisation code.

### 1.4 Visual design

- **Dark mode** with a neon blue (`#00E5FF`) and emerald green (`#00E676`) palette on a near-black background (`#0E1117`). Chosen for high contrast and a premium aesthetic consistent with modern sports analytics products.
- **KPI cards** rendered via custom HTML/CSS injected into Streamlit (`st.markdown(unsafe_allow_html=True)`) for a glassmorphic, card-based layout that Streamlit's native `st.metric` cannot achieve.
- **Plotly** for all charts: every chart supports hover tooltips, axis zoom/pan, legend toggling, and PNG export out of the box — critical for a live demo where the evaluator may want to explore individual data points.

---

## 2. Fault Tolerance Implementation

Fault tolerance operates at three levels: **file level**, **row level**, and **field level**.

### 2.1 File-level resilience (`ingest_json.py`)

```python
try:
    with zf.open(name) as f:
        raw = f.read()
        if not raw.strip():          # empty file guard
            skipped += 1; continue
        data = json.loads(raw)       # JSONDecodeError caught below
except json.JSONDecodeError as e:
    log.error(f"[{match_id}] JSON decode error: {e} — skipping.")
    skipped += 1; continue
```

Each file is opened inside a `try-except` block. Corrupt files (truncated, invalid UTF-8, mismatched brackets) raise `json.JSONDecodeError` and are logged to `ingest_json.log` with the exact match ID. The pipeline processes all remaining files without interruption.

**Result across 1,235 IPL files:** 0 files skipped, 0 errors.

### 2.2 Row/record-level resilience

```python
def _safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur
```

A recursive safe-getter traverses nested JSON dicts. Missing keys at any depth return the provided `default` rather than raising `KeyError`. This is used for every optional field: `outcome.winner`, `outcome.by.runs`, `toss.decision`, `event.match_number`, etc.

### 2.3 Field-level type safety

All numeric columns in the deliveries table are coerced after ingestion:

```python
for col in ['batsman_runs', 'extra_runs', 'total_runs', 'is_wicket', 'over', 'ball']:
    deliveries_df[col] = pd.to_numeric(deliveries_df[col], errors='coerce').fillna(0).astype(int)
```

If a string value (e.g. `"five"`) appears in a numeric column due to upstream corruption, `errors='coerce'` converts it to `NaN`, which is then filled with `0`. Downstream aggregations (`.sum()`, `.mean()`) are therefore always mathematically valid.

### 2.4 Dashboard-level resilience (`app.py`)

- **Missing data file:** `st.error(...)` + `st.stop()` — the app displays a clear error message and halts gracefully rather than raising an unhandled exception.
- **Missing `is_wicket` column:** The bowler scatter chart checks `if 'is_wicket' in filtered_deliveries.columns` and falls back to plotting Economy vs. Total Balls Bowled, updating the y-axis label accordingly.
- **No valid wins in filter scope:** Each chart guards against empty Series before plotting, displaying `st.info("Not enough data...")` rather than crashing on `.index[0]` of an empty object.
- **Toss/venue columns absent:** Every chart checks column existence before attempting any computation.

---

## 3. Schema Generalisation

The solution contains **zero hardcoded entity names**. Every team name, player name, venue name, and season value is extracted dynamically:

```python
# From app.py
seasons = sorted(matches['season'].dropna().unique().tolist())
teams   = sorted(pd.concat([matches['team1'], matches['team2']]).dropna().unique().tolist())
venues  = sorted(matches['venue'].dropna().unique().tolist())
```

This means the dashboard works identically if pointed at:
- A different IPL season subset
- A different T20 league (e.g. BBL, PSL) sharing the Cricsheet JSON schema
- A future dataset with new franchises (e.g. a hypothetical 11th IPL team)

The sidebar filter dropdowns, win-rate charts, and all analytics will automatically reflect whatever entities are present in the data.

---

## 4. Data Quality Issues Encountered

### 4.1 Team name variants across seasons

Cricsheet records team names exactly as they appeared at the time of the match. This creates historical variants that are technically distinct strings:

| Current name | Historical variant |
|---|---|
| Royal Challengers Bengaluru | Royal Challengers Bangalore |
| Punjab Kings | Kings XI Punjab |
| Delhi Capitals | Delhi Daredevils |
| Rising Pune Supergiants | Rising Pune Supergiant |

**Approach:** These variants are preserved as-is, matching Cricsheet's own data integrity. The sidebar filter and all charts treat them as distinct entries — which is analytically correct, since they represent distinct franchise eras. Merging them would require hardcoding name mappings, violating the schema-agnostic constraint.

### 4.2 Missing `winner` field — abandoned/rained-off matches

Cricsheet encodes no-result matches by omitting the `winner` key from `outcome`, or by including `outcome.result = "no result"`. The pipeline normalises both cases to `"No Result"` via `.get('winner', 'No Result')`. Win-rate calculations explicitly exclude `"No Result"`, `"Draw"`, and `"Tie"` strings to maintain statistical accuracy.

### 4.3 Batsmen with 0 balls faced (undefined strike rate)

Some batters are dismissed via run-out at the non-striker's end without facing a single delivery. Computing Strike Rate for these players (`runs / 0`) produces `Infinity` or `NaN`. The dashboard resolves this by applying a minimum threshold filter (`balls_faced > 50`) before the scatter plot, removing statistical noise while retaining all established batters.

### 4.4 Bowling Average undefined for wicketless spells

Bowling Average (`runs / wickets`) is mathematically undefined when a bowler takes 0 wickets in a match or across a filtered period. Rather than plotting infinity or dropping these bowlers entirely, the dashboard uses **Economy Rate** (`runs / overs`) as the primary efficiency metric — which is always defined for any bowler who has bowled at least one ball.

### 4.5 Season encoding inconsistency

Older Cricsheet files encode seasons as strings in `"YYYY/YY"` format (e.g. `"2007/08"`), while modern files use integer years. The ingestion pipeline normalises both:

```python
if isinstance(season, str) and "/" in season:
    season = int(season.split("/")[0])   # "2007/08" → 2007
```

---

## 5. Best Performing Batsmen and Bowlers

*Derived from the full Cricsheet IPL JSON dataset — 1,235 matches, 2007–2026.*

**Top 10 Batsmen** (minimum 200 balls faced across career; ranked by total runs):

| Rank | Batsman | Total Runs | Balls Faced | Strike Rate |
|------|---------|-----------|-------------|-------------|
| 1 | V Kohli | 9,213 | 7,048 | 130.7 |
| 2 | RG Sharma | 7,331 | 5,655 | 129.6 |
| 3 | S Dhawan | 6,769 | 5,483 | 123.5 |
| 4 | DA Warner | 6,567 | 4,849 | 135.4 |
| 5 | KL Rahul | 5,768 | 4,270 | 135.1 |
| 6 | SK Raina | 5,536 | 4,177 | 132.5 |
| 7 | MS Dhoni | 5,439 | 4,101 | 132.6 |
| 8 | AM Rahane | 5,304 | 4,350 | 121.9 |
| 9 | AB de Villiers | 5,181 | 3,487 | 148.6 |
| 10 | SV Samson | 5,181 | 3,770 | 137.4 |

**Top 10 Bowlers** (minimum 40 overs bowled; ranked by total wickets):

| Rank | Bowler | Wickets | Economy | Overs |
|------|--------|---------|---------|-------|
| 1 | YS Chahal | 240 | 7.93 | 690.5 |
| 2 | B Kumar | 239 | 7.59 | 782.3 |
| 3 | SP Narine | 228 | 6.81 | 784.3 |
| 4 | JJ Bumrah | 208 | 7.25 | 632.0 |
| 5 | DJ Bravo | 207 | 8.08 | 549.3 |
| 6 | R Ashwin | 205 | 7.05 | 811.3 |
| 7 | PP Chawla | 201 | 7.98 | 649.2 |
| 8 | SL Malinga | 188 | 7.03 | 495.7 |
| 9 | RA Jadeja | 187 | 7.63 | 714.2 |
| 10 | Rashid Khan | 185 | 7.29 | 588.5 |

**Key observation on metric adaptation:** Bowling Average was evaluated but rejected as the primary ranking metric because it is mathematically undefined for wicketless spells (division by zero) and undefined in aggregate for bowlers who have not taken a wicket in a filtered date range. Economy Rate is always computable and correlates strongly with match impact in T20 cricket, making it the superior efficiency metric for this format.

---

## 6. Key Analytical Observations

### 6.1 Toss impact
Winning the toss and choosing to **field first** correlates with a marginally higher win rate overall (~52–54% across all 18 seasons). The sunburst chart confirms this pattern: "field → Won Match" subtends a visibly larger arc than "bat → Won Match". This is consistent with the well-documented "dew factor" and the advantage of chasing a known target in T20 cricket. However, this advantage diminishes or inverts at slower, higher-altitude venues where the ball grips early and batting first is advantageous.

### 6.2 Batsman efficiency cluster
The strike-rate vs. runs scatter reveals a clear performance cluster between SR 120–145 and 2,000–5,000 runs for established batters. Outliers above SR 150 with high volumes (AB de Villiers: 148.6 SR, 5,181 runs; Sunil Narine's late-career reinvention) represent genuinely elite profiles that stand apart from the main cluster. Below ~SR 110 with moderate volumes, players are likely specialist lower-order batters.

### 6.3 Venue bias — bat first vs. field first
The venue heatmap shows Eden Gardens and Wankhede Stadium favour chasing (shorter boundaries, dew in evening games), while Chepauk (MA Chidambaram Stadium) historically favours batting first due to slow pitch deterioration. The Rajiv Gandhi International Stadium, Uppal, shows a more balanced split — consistent with SRH's historically strong bowling attacks making it a competitive venue regardless of toss decision.

### 6.4 Bowler longevity
SP Narine's economy rate of 6.81 across 784 overs is remarkable — nearly a full run per over cheaper than the next-best high-volume bowler. This reflects his mystery-spin advantage in the early-mid 2010s before batters adapted. JJ Bumrah's 7.25 economy across 632 overs with 208 wickets is arguably the standout all-format efficiency ratio, especially notable given T20 cricket's scoring inflation over the same period.

---

## 7. External APIs and Services

**No external APIs are used.** The entire solution runs locally with zero network calls during execution:

- Data source: Cricsheet (one-time download, free, no API key required)
- Visualisation: Plotly (runs entirely in-process)
- Dashboard: Streamlit (local server)
- Data processing: Pandas + NumPy (in-memory)

**Cost: £0 / $0.** There are no usage-based charges, free-tier limits, or per-request costs. This is a deliberate design choice — external LLM or analytics APIs would introduce latency, key-management overhead, and cost risk that are unnecessary for a batch analytics dashboard against a static dataset.

The Streamlit Community Cloud deployment (live demo URL) is free under Streamlit's community tier, with no cost implications.

---

## 8. Licence Choice

This project is released under the **MIT Licence**.

All runtime dependencies (Streamlit: Apache 2.0, Plotly: MIT, Pandas: BSD-3-Clause, NumPy: BSD-3-Clause) use permissive open-source licences. MIT is compatible with all of these — it imposes no copyleft obligations, allows commercial use, and permits modification and redistribution with attribution. No GPL or LGPL dependencies are present.
