import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_player_pool():
    """Load a balanced pool of top players by role."""
    df = pd.read_csv("data/player_pool.csv")

    # Increased limits so stars like Kohli, Bumrah are included
    batters     = df[df["role"] == "BAT"].head(25)
    bowlers     = df[df["role"] == "BOWL"].head(20)
    allrounders = df[df["role"] == "AR"].head(10)

    pool = pd.concat([batters, bowlers, allrounders]).reset_index(drop=True)
    return pool

def format_pool_for_prompt(pool):
    """Turn the dataframe into a readable string for the prompt."""
    lines = []
    for _, row in pool.iterrows():
        if row["role"] == "BAT":
            lines.append(
                f"{row['player']} | BAT | {row['credits']}cr | "
                f"Avg: {row['batting_avg']} | SR: {row['strike_rate']}"
            )
        elif row["role"] == "BOWL":
            lines.append(
                f"{row['player']} | BOWL | {row['credits']}cr | "
                f"Wickets: {int(row['wickets'])} | Economy: {row['economy']}"
            )
        else:
            lines.append(
                f"{row['player']} | AR | {row['credits']}cr | "
                f"SR: {row['strike_rate']} | Economy: {row['economy']} | "
                f"Wickets: {int(row['wickets'])}"
            )
    return "\n".join(lines)

def pick_team(conditions, pool, previous_critique=None):
    """
    Ask GPT-4o-mini to pick a fantasy XI.
    If previous_critique is provided, it revises based on that feedback.
    """
    pool_text = format_pool_for_prompt(pool)

    system_prompt = f"""You are an expert fantasy cricket selector.
Your job is to pick the best possible fantasy XI from a given player pool within a budget.

Rules:
- Pick exactly 11 players
- Must include: at least 1 wicket-keeper (WK), 3+ batters (BAT), 1+ all-rounder (AR), 3+ bowlers (BOWL)
- Note: WK players are listed as BAT in our pool — pick one batter to be your WK
- Total credits must not exceed 100
- Name 1 captain (2x points) and 1 vice-captain (1.5x points)

Conditions-based guidance:
- Flat pitch → favour explosive batters and all-rounders with high strike rates
- Seaming pitch → favour pace bowlers with good economy, lower batting credits
- Spinning pitch → favour spinners and batters with high averages
- Two-paced pitch → balanced attack, favour all-rounders
- Overcast weather → favour swing bowlers (pace)
- Humid weather → favour spin, ball grips more

Always respond in this EXACT format:
TEAM: [comma-separated list of exactly 11 player names]
CAPTAIN: [one player name]
VICE-CAPTAIN: [one player name]
TOTAL CREDITS: [number]
REASONING: [2-3 sentences explaining why this team suits the conditions]"""

    if previous_critique is None:
        user_prompt = f"""Match conditions:
- Format: {conditions['format']}
- Pitch: {conditions['pitch']}
- Weather: {conditions['weather']}
- Venue: {conditions['venue']}

Available players (Name | Role | Credits | Key stats):
{pool_text}

Budget: 100 credits. Pick your best fantasy XI for these exact conditions.
Make sure your captain and vice-captain are the highest point-scoring picks for this venue and pitch."""

    else:
        user_prompt = f"""Match conditions:
- Format: {conditions['format']}
- Pitch: {conditions['pitch']}
- Weather: {conditions['weather']}
- Venue: {conditions['venue']}

Available players (Name | Role | Credits | Key stats):
{pool_text}

Budget: 100 credits.

The analyst critiqued your previous selection:
{previous_critique}

Revise your team to specifically address each concern raised.
Use the same format:
TEAM: [comma-separated list of exactly 11 player names]
CAPTAIN: [one player name]
VICE-CAPTAIN: [one player name]
TOTAL CREDITS: [number]
REASONING: [2-3 sentences explaining what you changed and why]"""

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens=600,
        temperature=1   # slightly higher = more variety per run
    )

    return response.choices[0].message.content

def parse_team(response_text):
    """Extract team, captain and vice-captain from GPT's response."""
    result = {
        "team": [], "captain": "",
        "vice_captain": "", "reasoning": ""
    }

    for line in response_text.strip().split("\n"):
        if line.startswith("TEAM:"):
            names = line.replace("TEAM:", "").strip()
            result["team"] = [n.strip() for n in names.split(",")]
        elif line.startswith("CAPTAIN:"):
            result["captain"] = line.replace("CAPTAIN:", "").strip()
        elif line.startswith("VICE-CAPTAIN:"):
            result["vice_captain"] = line.replace("VICE-CAPTAIN:", "").strip()
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.replace("REASONING:", "").strip()

    return result

# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    conditions = {
        "format":  "T20",
        "pitch":   "Spinning",
        "weather": "Clear",
        "venue":   "MA Chidambaram Stadium, Chennai"
    }

    pool = load_player_pool()
    print(f"Player pool loaded: {len(pool)} players\n")

    print("Asking GPT-4o-mini to pick a team...\n")
    response = pick_team(conditions, pool)

    print("GPT-4o-mini's response:")
    print("-" * 50)
    print(response)
    print("-" * 50)

    parsed = parse_team(response)
    print(f"\nParsed team ({len(parsed['team'])} players):")
    for p in parsed["team"]:
        print(f"  - {p}")
    print(f"Captain     : {parsed['captain']}")
    print(f"Vice-captain: {parsed['vice_captain']}")