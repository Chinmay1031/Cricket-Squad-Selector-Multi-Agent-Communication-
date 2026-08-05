import os
from dotenv import load_dotenv
from gpt_selector import load_player_pool, pick_team, parse_team
from claude_critic import critique_team, parse_verdict

load_dotenv()

MAX_ROUNDS = 3

def run_debate(conditions):
    """
    Run the full GPT vs Claude debate loop.
    Returns the final agreed team and full transcript.
    """
    pool = load_player_pool()
    transcript = []  # keeps track of everything said

    print("\n" + "="*60)
    print("         FANTASY XI DEBATE STARTING")
    print("="*60)
    print(f"  Format  : {conditions['format']}")
    print(f"  Pitch   : {conditions['pitch']}")
    print(f"  Weather : {conditions['weather']}")
    print(f"  Venue   : {conditions['venue']}")
    print("="*60 + "\n")

    gpt_response = None
    final_team = None
    critique = None

    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"--- ROUND {round_num} ---\n")

        # ── GPT picks / revises ──────────────────────────────────
        print("GPT-4o-mini is selecting a team...")
        gpt_response = pick_team(
            conditions,
            pool,
            previous_critique=critique  # None in round 1
        )

        parsed = parse_team(gpt_response)
        final_team = parsed  # always keep the latest team

        transcript.append({
            "round": round_num,
            "agent": "GPT-4o-mini",
            "type": "selection",
            "content": gpt_response
        })

        print(f"\nGPT-4o-mini selected:")
        print(f"  Team    : {', '.join(parsed['team'])}")
        print(f"  Captain : {parsed['captain']}")
        print(f"  Vc      : {parsed['vice_captain']}")
        print(f"  Reason  : {parsed['reasoning']}\n")

        # ── Claude critiques ─────────────────────────────────────
        print("Claude is analysing the team...")
        critique = critique_team(conditions, gpt_response, round_number=round_num)
        verdict = parse_verdict(critique)

        transcript.append({
            "round": round_num,
            "agent": "Claude",
            "type": "critique",
            "content": critique,
            "verdict": verdict
        })

        print(f"\nClaude's verdict: {verdict}")
        print(f"\nClaude says:\n{critique}\n")

        # ── Early exit if Claude approves ────────────────────────
        if verdict == "ACCEPTABLE":
            print("✓ Claude approved the team! Debate ends early.\n")
            break

        if round_num < MAX_ROUNDS:
            print(f"GPT will revise for round {round_num + 1}...\n")
        else:
            print("Maximum rounds reached. Using final team.\n")

    return final_team, transcript

def display_final_team(team, transcript):
    """Print a clean summary of the final agreed team."""
    print("\n" + "="*60)
    print("              FINAL FANTASY XI")
    print("="*60)

    if team["team"]:
        for i, player in enumerate(team["team"], 1):
            tag = ""
            if player == team["captain"]:
                tag = "  ← CAPTAIN (2x)"
            elif player == team["vice_captain"]:
                tag = "  ← VICE-CAPTAIN (1.5x)"
            print(f"  {i:2}. {player}{tag}")

    print(f"\n  Rounds taken : {transcript[-1]['round']}")
    last_verdict = [t for t in transcript if t['agent'] == 'Claude'][-1]
    print(f"  Final verdict: {last_verdict['verdict']}")
    print("="*60)

    print("\n--- DEBATE TRANSCRIPT ---")
    for entry in transcript:
        print(f"\n[Round {entry['round']}] {entry['agent']} ({entry['type'].upper()})")
        print("-" * 40)
        print(entry["content"])

# Run it
if __name__ == "__main__":
    conditions = {
        "format": "T20",
        "pitch": "Flat",
        "weather": "Clear",
        "venue": "Wankhede Stadium, Mumbai"
    }

    final_team, transcript = run_debate(conditions)
    display_final_team(final_team, transcript)