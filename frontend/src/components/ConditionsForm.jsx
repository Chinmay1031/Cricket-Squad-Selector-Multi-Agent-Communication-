const VENUES = [
  "Wankhede Stadium, Mumbai",
  "Eden Gardens, Kolkata",
  "M Chinnaswamy Stadium, Bengaluru",
  "Narendra Modi Stadium, Ahmedabad",
  "MA Chidambaram Stadium, Chennai",
  "Sydney Cricket Ground, Australia",
  "Melbourne Cricket Ground, Australia",
  "Adelaide Cricket Ground, Australia",
  "Perth Cricket Ground, Australia",
  "Lords Cricket Stadium, England",
  "Edgbaston Cricket Stadium, England",
  "Old Trafford Cricket Stadium, England",
  "Dubai Cricket Stadium, UAE",
  "Wanderers Stadium, Johannesburg",
  "Newlands Cricket Ground, Cape Town",
  "Kingsmead Stadium, Durban",
];

const FIELDS = [
  { key: "format", label: "Format", options: ["T20", "ODI"] },
  { key: "pitch", label: "Pitch", options: ["Flat", "Seaming", "Spinning", "Two-paced"] },
  { key: "weather", label: "Weather", options: ["Clear", "Overcast", "Humid"] },
  { key: "venue", label: "Venue", options: VENUES },
];

export default function ConditionsForm({ conditions, setConditions, onStart, loading }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-eyebrow">Fantasy XI</div>
        <h1 className="brand-title">Debate Engine</h1>
        <p className="brand-sub">One model selects, another critiques.</p>
      </div>

      <div style={{ flex: 1 }}>
        <div className="section-label">Match conditions</div>

        {FIELDS.map(({ key, label, options }) => (
          <div className="field" key={key}>
            <label className="field-label" htmlFor={`field-${key}`}>
              {label}
            </label>
            <select
              id={`field-${key}`}
              className="select"
              value={conditions[key]}
              onChange={(e) =>
                setConditions((prev) => ({ ...prev, [key]: e.target.value }))
              }
              disabled={loading}
            >
              {options.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      <button
        className="btn-primary"
        onClick={onStart}
        disabled={loading}
        aria-busy={loading}
      >
        {loading ? (
          <>
            <span className="spinner" />
            Debating
          </>
        ) : (
          "Start debate"
        )}
      </button>

      <div className="sidebar-foot">
        Selector · GPT-4.1
        <br />
        Critic · Claude Haiku 4.5
        <br />
        Max 3 rounds
      </div>
    </aside>
  );
}
