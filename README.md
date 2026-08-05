# 🏏 Fantasy XI Debate Engine

**Two LLMs argue about cricket until they agree on a fantasy team.**

A multi-agent AI system where **GPT proposes** a fantasy cricket XI and **Claude critiques** it — round after round — until the critic approves the team or the debate hits its round limit. The players, their stats and their "credit" prices are not hardcoded: they are derived from **291,574 real IPL deliveries** (2008–2026) using a custom statistical pipeline.

Ships with two interfaces: a rich terminal app and a React web app that streams the debate live over Server-Sent Events.

---

## Table of contents

- [Why this project exists](#why-this-project-exists)
- [Demo / what you actually see](#demo--what-you-actually-see)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [The data pipeline](#the-data-pipeline)
- [The agents & prompt design](#the-agents--prompt-design)
- [Quickstart](#quickstart)
- [API reference](#api-reference)
- [Project structure](#project-structure)
- [Design decisions & trade-offs](#design-decisions--trade-offs)
- [Known limitations & roadmap](#known-limitations--roadmap)
- [Cost & performance](#cost--performance)
- [Tech stack](#tech-stack)
- [What this project demonstrates](#what-this-project-demonstrates)
- [Credits & licence](#credits--licence)

---

## Why this project exists

A single LLM asked to "pick the best fantasy XI" gives you a confident answer with no scrutiny. It over-indexes on famous names, ignores pitch conditions, and never checks its own credit budget.

This project tests a different idea: **adversarial collaboration between two different model families**. One model has the job of *producing*; a second, independently prompted model has the job of *finding fault*. The producer only gets to stop when the critic signs off.

That pattern — generator + critic with a machine-readable verdict and a bounded retry loop — is the same shape used in real production LLM systems (LLM-as-judge, reflection loops, self-refine). Fantasy cricket is just an unusually good test bed for it, because a "good answer" has hard constraints (11 players, ≤100 credits, role minimums) *and* soft judgement calls (does this attack suit a spinning pitch at Chepauk?).

---

## Demo / what you actually see

Pick your match conditions — format, pitch type, weather, venue — hit start, and the argument streams in live, round by round. Every screenshot below is one real debate: a T20 at Wankhede Stadium, flat pitch, clear weather.

### 1. The selector proposes an XI

Eleven picks with the captain and vice-captain marked inline, plus the reasoning that justifies them against the conditions — here, betting on Wankhede's short boundaries with explosive strike rates.

### 2. The critic attacks it

Not vague praise — specific, checkable objections: no frontline spinner for the middle overs, a vice-captain picked on recent form rather than venue record, five aggressive top-order batters with no anchor, three death specialists on a flat deck. Verdict: **needs revision**, so the loop continues.

### 3. The selector revises

Round 2 addresses each point — genuine spin depth via a leg-spinner and a left-arm orthodox all-rounder — and the critic responds in diff form: what improved, what's still weak.

### 4. The final XI

The debate settles into a final team with the captain (2×) and vice-captain (1.5×) multipliers marked, tagged with how it ended — approved by the critic, or returned at the three-round limit as it was here.

### The terminal interface

The same loop runs without a browser via `python main.py`, rendered with Rich (representative output):

```
──────────────── Round 1 · Selector ────────────────
  Captain        Suryakumar Yadav
  Vice-captain   JJ Bumrah
  Team           V Kohli, Suryakumar Yadav, Shubman Gill, ...
  Reasoning      Flat Wankhede deck favours high strike-rate...

──────────────── Round 1 · Critic ──────────────────
╭─ Analysis · ✗ NEEDS REVISION ─────────────────────────────╮
│ • Bowling attack is pace-heavy — no frontline spinner for  │
│   the middle overs despite a 187 SR top order              │
│ • Captaincy on a bowler at Wankhede wastes the 2× on a     │
│   venue averaging 180+ first-innings scores                │
│ • Credits: 96.5 used, 3.5 left idle — under-spent          │
│ VERDICT: NEEDS REVISION                                    │
╰────────────────────────────────────────────────────────────╯

──────────────── Round 2 · Selector ────────────────
  ...revises to address each point...
```

---

## How it works

```
                    ┌─────────────────────────────┐
                    │   User sets conditions      │
                    │  format · pitch · weather   │
                    │         · venue             │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Player pool (55 players)    │
                    │  25 BAT · 20 BOWL · 10 AR    │
                    │  built from IPL ball-by-ball │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────▼──────────────────────────┐
        │                    DEBATE LOOP                      │
        │                  (max 3 rounds)                     │
        │                                                     │
        │   ┌───────────────┐   team +    ┌───────────────┐   │
        │   │  GPT selector │  reasoning  │ Claude critic │   │
        │   │   (OpenAI)    ├────────────►│  (Anthropic)  │   │
        │   │               │             │               │   │
        │   │  picks XI, C, │◄────────────┤ 2-4 bullet    │   │
        │   │  VC, credits  │  critique   │ critique +    │   │
        │   └───────────────┘             │ VERDICT       │   │
        │                                 └───────┬───────┘   │
        └─────────────────────────────────────────┼───────────┘
                                                  │
                       ACCEPTABLE ────────────────┴──── NEEDS REVISION
                            │                              │
                            ▼                              ▼
                    ┌───────────────┐              loop back to GPT
                    │  Final XI +   │              with the critique
                    │  transcript   │              injected into the
                    └───────────────┘              next prompt
```

**The loop, precisely:**

1. **Round 1 — selection.** The selector receives the match conditions, the 55-player pool with per-role stats and credit prices, and a rules block (exactly 11 players, ≥1 WK, ≥3 BAT, ≥1 AR, ≥3 BOWL, ≤100 credits, one captain, one vice-captain). It replies in a fixed `TEAM: / CAPTAIN: / VICE-CAPTAIN: / TOTAL CREDITS: / REASONING:` format that is parsed into a dict.
2. **Round 1 — critique.** The critic gets the same conditions plus the selector's raw output, and is instructed to be specific, concise (max 4 bullets) and decisive, ending with exactly `VERDICT: ACCEPTABLE` or `VERDICT: NEEDS REVISION`.
3. **Verdict routing.** `parse_verdict()` extracts the verdict, defaulting to `NEEDS REVISION` when the string is missing — the loop **fails closed**, so a malformed critique never silently rubber-stamps a bad team.
4. **Rounds 2–3 — revision.** On `NEEDS REVISION`, the critique text is injected into the selector's next prompt with an explicit instruction to address each concern. The critic switches to a follow-up prompt that asks what improved and what is still weak.
5. **Termination.** Early exit on `ACCEPTABLE`; otherwise the loop stops after round 3 and returns the latest team, tagged "max rounds reached". Every round is appended to a `transcript` list, so the full argument is auditable after the fact.

---

## Architecture

The core debate logic is a single, interface-agnostic module. Both front doors — CLI and HTTP — call the same selector and critic functions, so behaviour can't drift between them.

```
                    ┌────────────────────────────────────┐
                    │   frontend/ (React 19 + Vite)      │
                    │   ConditionsForm · DebateStream    │
                    │   · FinalTeam                      │
                    └────────────────┬───────────────────┘
                                     │ POST /api/debate
                                     │ ◄── text/event-stream
                    ┌────────────────▼───────────────────┐
   ┌──────────┐     │   backend/ (FastAPI)               │
   │ main.py  │     │   routes/debate.py                 │
   │ Rich CLI │     │   StreamingResponse generator      │
   └────┬─────┘     └────────────────┬───────────────────┘
        │                            │
        └────────────┬───────────────┘
                     ▼
        ┌────────────────────────────┐
        │  gpt_selector.py           │──► OpenAI API
        │  claude_critic.py          │──► Anthropic API
        │  debate_loop.py            │
        └────────────┬───────────────┘
                     ▼
        ┌────────────────────────────┐
        │  data/player_pool.csv      │◄── player_pool.py
        │  (284 priced players)      │    (offline build step)
        └────────────────────────────┘
                     ▲
        ┌────────────┴───────────────┐
        │  data/*.csv                │
        │  1,226 IPL matches         │
        │  291,574 deliveries        │
        └────────────────────────────┘
```

**Streaming.** The web path doesn't wait for the whole debate. `stream_debate()` is a Python generator that yields SSE frames as each API call returns, so the browser paints round 1's selection while round 1's critique is still being generated. The frontend reads the response body with `ReadableStream.getReader()` and a `TextDecoder`, parses `data: ` frames, and appends to React state.

**Event types on the wire:** `status` (which agent is thinking), `gpt` (raw + parsed selection), `claude` (critique + verdict), `done` (final team, rounds taken, final verdict).

---

## The data pipeline

Nothing about the player pool is hand-typed guesswork — it's computed from raw ball-by-ball data in [Cricsheet](https://cricsheet.org/) format.

**Input:** `data/` holds 1,226 IPL matches as ball-by-ball CSVs (plus a matching `*_info.csv` metadata file each) — **291,574 deliveries**, seasons **2007/08 → 2026**, 732 unique batters, 575 unique bowlers, 60 venues. ~48 MB on disk.

**`player_pool.py` turns that into a priced, role-tagged pool:**

| Stage | What happens |
|---|---|
| **Load** | Concatenate every non-`_info` CSV into one DataFrame; normalise `season` to string (the dataset mixes `2024` and `2007/08` styles). |
| **Recency filter** | Keep only seasons 2022–2026. Fantasy value is about current form, not a player's 2011 numbers. |
| **Batting stats** | Balls faced (excluding wides), runs off bat, dismissals → `batting_avg` and `strike_rate`. Minimum **100 balls faced** to qualify. |
| **Bowling stats** | Legal balls bowled (excluding wides and no-balls), runs conceded (runs off bat + extras), wickets — with `run out`, `retired hurt` and `obstructing the field` excluded so a bowler isn't credited for a fielding dismissal. → `economy`. Minimum **60 balls bowled** to qualify. |
| **Role assignment** | Qualifies at both bat and ball → `AR`; bat only → `BAT`; otherwise → `BOWL`. |
| **Credit pricing** | A percentile-rank composite, scaled into the 8.0–10.5 band. Batters: 50% batting average + 50% strike rate. Bowlers: 60% inverse economy + 40% wickets. All-rounders: 30% SR + 20% avg + 30% inverse economy + 20% wickets. Ranks (not raw values) keep one outlier from distorting the whole price curve. |
| **Star injection** | 35 globally recognised players are merged in at the front with curated recent T20 numbers, then `drop_duplicates(keep="first")` lets them override the data-driven row. |
| **Output** | `data/player_pool.csv` — **284 players** (107 BAT · 139 BOWL · 38 AR), sorted by credits. |

**Why the star-injection layer exists:** the ball-by-ball archive is IPL-only and season-filtered, so a genuinely elite player who missed a window (injury, national duty, a franchise-less season) either falls below the qualification threshold or gets priced oddly. A pool where Bumrah is missing and a fringe seamer is priced at 10.5 makes the *debate* look broken even when the *maths* is right. The injection layer is an explicit, auditable override list rather than a silent fudge to the formula — the trade-off is documented in [Known limitations](#known-limitations--roadmap).

At debate time, `load_player_pool()` takes the top **25 BAT + 20 BOWL + 10 AR = 55 players** — enough breadth for genuinely different teams across rounds, small enough to keep the prompt cheap and the model's attention focused.

---

## The agents & prompt design

| Role | Model | Job |
|---|---|---|
| **Selector** | `gpt-4.1` (OpenAI), `temperature=1`, `max_tokens=600` | Pick 11 players within constraints; revise against critique |
| **Critic** | `claude-haiku-4-5` (Anthropic), `max_tokens=400` | Find specific weaknesses; issue a binary verdict |

**Why two different providers?** A model critiquing its own output shares its blind spots. Crossing families gives the critique genuinely independent priors — and it makes the disagreements interesting rather than performative.

**Why a small, cheap critic?** The critic's job is narrow and well-specified: read a team, name concrete weaknesses, emit one of two verdicts. That's exactly the shape of task where a fast, inexpensive model performs on par with a frontier one, and it keeps a full 3-round debate at fractions of a cent.

**Prompt techniques used:**

- **Structured output via strict formatting.** The selector is given an exact response template, which `parse_team()` reads line-by-line. No JSON mode dependency, no parser library — and a fixed contract that makes the CLI, the API and the React UI all read from the same parsed shape.
- **Machine-readable verdicts.** `VERDICT: ACCEPTABLE` / `VERDICT: NEEDS REVISION` turns a paragraph of prose into control flow, which is what makes the loop a loop instead of a chat.
- **Fail-closed parsing.** An unparseable verdict is treated as `NEEDS REVISION`. The system errs toward more scrutiny, never less.
- **Conditions → heuristics in the system prompt.** Rather than hoping the model knows cricket, the selector's system prompt maps conditions to guidance explicitly: flat pitch → high-SR batters and all-rounders; seaming → pace with good economy; spinning → spinners and high-average batters; overcast → swing bowlers; humid → spin grips more.
- **Round-aware prompts.** Round 1 asks for a fresh critique across five named dimensions (conditions fit, batting depth, pace/spin balance, C/VC choice, credit efficiency). Rounds 2+ switch to a diff-style prompt: what improved, what's still weak. The critic is judging a revision, not re-reviewing from scratch.
- **Temperature 1 on the selector** so repeated runs on identical conditions produce genuinely different teams — the debate stays interesting and the pool actually gets explored.
- **Constraint reminders in-prompt.** Role minimums and the 100-credit cap are restated in every revision prompt, because constraints degrade first under long-context revision pressure.

---

## Quickstart

### Prerequisites

- Python 3.11+ (developed on 3.14)
- Node 18+ (for the web UI)
- An **OpenAI API key** and an **Anthropic API key**

### 1. Clone and install

```bash
git clone <your-repo-url>
cd fantasy-cricket-debate

python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your API keys

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Verify both keys are visible to the app:

```bash
python test_setup.py
# OpenAI key loaded: True
# Anthropic key loaded: True
```

> `.env` is git-ignored and must stay that way. Never commit real keys.

### 3. Build the player pool

```bash
python player_pool.py
```

Reads every match CSV in `data/`, computes the stats, prices the players, and writes `data/player_pool.csv`. Prints a summary and the top 20 by credits. Run this once (or again whenever you add new match data).

Optional — sanity-check the raw dataset first:

```bash
python explore_data.py    # deliveries, seasons, unique players, venues
```

### 4a. Run the terminal app

```bash
python main.py
```

Prompts you for format, pitch, weather and venue, then streams the debate into a Rich-formatted terminal UI with the final XI and a round-by-round summary.

### 4b. Run the web app

Two terminals.

**Backend:**

```bash
uvicorn backend.main:app --reload --port 8000
# http://localhost:8000        → health check
# http://localhost:8000/docs   → interactive OpenAPI docs
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

CORS on the backend is pinned to `http://localhost:5173`; change `allow_origins` in [backend/main.py](backend/main.py) if you run Vite on a different port.

The frontend targets `http://localhost:8000` by default. Point it elsewhere with a `frontend/.env` file:

```env
VITE_API_URL=http://localhost:8000
```

### Test individual agents in isolation

Both agent modules are runnable on their own — handy when you're iterating on a prompt:

```bash
python gpt_selector.py     # one selection for a fixed set of conditions
python claude_critic.py    # one critique of a hardcoded team
python debate_loop.py      # full debate, plain-text output, no Rich, no server
```

---

## API reference

**`GET /`** — health check.

```json
{ "status": "Fantasy Cricket Debate API is running" }
```

**`POST /api/debate`** — run a debate, streamed as `text/event-stream`.

Request body:

```json
{
  "format":  "T20",
  "pitch":   "Flat",
  "weather": "Clear",
  "venue":   "Wankhede Stadium, Mumbai"
}
```

Response — a sequence of SSE frames:

```
data: {"type":"status","message":"Round 1: GPT is selecting a team..."}

data: {"type":"gpt","round":1,"raw":"TEAM: ...","parsed":{"team":[...],"captain":"...","vice_captain":"...","reasoning":"..."}}

data: {"type":"status","message":"Round 1: Claude is analysing the team..."}

data: {"type":"claude","round":1,"critique":"• ...","verdict":"NEEDS REVISION"}

data: {"type":"done","final_team":{...},"rounds":2,"verdict":"ACCEPTABLE"}
```

Consume it with `curl`:

```bash
curl -N -X POST http://localhost:8000/api/debate \
  -H "Content-Type: application/json" \
  -d '{"format":"T20","pitch":"Spinning","weather":"Humid","venue":"MA Chidambaram Stadium, Chennai"}'
```

The `done` frame is always the last one, whether the debate ended by approval or by exhausting its rounds — its `verdict` field tells you which.

---

## Project structure

```
fantasy-cricket-debate/
├── player_pool.py           # Data pipeline: 291k deliveries → priced player pool
├── explore_data.py          # Dataset sanity checks
├── gpt_selector.py          # Selector agent: prompt, call, response parser
├── claude_critic.py         # Critic agent: prompt, call, verdict parser
├── debate_loop.py           # Interface-agnostic debate loop + plain-text runner
├── main.py                  # Rich terminal app
├── test_setup.py            # Env/dependency smoke test
├── requirements.txt
├── .env                     # API keys (git-ignored)
│
├── backend/
│   ├── main.py              # FastAPI app, CORS, router mount
│   └── routes/
│       └── debate.py        # POST /api/debate — SSE generator
│
├── docs/                    # README screenshots
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx          # State, fetch + stream reader, layout
│       └── components/
│           ├── ConditionsForm.jsx   # Sidebar: format/pitch/weather/venue
│           ├── DebateStream.jsx     # Live round-by-round feed
│           └── FinalTeam.jsx        # Final XI grid with C/VC badges
│
└── data/
    ├── <match_id>.csv        # 1,226 ball-by-ball match files (Cricsheet)
    ├── <match_id>_info.csv   # matching match metadata
    └── player_pool.csv       # generated — 284 priced players
```

**Key files, if you're skimming:** [player_pool.py](player_pool.py) for the data engineering, [gpt_selector.py](gpt_selector.py) and [claude_critic.py](claude_critic.py) for the prompt design, [backend/routes/debate.py](backend/routes/debate.py) for the streaming loop.

---

## Design decisions & trade-offs

**Structured text over JSON mode.** Provider-specific JSON modes would give stronger guarantees, but a plain `KEY: value` contract keeps the two agents symmetric and provider-agnostic — the same parser shape works whichever model sits behind either role. The cost is a hand-rolled parser; the benefit is that swapping either model is a one-line change.

**A hard 3-round cap.** LLM debate loops can oscillate forever — the critic can always find *something*. Capping rounds bounds latency and spend, and returning the latest team with an explicit "max rounds reached" flag is more honest than pretending consensus was reached.

**Percentile ranks, not raw stats, for pricing.** A player with a 400 strike rate off 3 balls would dominate any raw-value normalisation. Ranking first makes prices robust to small samples and outliers; the qualification thresholds (100 balls faced / 60 bowled) handle the rest.

**Pool trimmed to 55 players at prompt time.** The full pool is 284. Sending all of it would cost more tokens, and long lists actively hurt selection quality — models anchor on the head of a long list. 55 is enough for round-to-round variety without that.

**Streaming instead of a single response.** A 3-round debate is six sequential LLM calls. A request/response API would leave the user staring at a spinner for the duration. SSE turns dead waiting time into the actual product — watching the argument is the point.

**Generator-based SSE, not WebSockets.** The data flows one way and the connection is short-lived. A Python generator plus `StreamingResponse` is about fifteen lines and needs no connection state, no reconnect logic, and no extra dependency.

---

## Known limitations & roadmap

Being straight about what this does *not* do yet:

- **Model label mismatch in the CLI.** The terminal app still labels the selector "GPT-4o-mini" (the model used while prototyping) while the code calls `gpt-4.1`. The web UI and API status messages have been corrected; [main.py](main.py) and [debate_loop.py](debate_loop.py) still need the same treatment.
- **Constraints are prompt-enforced, not code-enforced.** Nothing validates the returned XI against the 100-credit cap or the role minimums after the fact. The critic usually catches violations — but a deterministic post-parse validator (and a re-ask on failure) is the obvious next step.
- **Venue is a string, not data.** The venue name goes into the prompt and the model reasons from its own knowledge; the pipeline doesn't yet compute venue-specific splits, even though `data/` has 60 venues of ball-by-ball detail. Venue-conditioned stats are the single biggest available quality win.
- **Wicket-keepers aren't modelled.** The pool has no WK role, so the prompt asks the selector to nominate one of its batters as keeper. Real fantasy scoring treats keepers differently.
- **Curated star stats.** The 35 injected star rows use hand-entered recent-form numbers rather than pipeline output, so they can go stale. Widening the season window and adding non-IPL T20 data would let the formula stand on its own.
- **Option lists drift between interfaces.** The CLI offers pitch types `Flat / Seaming / Spinning / Dry / Hard / Grass` while the web UI offers `Flat / Seaming / Spinning / Two-paced`, and the CLI lists 16 venues but only accepts a selection from the first five. Both should read one shared config.
- **No test suite.** `test_setup.py` is an import/env smoke test, not tests. The parsers (`parse_team`, `parse_verdict`) and the credit formula are pure functions and pleasant to unit-test — a natural first PR.
- **No persistence.** Debates aren't saved, so you can't compare a team against the same conditions a week later, or measure whether round-3 teams actually beat round-1 teams.

**Roadmap, roughly in order of value:** deterministic constraint validator → venue-conditioned stats → persisted debate history → backtesting against real fantasy points → a third "referee" agent for deadlocks.

---

## Cost & performance

| | |
|---|---|
| LLM calls per debate | 2 per round, 4–6 total |
| Typical wall-clock | ~15–40 s for a full 3-round debate |
| Prompt size | ~1.5–2k tokens per selector call (55-player pool) |
| Output cap | 600 tokens (selector) / 400 tokens (critic) |
| Cost per debate | well under a cent at current pricing for both models |
| Pool build | one-time, a few seconds over 291k rows in pandas |

Latency is dominated by sequential LLM round-trips, which is inherent to the design — the critic cannot start until the selection exists. Streaming is what makes that acceptable in practice.

---

## Tech stack

**AI / LLM** — OpenAI Python SDK (`openai` 2.36), Anthropic Python SDK (`anthropic` 0.102), multi-agent orchestration, prompt engineering, structured output parsing

**Data** — pandas 3.0, 291k-row ball-by-ball aggregation, percentile-rank feature engineering, Cricsheet CSV format

**Backend** — FastAPI 0.136, Uvicorn, Pydantic 2 request validation, Server-Sent Events via generator-based `StreamingResponse`, CORS

**Frontend** — React 19, Vite 8, streaming `fetch` with `ReadableStream` + `TextDecoder`, hooks-based state, ESLint 10

**CLI** — Rich 15 (panels, tables, prompts, live formatting)

**Config** — python-dotenv, `.env`-based secrets

---

## What this project demonstrates

For anyone evaluating the code rather than the cricket:

- **Multi-agent LLM orchestration** — a generator/critic loop with a machine-readable verdict driving real control flow, bounded retries, and fail-closed parsing
- **Cross-provider integration** — OpenAI and Anthropic SDKs in one system, deliberately chosen for independent priors, with model choice matched to task difficulty and cost
- **Prompt engineering under constraints** — strict output contracts, round-aware prompting, domain heuristics encoded in the system prompt, temperature tuned for exploration
- **Data engineering** — a real pipeline from 291k raw deliveries to a clean, priced, role-tagged feature table, with qualification thresholds and outlier-robust ranking
- **Full-stack delivery** — the same core logic behind both a streaming HTTP API and a terminal app, with a React client consuming SSE incrementally
- **Separation of concerns** — agents, loop, transport and presentation are independent modules; either model, either interface, or the data source can be swapped without touching the others
- **Engineering judgement** — documented trade-offs, and an honest, specific account of what's still missing

---

## Credits & licence

Ball-by-ball match data from **[Cricsheet](https://cricsheet.org/)**, which publishes it under the [Open Data Commons Attribution Licence](https://opendatacommons.org/licenses/by/1-0/).

Built as a personal project exploring multi-agent LLM systems. Not affiliated with any fantasy sports platform, and not betting or investment advice — the teams here are generated by language models arguing with each other, which is exactly as reliable as it sounds.

Licensed under the MIT Licence.
