import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function Search() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);

  async function run(e) {
    e?.preventDefault();
    if (!q.trim()) return;
    const res = await api.get(`/nodes/search/?q=${encodeURIComponent(q.trim())}`);
    setResults(res.data);
    setSearched(true);
  }

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>search
        </div>
      </div>

      <form className="search-bar" onSubmit={run}>
        <input
          autoFocus
          placeholder="Search files and folders by name or content…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="btn sm">Search</button>
      </form>

      {searched && results.length === 0 && (
        <div className="empty">No matches for “{q}”.</div>
      )}

      {results.length > 0 && (
        <div className="panel">
          <div className="panel-h">// {results.length} result(s)</div>
          <table>
            <thead>
              <tr>
                <th>name</th>
                <th>type</th>
                <th>path</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {results.map((n) => (
                <tr key={n.id}>
                  <td>{n.name}</td>
                  <td>
                    <span className={"tag " + (n.node_type === "file" ? "blue" : "amber")}>
                      {n.node_type}
                    </span>
                  </td>
                  <td className="mono" style={{ color: "var(--muted)" }}>
                    {n.path}
                  </td>
                  <td>
                    {n.node_type === "file" && (
                      <button className="icon-btn" onClick={() => navigate(`/file/${n.id}`)}>
                        open
                      </button>
                    )}
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
