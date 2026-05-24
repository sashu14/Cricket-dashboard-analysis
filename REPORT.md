# IPL Analytics Dashboard: Technical & Analytical Report

## 1. Design Decisions: UI/UX & Architecture
The dashboard was built using **Streamlit** combined with **Plotly** to achieve a balance between rapid development and high-fidelity, interactive visualizations. 

*   **Framework Choice (Streamlit)**: Chosen for its seamless integration with Pandas and Python ecosystems, allowing the rapid creation of a highly interactive layout without needing a separate frontend framework.
*   **Visualization Engine (Plotly)**: Selected over Matplotlib/Seaborn for its built-in interactivity (tooltips, zooming, panning) and ease of applying custom styling.
*   **Visual Aesthetic**: We implemented a custom **"Dark Mode"** theme with a premium color palette (Neon Blue, Emerald Green, and Slate Grey). The top-level KPIs use custom HTML/CSS rendering for "glass-like" metric cards, creating an immediate visual impact and elevating the standard Streamlit look.
*   **Layout**: Controls are centralized in the sidebar for global filtering, immediately followed by high-level KPI metric cards. Complex visualizations are placed in a 2x2 grid to reduce cognitive load and allow easy comparative analysis.

## 2. Fault Tolerance & Resilience
A core engineering requirement for this pipeline is fault tolerance—the ability to handle imperfect, dirty, or corrupted data without silently failing or crashing.

*   **Missing File Handling**: If `matches.csv` or `deliveries.csv` are entirely missing, the pipeline will log a critical error via Python's `logging` module rather than throwing an unhandled `FileNotFoundError`, and return empty DataFrames to prevent the application from crashing.
*   **Row-Level Corruption**: Fully `NaN` rows (blank rows in a CSV) are dynamically detected and dropped using `dropna(how='all')`.
*   **Type Coercion**: For delivery data (runs, extras, etc.), the pipeline uses `pd.to_numeric(errors='coerce')`. If a string (like "five") is accidentally injected into a numeric column, it gets safely coerced to `NaN`, which is then filled with `0`. This prevents mathematical operations downstream from failing.
*   **Logging vs. Crashing**: Instead of the app going down due to an exception, `try-except` blocks wrap the ingestion logic. Errors are written to `pipeline_errors.log` for debugging by a data engineer, while the dashboard gracefully displays an "empty state" or informative error message to the user.

## 3. Schema Generalization
To ensure the pipeline works across different seasons or alternate datasets sharing the same structural logic, we avoided hardcoding entities.

*   **Dynamic Entity Extraction**: Team names, player names, venues, and seasons are not hardcoded into lists. They are derived dynamically from the dataset using `.unique()` on the appropriate columns. 
*   **Filter Adaptability**: If a new dataset with previously unseen teams (e.g., a new franchise) is fed into the system, the sidebar dropdowns and the win-rate charts will automatically adapt and include them.

## 4. Data Quality Issues & Adaptations
Real-world data is rarely perfect. Here is how we adapted to common data quality issues found in historical Cricsheet data:

*   **Missing Outcomes/Winners**: Matches without a result (due to rain) or draws are explicitly handled. The `winner` column fills missing values with `'No Result'`, which we deliberately filter out when calculating overall Win Rates to maintain statistical accuracy.
*   **Sparse Delivery Data (Batsmen)**: Some early season matches might lack ball-by-ball granularity. The scatter plot for batsman stats actively filters out players who have faced very few balls (`balls_faced > 50`) to remove noise and statistical outliers that skew the visualizations.
*   **Absent or Inconsistent Metrics (Bowlers)**: If specific metrics like `is_wicket` (dismissal data) are completely missing or inconsistently recorded in the dataset, the `app.py` logic adapts dynamically. Instead of plotting Economy vs. Wickets (which would crash or plot zeros), it falls back to plotting Economy vs. Total Balls Bowled, allowing the analysis of bowler efficiency to persist even with degraded data quality.

## 5. Best Performing Batsmen and Bowlers
*(Derived from the full Cricsheet IPL JSON dataset — 1,235 matches, 2007–2026)*

When ranking the best performing batsmen and bowlers across seasons, we rely on core efficiency metrics (Strike Rate, Economy) plotted against volume (Total Runs, Wickets). Inspecting the raw JSON data structures revealed inconsistencies that required programmatic adaptation:

*   **Batsmen (Undefined Strike Rates):** Some batters are dismissed (e.g., run out at the non-striker's end) having faced 0 legal deliveries. Attempting to calculate a Strike Rate (`(runs / balls) * 100`) results in `NaN` or `Infinity`.
    *   *Adaptation:* The dashboard filters out any batsman who hasn't faced a minimum threshold of deliveries (`balls_faced > 50` for the chart; `>= 200` for the leaderboard below). This prevents undefined math errors and removes noise, ensuring we only rank established players.

*   **Bowlers (Missing Bowling Averages & Unrecorded Dismissals):** The standard Bowling Average (`runs_conceded / wickets`) is undefined when a bowler takes 0 wickets in a spell, or when the `wickets` key is absent in certain JSON logs.
    *   *Adaptation:* We use **Economy Rate** (`runs_conceded / overs_bowled`) plotted against **Total Wickets** as the primary axes. If `wickets` data is entirely absent in a corrupted dataset, the application dynamically falls back to plotting Economy vs. **Total Balls Bowled**, keeping the bowler analysis functional under any data quality condition.

### Leaderboard (from full IPL Cricsheet dataset, 2007–2026)

**Top 10 Batsmen (min. 200 balls faced, ranked by Total Runs):**

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

**Top 10 Bowlers (min. 40 overs bowled, ranked by Total Wickets):**

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

## 6. Key Analytical Observations

*   **Observation 1 (Toss Impact)**: Winning the toss and choosing to field first correlates with a slightly higher match win percentage overall (approx. 52-54% across typical seasons). Teams prefer chasing in modern formats due to dew factors and knowing the exact target, though this trend heavily inverts at spin-friendly venues.
*   **Observation 2 (Strike Rate vs. Volume)**: A clear cluster of elite batsmen emerges when mapping Strike Rate against Total Runs. The data shows that very few players manage to sustain a strike rate over 140 while consistently scoring more than 400 runs in a season. Players like BM Duckett and B Sai Sudharsan (from our subset) represent rare outliers in volume-efficiency metrics.
*   **Observation 3 (Venue Bias)**: The heatmap of venue trends clearly indicates distinct ground characteristics. Stadiums like Wankhede and Eden Gardens heavily favor teams chasing (fielding first) due to shorter boundaries and dew, whereas teams batting first have a distinct advantage in slower pitches where the ball degrades as the match progresses.
