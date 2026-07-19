import random

import pandas as pd
import numpy as np

SOURCE_PATH = ".data/archive/fifa_world_cup_2026_player_performance.csv"
OUTPUT_PATH = "./data.csv"
N_ITERATIONS = 100
N_BINS = 5

df = pd.read_csv(SOURCE_PATH)

numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
categorical_columns = df.select_dtypes(exclude=np.number).columns.tolist()

new_features = {}

for i in range(1, N_ITERATIONS + 1):
    col_a, col_b = random.sample(df.columns.tolist(), 2)

    a_is_numeric = col_a in numeric_columns
    b_is_numeric = col_b in numeric_columns

    if a_is_numeric and b_is_numeric:
        new_features[f"feat_{i}"] = df[col_a] + df[col_b]
    elif not a_is_numeric and not b_is_numeric:
        new_features[f"feat_{i}"] = df[col_a].astype(str) + df[col_b].astype(str)
    else:
        continue

feat_df = pd.DataFrame(new_features, index=df.index)

for col in feat_df.columns:
    if pd.api.types.is_numeric_dtype(feat_df[col]):
        binned = pd.qcut(feat_df[col], q=N_BINS, duplicates="drop")
        codes = binned.cat.codes
        feat_df[col] = ["Q" + str(c + 1) for c in codes]

result = pd.concat([df, feat_df], axis=1)
result.to_csv(OUTPUT_PATH, index=False)

print(f"Generated {len(new_features)} new feature(s) out of {N_ITERATIONS} iterations.")
print(f"Saved to {OUTPUT_PATH} with shape {result.shape}.")
