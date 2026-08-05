import { useState } from "react";
import ConditionsForm from "./components/ConditionsForm";
import DebateStream from "./components/DebateStream";
import FinalTeam from "./components/FinalTeam";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [conditions, setConditions] = useState({
    format: "T20",
    pitch: "Flat",
    weather: "Clear",
    venue: "Wankhede Stadium, Mumbai",
  });
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [finalTeam, setFinalTeam] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleEvent = (data) => {
    if (data.type === "status") {
      setStatus(data.message);
    } else if (data.type === "gpt" || data.type === "claude") {
      setEvents((prev) => [...prev, data]);
      setStatus("");
    } else if (data.type === "done") {
      setFinalTeam(data.final_team);
      setResult({ rounds: data.rounds, verdict: data.verdict });
      setStatus("");
    }
  };

  const startDebate = async () => {
    setEvents([]);
    setFinalTeam(null);
    setResult(null);
    setError(null);
    setLoading(true);
    setStatus("Connecting to the debate API…");

    try {
      const res = await fetch(`${API_BASE}/api/debate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(conditions),
      });

      if (!res.ok) throw new Error(`The API responded with ${res.status}.`);
      if (!res.body) throw new Error("This browser can't read a streamed response.");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Buffer across chunks — a single SSE frame can be split mid-JSON.
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const line = frame.split("\n").find((l) => l.startsWith("data: "));
          if (!line) continue;
          handleEvent(JSON.parse(line.slice(6)));
        }
      }
    } catch (err) {
      setError(err.message ?? "The debate failed.");
      setStatus("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <ConditionsForm
        conditions={conditions}
        setConditions={setConditions}
        onStart={startDebate}
        loading={loading}
      />

      <main className="main">
        <header className="topbar">
          <span className="topbar-title">Live debate</span>
          {loading && (
            <span className="tag">
              <span className="dot dot--pulse" />
              Running
            </span>
          )}
          {result && !loading && (
            <span className="meta">
              Settled in {result.rounds} round{result.rounds > 1 ? "s" : ""}
            </span>
          )}
        </header>

        <DebateStream events={events} status={status} error={error} />

        {finalTeam && (
          <FinalTeam
            team={finalTeam}
            rounds={result?.rounds}
            verdict={result?.verdict}
          />
        )}
      </main>
    </div>
  );
}
