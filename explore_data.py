import pandas as pd
import os
import glob

# Load all ball-by-ball files (exclude _info files)
all_files = glob.glob("data/*.csv")
ball_by_ball_files = [f for f in all_files if "_info" not in f]

print(f"Loading {len(ball_by_ball_files)} match files...")

df = pd.concat(
    [pd.read_csv(f) for f in ball_by_ball_files],
    ignore_index=True
)

print(f"Total deliveries: {len(df):,}")

# Fix: convert season to string before sorting
print(f"Seasons: {sorted(df['season'].astype(str).unique())}")
print(f"Unique batters: {df['striker'].nunique()}")
print(f"Unique bowlers: {df['bowler'].nunique()}")
print(f"Unique venues:  {df['venue'].nunique()}")

# Preview the key columns we'll use
print("\nSample data:")
print(df[['season', 'striker', 'bowler', 'runs_off_bat',
          'wicket_type', 'player_dismissed']].head(10))