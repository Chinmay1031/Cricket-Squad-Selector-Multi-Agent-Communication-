import os
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def critique_team(conditions, gpt_response, round_number=1):
    """
    Claude analyses GPT's team selection and either
    critiques it (NEEDS REVISION) or approves it (ACCEPTABLE).
    """

    system_prompt = """You are a sharp, experienced fantasy cricket analyst for IPL T20 matches.
Your job is to critically evaluate a team selection and identify weaknesses.

Be specific — reference actual player stats and match conditions.
Be concise — maximum 4 bullet points.
Be decisive — end with exactly one of these verdicts:

VERDICT: ACCEPTABLE  (only if the team is genuinely strong)
VERDICT: NEEDS REVISION  (if there are clear weaknesses to fix)"""

    if round_number == 1:
        prompt = f"""A fantasy selector has proposed this team for an IPL T20 match.

Match conditions:
- Format: {conditions['format']}
- Pitch: {conditions['pitch']}
- Weather: {conditions['weather']}
- Venue: {conditions['venue']}

Their selection:
{gpt_response}

Critique this team. Identify 2-3 specific weaknesses — consider:
- Does the team suit the pitch and weather conditions?
- Is the batting order deep enough?
- Is the bowling attack varied enough (pace vs spin balance)?
- Are the captain and vice-captain the highest-scoring picks?
- Are credits being used efficiently?

End your response with either VERDICT: ACCEPTABLE or VERDICT: NEEDS REVISION"""

    else:
        prompt = f"""The selector has revised their team based on your previous critique.

Match conditions:
- Format: {conditions['format']}
- Pitch: {conditions['pitch']}
- Weather: {conditions['weather']}
- Venue: {conditions['venue']}

Revised selection:
{gpt_response}

Has the revision addressed the concerns? 
Give 1-2 specific comments on what improved and what (if anything) is still weak.
End with either VERDICT: ACCEPTABLE or VERDICT: NEEDS REVISION"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # cheapest Claude model
        max_tokens=400,
        messages=[
            {"role": "user", "content": prompt}
        ],
        system=system_prompt
    )

    return response.content[0].text

def parse_verdict(critique_text):
    """Extract whether Claude approved or wants revision."""
    if "VERDICT: ACCEPTABLE" in critique_text:
        return "ACCEPTABLE"
    elif "VERDICT: NEEDS REVISION" in critique_text:
        return "NEEDS REVISION"
    else:
        return "NEEDS REVISION"  # default to revision if unclear

# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    conditions = {
        "format": "T20",
        "pitch": "Flat",
        "weather": "Clear",
        "venue": "Wankhede Stadium, Mumbai"
    }

    # Paste GPT's output from Step 4 here to test
    gpt_output = """TEAM: S Dhawan, RD Gaikwad, D Padikkal, DJ Hooda, WP Saha, HH Pandya, R Ashwin, MA Starc, G Coetzee, Ashok Sharma, Yudhvir Singh
CAPTAIN: S Dhawan
VICE-CAPTAIN: R Ashwin
TOTAL CREDITS: 100
REASONING: This team is well-balanced for the flat pitch at Wankhede Stadium, maximizing batting depth with experienced players like S Dhawan and RD Gaikwad in the top order. The inclusion of all-rounders like HH Pandya and R Ashwin adds versatility and wicket-taking options, while the bowling lineup features quality bowlers like MA Starc and G Coetzee who can exploit conditions effectively."""

    print("Sending GPT's team to Claude for critique...\n")
    critique = critique_team(conditions, gpt_output, round_number=1)

    print("Claude's critique:")
    print("-" * 50)
    print(critique)
    print("-" * 50)

    verdict = parse_verdict(critique)
    print(f"\nVerdict: {verdict}")