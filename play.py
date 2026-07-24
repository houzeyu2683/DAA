import pandas as pd

path = '.data/archive/fifa_world_cup_2026_player_performance.csv'
table = pd.read_csv(path)
print(table.columns.index)