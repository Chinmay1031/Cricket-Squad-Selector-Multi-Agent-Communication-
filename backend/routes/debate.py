import sys
import json
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from gpt_selector import load_player_pool, pick_team, parse_team
from claude_critic import critique_team, parse_verdict

router = APIRouter()

class MatchConditions(BaseModel):
    format: str
    pitch: str
    weather: str
    venue: str

def stream_debate(conditions: dict):
    """Generator that yields debate events as JSON strings."""

    pool = load_player_pool()
    critique = None
    final_team = None
    MAX_ROUNDS = 3

    for round_num in range(1, MAX_ROUNDS + 1):

        # ── Notify frontend: GPT is thinking ──
        yield f"data: {json.dumps({'type': 'status', 'message': f'Round {round_num} — the selector is picking a team…'})}\n\n"

        # ── GPT picks a team ──
        gpt_response = pick_team(conditions, pool, previous_critique=critique)
        parsed = parse_team(gpt_response)
        final_team = parsed

        yield f"data: {json.dumps({'type': 'gpt', 'round': round_num, 'raw': gpt_response, 'parsed': parsed})}\n\n"

        # ── Notify frontend: Claude is thinking ──
        yield f"data: {json.dumps({'type': 'status', 'message': f'Round {round_num} — the critic is analysing the team…'})}\n\n"

        # ── Claude critiques ──
        critique = critique_team(conditions, gpt_response, round_number=round_num)
        verdict = parse_verdict(critique)

        yield f"data: {json.dumps({'type': 'claude', 'round': round_num, 'critique': critique, 'verdict': verdict})}\n\n"

        # ── Early exit if Claude approves ──
        if verdict == "ACCEPTABLE":
            yield f"data: {json.dumps({'type': 'done', 'final_team': final_team, 'rounds': round_num, 'verdict': 'ACCEPTABLE'})}\n\n"
            return

        if round_num == MAX_ROUNDS:
            yield f"data: {json.dumps({'type': 'done', 'final_team': final_team, 'rounds': round_num, 'verdict': 'NEEDS REVISION'})}\n\n"

@router.post("/debate")
def start_debate(conditions: MatchConditions):
    return StreamingResponse(
        stream_debate(conditions.dict()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )