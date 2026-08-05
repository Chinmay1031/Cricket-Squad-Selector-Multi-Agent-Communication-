import pandas as pd
import glob

def load_data():
    files = [f for f in glob.glob("data/*.csv") if "_info" not in f]
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["season"] = df["season"].astype(str)
    return df

def build_batting_stats(df):
    recent = df[df["season"].isin(["2022", "2023", "2024", "2025", "2026"])]

    balls = (
        recent[recent["wides"].isna()]
        .groupby("striker").size()
        .rename("balls_faced")
        .reset_index()
        .rename(columns={"striker": "player"})
    )
    runs = (
        recent.groupby("striker")["runs_off_bat"].sum()
        .rename("runs")
        .reset_index()
        .rename(columns={"striker": "player"})
    )
    dismissals = (
        recent[recent["player_dismissed"].notna()]
        .groupby("player_dismissed").size()
        .rename("dismissals")
        .reset_index()
        .rename(columns={"player_dismissed": "player"})
    )

    batting = runs.merge(balls, on="player").merge(dismissals, on="player", how="left")
    batting["dismissals"] = batting["dismissals"].fillna(0)
    batting["batting_avg"] = (batting["runs"] / batting["dismissals"].replace(0, 1)).round(1)
    batting["strike_rate"] = ((batting["runs"] / batting["balls_faced"]) * 100).round(1)
    batting = batting[batting["balls_faced"] >= 100].copy()
    return batting

def build_bowling_stats(df):
    recent = df[df["season"].isin(["2022", "2023", "2024", "2025", "2026"])]

    legal = recent[recent["wides"].isna() & recent["noballs"].isna()]
    balls_bowled = (
        legal.groupby("bowler").size()
        .rename("balls_bowled")
        .reset_index()
        .rename(columns={"bowler": "player"})
    )
    runs_off_bat = (
        recent.groupby("bowler")["runs_off_bat"].sum()
        .reset_index()
        .rename(columns={"bowler": "player"})
    )
    extras = (
        recent.groupby("bowler")["extras"].sum()
        .reset_index()
        .rename(columns={"bowler": "player"})
    )
    wickets = (
        recent[
            recent["wicket_type"].notna() &
            ~recent["wicket_type"].isin(["run out", "retired hurt", "obstructing the field"])
        ]
        .groupby("bowler").size()
        .rename("wickets")
        .reset_index()
        .rename(columns={"bowler": "player"})
    )

    bowling = balls_bowled.merge(runs_off_bat, on="player").merge(extras, on="player", how="left")
    bowling["runs_conceded"] = bowling["runs_off_bat"] + bowling["extras"].fillna(0)
    bowling = bowling.merge(wickets, on="player", how="left")
    bowling["wickets"] = bowling["wickets"].fillna(0)
    bowling["economy"] = ((bowling["runs_conceded"] / bowling["balls_bowled"]) * 6).round(2)
    bowling = bowling[bowling["balls_bowled"] >= 60].copy()
    return bowling[["player", "balls_bowled", "runs_conceded", "wickets", "economy"]]

def compute_credits(pool):
    """
    Credits range: 8.0 to 10.5 for all players.
    Batters  : higher avg + higher SR = higher credits.
    Bowlers  : lower economy + more wickets = higher credits.
    AR       : blend of batting and bowling scores.
    """
    pool = pool.copy()
    pool["credits"] = 8.0

    # ── Batters ──────────────────────────────────────────────────────────────
    bat = pool["role"] == "BAT"
    bat_df = pool[bat].copy()
    bat_df["score"] = (
        bat_df["batting_avg"].rank(pct=True) * 0.5 +
        bat_df["strike_rate"].rank(pct=True) * 0.5
    )
    ranked = bat_df["score"].rank(pct=True)
    pool.loc[bat, "credits"] = (ranked * 2.5 + 8.0).round(1).clip(8.0, 10.5)

    # ── Bowlers ──────────────────────────────────────────────────────────────
    bowl = pool["role"] == "BOWL"
    bowl_df = pool[bowl].copy()
    # Replace 0 economy with penalty so unproven bowlers rank low
    bowl_df["economy_safe"] = bowl_df["economy"].replace(0, 99)
    bowl_df["inv_economy"]  = (1 / bowl_df["economy_safe"]).rank(pct=True)
    bowl_df["wickets_rank"] = bowl_df["wickets"].rank(pct=True)
    bowl_df["score"] = (
        bowl_df["inv_economy"]  * 0.6 +   # lower economy = better
        bowl_df["wickets_rank"] * 0.4     # more wickets = better
    )
    ranked = bowl_df["score"].rank(pct=True)
    pool.loc[bowl, "credits"] = (ranked * 2.5 + 8.0).round(1).clip(8.0, 10.5)

    # ── All-rounders ─────────────────────────────────────────────────────────
    ar = pool["role"] == "AR"
    ar_df = pool[ar].copy()
    ar_df["economy_safe"] = ar_df["economy"].replace(0, 99)
    ar_df["inv_economy"]  = (1 / ar_df["economy_safe"]).rank(pct=True)
    ar_df["score"] = (
        ar_df["strike_rate"].rank(pct=True) * 0.3 +
        ar_df["batting_avg"].rank(pct=True) * 0.2 +
        ar_df["inv_economy"]                * 0.3 +
        ar_df["wickets"].rank(pct=True)     * 0.2
    )
    ranked = ar_df["score"].rank(pct=True)
    pool.loc[ar, "credits"] = (ranked * 2.5 + 8.0).round(1).clip(8.0, 10.5)

    return pool

def inject_star_players():
    """
    Manually add globally recognised players with accurate recent T20/IPL stats.
    These override the data-driven pool for star players.
    """
    stars = [
        # name,                  role,  credits, avg,   sr,     eco,   wkts
        # ── Top batters ──────────────────────────────────────────────────────
        ("V Kohli",              "BAT", 10.5,   47.7,  144.8,  0.0,    0),
        ("Suryakumar Yadav",     "BAT", 10.5,   46.4,  187.4,  0.0,    0),
        ("Yashasvi Jaiswal",     "BAT", 10.5,   39.8,  162.4,  0.0,    0),
        ("RG Sharma",            "BAT", 10.0,   30.2,  140.3,  0.0,    0),
        ("Shubman Gill",         "BAT", 10.0,   45.6,  151.1,  0.0,    0),
        ("Ruturaj Gaikwad",      "BAT", 10.0,   40.2,  145.6,  0.0,    0),
        ("KL Rahul",             "BAT",  9.5,   38.5,  135.2,  0.0,    0),
        ("DA Warner",            "BAT",  9.5,   36.0,  138.8,  0.0,    0),
        ("MS Dhoni",             "BAT",  9.5,   35.2,  145.6,  0.0,    0),
        ("Q de Kock",            "BAT",  9.0,   32.4,  136.5,  0.0,    0),
        ("SPD Smith",            "BAT",  9.0,   35.1,  125.4,  0.0,    0),
        ("JE Root",              "BAT",  9.0,   33.8,  128.2,  0.0,    0),
        ("Liam Livingstone",     "BAT",  9.0,   28.6,  158.4,  0.0,    0),
        ("Glenn Maxwell",        "BAT",  9.0,   26.4,  162.8,  0.0,    0),
        # ── Top bowlers ──────────────────────────────────────────────────────
        ("JJ Bumrah",            "BOWL", 10.5,   0.0,    0.0,   6.2,   56),
        ("Rashid Khan",          "BOWL", 10.0,   0.0,    0.0,   6.5,   40),
        ("Varun Chakaravarthy",  "BOWL",  9.5,   0.0,    0.0,   7.2,   35),
        ("Arshdeep Singh",       "BOWL",  9.5,   0.0,    0.0,   7.8,   32),
        ("Mohammed Shami",       "BOWL",  9.5,   0.0,    0.0,   7.6,   25),
        ("Mohammed Siraj",       "BOWL",  9.0,   0.0,    0.0,   8.1,   28),
        ("YS Chahal",            "BOWL",  9.0,   0.0,    0.0,   7.9,   30),
        ("Avesh Khan",           "BOWL",  8.5,   0.0,    0.0,   8.4,   22),
        ("T Natarajan",          "BOWL",  8.5,   0.0,    0.0,   8.2,   18),
        ("SL Malinga",           "BOWL",  9.0,   0.0,    0.0,   7.1,   30),
        # ── Top all-rounders ─────────────────────────────────────────────────
        ("RA Jadeja",            "AR",   10.5,   32.2,  136.1,  7.2,   51),
        ("Abhishek Sharma",      "AR",   10.0,   32.1,  175.6,  8.9,    4),
        ("Andre Russell",        "AR",   10.0,   29.5,  178.2,  8.7,   25),
        ("SP Narine",            "AR",    9.5,   22.1,  180.4,  6.8,   28),
        ("KH Pandya",            "AR",    9.5,   26.2,  142.1,  8.4,   52),
        ("BA Stokes",            "AR",    9.5,   28.4,  138.6,  8.9,   18),
        ("Glenn Maxwell",        "AR",    9.5,   26.4,  162.8,  8.2,   20),
        ("Axar Patel",           "AR",    9.0,   25.4,  138.2,  7.8,   30),
        ("Washington Sundar",    "AR",    8.5,   22.8,  128.4,  7.9,   18),
        ("KA Pollard",           "AR",    8.5,   24.3,  145.2,  9.1,   12),
        ("DM Bravo",             "AR",    8.5,   23.5,  130.1,  8.8,   10),
    ]
    rows = []
    for name, role, credits, avg, sr, eco, wkts in stars:
        rows.append({
            "player":       name,
            "role":         role,
            "credits":      credits,
            "batting_avg":  avg,
            "strike_rate":  sr,
            "balls_faced":  300 if sr > 0 else 0,
            "runs":         0,
            "dismissals":   0,
            "balls_bowled": 200 if eco > 0 else 0,
            "runs_conceded":0,
            "economy":      eco,
            "wickets":      float(wkts)
        })
    return pd.DataFrame(rows)

def build_player_pool():
    print("Loading data...")
    df = load_data()

    print("Building batting stats...")
    batting = build_batting_stats(df)

    print("Building bowling stats...")
    bowling = build_bowling_stats(df)

    pool = batting.merge(bowling, on="player", how="outer")

    def assign_role(row):
        has_bat  = row.get("balls_faced",  0) >= 100
        has_bowl = row.get("balls_bowled", 0) >= 60
        if has_bat and has_bowl:
            return "AR"
        elif has_bat:
            return "BAT"
        else:
            return "BOWL"

    pool["role"] = pool.apply(assign_role, axis=1)

    # Apply new composite credit formula
    pool = compute_credits(pool)

    pool = pool.fillna(0).sort_values("credits", ascending=False).reset_index(drop=True)

    # Inject star players — they take priority over data-driven entries
    stars_df = inject_star_players()
    pool = pd.concat([stars_df, pool], ignore_index=True)
    pool = pool.drop_duplicates(subset="player", keep="first")
    pool = pool.sort_values("credits", ascending=False).reset_index(drop=True)

    print(f"\nPlayer pool: {len(pool)} players")
    print(f"  BAT:  {(pool['role']=='BAT').sum()}")
    print(f"  BOWL: {(pool['role']=='BOWL').sum()}")
    print(f"  AR:   {(pool['role']=='AR').sum()}")
    print(f"\nMin credits: {pool['credits'].min()}")
    print(f"Max credits: {pool['credits'].max()}")
    print("\nTop 20 by credits:")
    print(pool[["player","role","credits","batting_avg",
                "strike_rate","economy","wickets"]].head(20).to_string(index=False))

    return pool

if __name__ == "__main__":
    pool = build_player_pool()
    pool.to_csv("data/player_pool.csv", index=False)
    print("\nSaved to data/player_pool.csv")