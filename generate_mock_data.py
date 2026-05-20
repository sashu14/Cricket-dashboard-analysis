import pandas as pd
import numpy as np

# Mock Matches Data
np.random.seed(42)

teams = ['Chennai Super Kings', 'Mumbai Indians', 'Royal Challengers Bangalore', 'Kolkata Knight Riders', 'Delhi Capitals', 'Sunrisers Hyderabad']
venues = ['Wankhede Stadium', 'M.Chinnaswamy Stadium', 'Eden Gardens', 'Feroz Shah Kotla', 'Rajiv Gandhi International Stadium']

matches_data = []
for i in range(1, 51):
    t1, t2 = np.random.choice(teams, 2, replace=False)
    toss_winner = np.random.choice([t1, t2])
    toss_decision = np.random.choice(['bat', 'field'])
    winner = np.random.choice([t1, t2])
    
    matches_data.append({
        'id': i,
        'season': np.random.choice(['2021', '2022', '2023']),
        'city': 'Test City',
        'date': f'2022-04-{i%30 + 1:02d}',
        'team1': t1,
        'team2': t2,
        'toss_winner': toss_winner,
        'toss_decision': toss_decision,
        'winner': winner,
        'venue': np.random.choice(venues),
        'player_of_match': f'Player_{np.random.randint(1, 50)}'
    })

matches_df = pd.DataFrame(matches_data)
matches_df.to_csv('matches.csv', index=False)

# Mock Deliveries Data
deliveries_data = []
for match_id in range(1, 51):
    for inning in [1, 2]:
        for over in range(1, 21):
            for ball in range(1, 7):
                batsman = f'Player_{np.random.randint(1, 50)}'
                bowler = f'Player_{np.random.randint(50, 100)}'
                batsman_runs = np.random.choice([0, 1, 2, 3, 4, 6], p=[0.4, 0.3, 0.1, 0.05, 0.1, 0.05])
                extra_runs = np.random.choice([0, 1], p=[0.95, 0.05])
                
                deliveries_data.append({
                    'match_id': match_id,
                    'inning': inning,
                    'over': over,
                    'ball': ball,
                    'batsman': batsman,
                    'bowler': bowler,
                    'batsman_runs': batsman_runs,
                    'extra_runs': extra_runs,
                    'total_runs': batsman_runs + extra_runs
                })

deliveries_df = pd.DataFrame(deliveries_data)
deliveries_df.to_csv('deliveries.csv', index=False)

print("Mock data generated: matches.csv and deliveries.csv")
