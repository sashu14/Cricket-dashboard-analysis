import os
import json
import pandas as pd

json_dir = 'venv/recently_played_30_male_json'
json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]

batsman_data = []
bowler_data = []

for file in json_files:
    with open(os.path.join(json_dir, file), 'r') as f:
        try:
            data = json.load(f)
            if 'innings' not in data: continue
            for inning in data['innings']:
                if 'overs' not in inning: continue
                for over in inning['overs']:
                    for delivery in over['deliveries']:
                        batter = delivery['batter']
                        bowler = delivery['bowler']
                        runs = delivery['runs']['batter']
                        total_runs = delivery['runs']['total']
                        
                        is_wicket = 0
                        if 'wickets' in delivery:
                            for w in delivery['wickets']:
                                # Exclude run outs for bowler wickets
                                if w.get('kind') not in ['run out', 'retired hurt', 'obstructing the field']:
                                    is_wicket += 1
                        
                        # Batsman
                        batsman_data.append({'batter': batter, 'runs': runs, 'balls': 1})
                        
                        # Bowler
                        is_legal = 1
                        if 'extras' in delivery and ('wides' in delivery['extras'] or 'noballs' in delivery['extras']):
                            is_legal = 0
                        
                        bowler_runs = total_runs
                        if 'extras' in delivery:
                            for ex in ['byes', 'legbyes', 'penalty']:
                                bowler_runs -= delivery['extras'].get(ex, 0)
                                
                        bowler_data.append({
                            'bowler': bowler, 
                            'runs_conceded': bowler_runs, 
                            'balls_bowled': is_legal,
                            'wickets': is_wicket
                        })
        except Exception as e:
            pass

df_bat = pd.DataFrame(batsman_data)
df_bowl = pd.DataFrame(bowler_data)

bat_stats = df_bat.groupby('batter').sum().reset_index()
bat_stats['strike_rate'] = (bat_stats['runs'] / bat_stats['balls']) * 100
bat_stats = bat_stats[bat_stats['balls'] > 50].sort_values(by='runs', ascending=False).head(5)

bowl_stats = df_bowl.groupby('bowler').sum().reset_index()
bowl_stats['overs'] = bowl_stats['balls_bowled'] / 6
bowl_stats['economy'] = bowl_stats['runs_conceded'] / bowl_stats['overs']
bowl_stats = bowl_stats[bowl_stats['overs'] > 10].sort_values(by=['wickets', 'economy'], ascending=[False, True]).head(5)

print("--- TOP BATSMEN ---")
for _, row in bat_stats.iterrows():
    print(f"{row['batter']}: {int(row['runs'])} Runs | {row['strike_rate']:.1f} SR")

print("--- TOP BOWLERS ---")
for _, row in bowl_stats.iterrows():
    print(f"{row['bowler']}: {int(row['wickets'])} Wickets | {row['economy']:.2f} Econ")
