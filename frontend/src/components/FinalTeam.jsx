export default function FinalTeam({ team, rounds, verdict }) {
  if (!team?.team?.length) return null;

  const approved = verdict === "ACCEPTABLE";

  return (
    <section className="final">
      <div className="final-inner">
        <div className="final-head">
          <div>
            <h2 className="final-title">Final XI</h2>
            <p className="final-meta">
              {rounds} round{rounds > 1 ? "s" : ""} ·{" "}
              {approved ? "approved by the critic" : "returned at the round limit"}
            </p>
          </div>
          <span className={`tag ${approved ? "tag--ok" : "tag--warn"}`}>
            {approved ? "Approved" : "Max rounds"}
          </span>
        </div>

        <div className="final-grid">
          {team.team.map((player, i) => {
            const isCaptain = player === team.captain;
            const isVice = player === team.vice_captain;
            return (
              <div
                key={`${player}-${i}`}
                className={`player${isCaptain || isVice ? " player--lead" : ""}`}
              >
                <span className="player-num">{String(i + 1).padStart(2, "0")}</span>
                <span className="player-name" title={player}>
                  {player}
                </span>
                {isCaptain && <span className="player-role">C · 2×</span>}
                {isVice && <span className="player-role">VC · 1.5×</span>}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
