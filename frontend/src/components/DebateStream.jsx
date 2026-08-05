import { useEffect, useRef } from "react";

function SelectionTurn({ ev }) {
  const { captain, vice_captain: viceCaptain, team = [], reasoning } = ev.parsed ?? {};

  return (
    <div className="card">
      <div className="card-head">
        <span className="card-agent">Selector</span>
        <span className="card-round">Round {ev.round} · Team selection</span>
        <span className="card-head-end meta">{team.length} players</span>
      </div>

      <div className="card-body">
        <div className="chips">
          {team.map((player, i) => {
            const isCaptain = player === captain;
            const isVice = player === viceCaptain;
            return (
              <span
                key={`${player}-${i}`}
                className={`chip${isCaptain || isVice ? " chip--lead" : ""}`}
              >
                {player}
                {isCaptain && <span className="chip-role">C</span>}
                {isVice && <span className="chip-role">VC</span>}
              </span>
            );
          })}
        </div>

        {reasoning && <p className="prose prose--quiet">{reasoning}</p>}
      </div>
    </div>
  );
}

function CritiqueTurn({ ev }) {
  const approved = ev.verdict === "ACCEPTABLE";

  return (
    <div className="card">
      <div className="card-head">
        <span className="card-agent">Critic</span>
        <span className="card-round">Round {ev.round} · Analysis</span>
        <span className="card-head-end">
          <span className={`tag ${approved ? "tag--ok" : "tag--warn"}`}>
            {approved ? "Acceptable" : "Needs revision"}
          </span>
        </span>
      </div>

      <div className="card-body">
        <p className="prose">{ev.critique}</p>
      </div>
    </div>
  );
}

export default function DebateStream({ events, status, error }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events, status]);

  const idle = events.length === 0 && !status && !error;

  return (
    <div className="stream">
      <div className="stream-inner">
        {error && (
          <div className="error" role="alert">
            {error}
            <div className="error-hint">
              Check that the API is running on port 8000 — <code>uvicorn backend.main:app --reload</code>
            </div>
          </div>
        )}

        {idle && (
          <div className="empty">
            <div className="empty-mark" />
            <p className="empty-title">No debate yet</p>
            <p className="empty-hint">Set the match conditions, then start the debate.</p>
          </div>
        )}

        {events.map((ev, i) => (
          <div className="turn" key={`${ev.type}-${ev.round}-${i}`}>
            {ev.type === "gpt" ? <SelectionTurn ev={ev} /> : null}
            {ev.type === "claude" ? <CritiqueTurn ev={ev} /> : null}
          </div>
        ))}

        {status && (
          <div className="status" role="status" aria-live="polite">
            <span className="dot dot--pulse" />
            {status}
          </div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
