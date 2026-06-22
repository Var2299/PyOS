import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ files: 0, directories: 0, deleted: 0 });
  const [commands, setCommands] = useState(0);
  const [recentLogs, setRecentLogs] = useState([]);

  useEffect(() => {
    async function load() {
      const [statsRes, cmdRes, logsRes] = await Promise.all([
        api.get("/nodes/stats/"),
        api.get("/commands/"),
        api.get("/logs/"),
      ]);
      setStats(statsRes.data);
      setCommands(cmdRes.data.count ?? cmdRes.data.length ?? 0);
      setRecentLogs((logsRes.data.results || logsRes.data).slice(0, 6));
    }
    load();
  }, []);

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>dashboard
        </div>
      </div>

      <p style={{ color: "var(--muted)", marginBottom: 20, fontFamily: "var(--mono)", fontSize: 13 }}>
        Welcome back, {user?.username}. Here is the state of your workspace.
      </p>

      <div className="stat-grid">
        <div className="stat green">
          <div className="n">{stats.files}</div>
          <div className="l">files</div>
        </div>
        <div className="stat amber">
          <div className="n">{stats.directories}</div>
          <div className="l">directories</div>
        </div>
        <div className="stat blue">
          <div className="n">{commands}</div>
          <div className="l">commands run</div>
        </div>
        <div className="stat">
          <div className="n">{stats.deleted}</div>
          <div className="l">in recycle bin</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-h">// recent activity</div>
        <table>
          <thead>
            <tr>
              <th>action</th>
              <th>detail</th>
              <th>when</th>
            </tr>
          </thead>
          <tbody>
            {recentLogs.map((l) => (
              <tr key={l.id}>
                <td>
                  <span className="tag blue">{l.action}</span>
                </td>
                <td>{l.detail}</td>
                <td className="mono" style={{ color: "var(--muted)" }}>
                  {new Date(l.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {recentLogs.length === 0 && (
              <tr>
                <td colSpan={3} className="empty">
                  No activity yet — head to the <Link to="/explorer">explorer</Link>.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
