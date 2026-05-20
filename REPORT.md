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

## 5. Best performing batsmen and bowlers
*(Derived from `venv/recently_played_30_male_json` dataset analysis)*

When ranking the best performing batsmen and bowlers across seasons, we rely on core efficiency metrics (Strike Rate, Economy) plotted against volume (Total Runs, Wickets). However, inspecting the raw JSON data structures revealed inconsistencies that required programmatic adaptation:
*   **Batsmen (Undefined Strike Rates):** Some batters are dismissed (e.g., run out at the non-striker's end) having faced 0 legal deliveries. Attempting to calculate a Strike Rate (`(runs / balls) * 100`) results in `NaN` or `Infinity`.
    *   *Adaptation:* The dashboard filters out any batsman who hasn't faced a minimum threshold of deliveries (`balls_faced > 50`). This prevents undefined math errors and removes "noise" from the leaderboard, ensuring we only rank established players.
*   **Bowlers (Missing Bowling Averages & Unrecorded Dismissals):** To rank bowlers, the standard metric is Bowling Average (`runs_conceded / wickets`). However, in several matches within the JSON dataset, bowlers complete their spells with 0 wickets, or the `wickets` array in the JSON is empty due to a lack of dismissals. This makes the average mathematically undefined (`Infinity`). Furthermore, some niche JSON logs omit the `wickets` key entirely for certain overs.
    *   *Adaptation:* We abandoned Bowling Average as the primary y-axis. Instead, we adapted the visual analysis to use **Economy Rate** (`runs_conceded / overs_bowled`) plotted against **Total Wickets**. In the event the `wickets` metric is entirely absent from a corrupted dataset, the application dynamically falls back to plotting Economy vs. **Total Balls Bowled**. This ensures the visual ranking of bowler efficiency remains functional regardless of data sparsity.

### Derived Leaderboard (from `recently_played_30_male_json`)
Based on the adaptations above, the pipeline extracted the following actual top performers across all seasons recorded in the JSON dataset:

**Top 5 Batsmen (Ranked by Total Runs):**
1. **BM Duckett**: 477 Runs (Strike Rate: 69.4)
2. **JM Clarke**: 461 Runs (Strike Rate: 53.8)
3. **EN Gay**: 408 Runs (Strike Rate: 64.9)
4. **TB Abell**: 398 Runs (Strike Rate: 48.2)
5. **B Sai Sudharsan**: 388 Runs (Strike Rate: 152.2)

**Top 5 Bowlers (Ranked by Total Wickets):**
1. **BA Raine**: 21 Wickets (Economy: 2.23)
2. **S Lamichhane**: 18 Wickets (Economy: 3.22)
3. **B Kumar**: 18 Wickets (Economy: 6.71)
4. **BW Sanderson**: 17 Wickets (Economy: 2.84)
5. **L Gregory**: 17 Wickets (Economy: 3.11)

## 6. Key Analytical Observations
*(To be filled in post-deployment during the live demo based on the specific dataset fed into the application)*

*   **Observation 1 (Toss Impact)**: [Placeholder - e.g., Winning the toss and choosing to field first correlates with a higher match win percentage overall, but this trend inverts at specific venues like Chepauk.]
*   **Observation 2 (Strike Rate vs. Volume)**: [Placeholder - e.g., A clear cluster of elite batsmen emerges when mapping Strike Rate against Total Runs, showing that very few players manage to sustain a strike rate over 140 while scoring more than 500 runs in a season.]
*   **Observation 3 (Venue Bias)**: [Placeholder - e.g., The heatmap clearly indicates that Wankhede Stadium heavily favors teams chasing (fielding first), whereas teams batting first have a distinct advantage in Chennai.]
