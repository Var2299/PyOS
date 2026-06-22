import { useEffect, useRef, useState } from "react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function CommandHistory() {
  const { user } = useAuth();
  // Terminal state
  const [cwd, setCwd] = useState(["home", user?.username].filter(Boolean));
  const [lines, setLines] = useState([
    { type: "sys", text: "PyOS terminal — type 'help' to see commands." },
  ]);
  const [cmd, setCmd] = useState("");
  const [busy, setBusy] = useState(false);
  const [recall, setRecall] = useState([]); // for up/down arrow recall
  const [recallIdx, setRecallIdx] = useState(-1);

  // Persisted history table
  const [items, setItems] = useState([]);

  const paneRef = useRef(null);
  const inputRef = useRef(null);

  async function loadHistory() {
    const res = await api.get("/commands/");
    setItems(res.data.results || res.data);
  }
  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    // autoscroll terminal to bottom on new output
    if (paneRef.current) paneRef.current.scrollTop = paneRef.current.scrollHeight;
  }, [lines]);

  const prompt = (path) =>
    `${user?.username}@pyos:/${path.join("/")}$`;

  async function run(e) {
    e.preventDefault();
    const trimmed = cmd.trim();
    if (!trimmed || busy) return;

    // echo the command line into the pane
    setLines((l) => [...l, { type: "cmd", text: `${prompt(cwd)} ${trimmed}` }]);
    setRecall((r) => [...r, trimmed]);
    setRecallIdx(-1);
    setCmd("");

    if (trimmed === "clear") {
      setLines([]);
      return;
    }

    setBusy(true);
    try {
      const res = await api.post("/terminal/run/", { command: trimmed, cwd });
      const { output, cwd: newCwd } = res.data;
      if (Array.isArray(newCwd)) setCwd(newCwd);
      if (output && output !== "\x0c") {
        setLines((l) => [...l, { type: "out", text: output }]);
      } else if (output === "\x0c") {
        setLines([]);
      }
      loadHistory();
    } catch (err) {
      setLines((l) => [
        ...l,
        { type: "err", text: err.response?.data?.detail || "command failed" },
      ]);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function onKeyDown(e) {
    // up/down arrows recall previous commands
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!recall.length) return;
      const idx = recallIdx === -1 ? recall.length - 1 : Math.max(0, recallIdx - 1);
      setRecallIdx(idx);
      setCmd(recall[idx]);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (recallIdx === -1) return;
      const idx = recallIdx + 1;
      if (idx >= recall.length) {
        setRecallIdx(-1);
        setCmd("");
      } else {
        setRecallIdx(idx);
        setCmd(recall[idx]);
      }
    }
  }

  async function del(id) {
    await api.delete(`/commands/${id}/`);
    loadHistory();
  }

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>terminal
        </div>
      </div>

      <div className="terminal" onClick={() => inputRef.current?.focus()}>
        <div className="terminal-bar">
          <span className="dot red" />
          <span className="dot amber" />
          <span className="dot green" />
          <span className="terminal-title">pyos — {user?.username}</span>
        </div>
        <div className="terminal-pane" ref={paneRef}>
          {lines.map((ln, i) => (
            <div key={i} className={`tline ${ln.type}`}>
              {ln.text}
            </div>
          ))}
          <form onSubmit={run} className="terminal-input-row">
            <span className="tprompt">{prompt(cwd)}</span>
            <input
              ref={inputRef}
              className="terminal-input"
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
              onKeyDown={onKeyDown}
              spellCheck={false}
              autoComplete="off"
              autoFocus
              disabled={busy}
            />
          </form>
        </div>
      </div>

      <p className="hint">
        Files and folders you create here also appear in the Explorer. Try:{" "}
        <span className="mono">tree</span>,{" "}
        <span className="mono">mkdir projects</span>,{" "}
        <span className="mono">cd projects</span>,{" "}
        <span className="mono">echo "hi" &gt; note.txt</span>,{" "}
        <span className="mono">cat note.txt</span>.
      </p>

      {items.length > 0 && (
        <div className="panel" style={{ marginTop: 22 }}>
          <div className="panel-h">// saved command history</div>
          <table>
            <thead>
              <tr>
                <th>command</th>
                <th>output</th>
                <th>when</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td className="mono" style={{ color: "var(--green)" }}>
                    $ {c.command}
                  </td>
                  <td
                    className="mono"
                    style={{ whiteSpace: "pre-wrap", color: "var(--muted)", maxWidth: 360 }}
                  >
                    {c.output}
                  </td>
                  <td className="mono" style={{ color: "var(--muted)" }}>
                    {new Date(c.created_at).toLocaleTimeString()}
                  </td>
                  <td>
                    <button className="icon-btn danger" onClick={() => del(c.id)}>
                      del
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
