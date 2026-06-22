import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const TAG = {
  LOGIN: "green",
  CREATE: "green",
  UPDATE: "blue",
  SEARCH: "blue",
  DELETE: "amber",
  RESTORE: "blue",
  PURGE: "red",
  USER_UPDATE: "amber",
  USER_ROLE: "amber",
  USER_DELETE: "red",
  OWNER_NOTICE: "violet",
};

// Friendlier display names for a few internal action codes.
const LABEL = {
  OWNER_NOTICE: "NOTICE",
  USER_UPDATE: "USER",
  USER_ROLE: "ROLE",
  USER_DELETE: "USER",
};

export default function Logs() {
  const { user } = useAuth();
  const isAdmin = !!(user?.is_admin_role || user?.is_staff);
  // Admins default to the system-wide view; regular users only ever see "me".
  const [scope, setScope] = useState(isAdmin ? "all" : "me");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/logs/?scope=${scope}`).then((res) => {
      setItems(res.data.results || res.data);
      setLoading(false);
    });
  }, [scope]);

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>logs
        </div>
        {isAdmin && (
          <div className="toggle">
            <button
              className={"toggle-btn" + (scope === "all" ? " active" : "")}
              onClick={() => setScope("all")}
            >
              System-wide
            </button>
            <button
              className={"toggle-btn" + (scope === "me" ? " active" : "")}
              onClick={() => setScope("me")}
            >
              My activity
            </button>
          </div>
        )}
      </div>

      <p style={{ color: "var(--muted)", marginBottom: 16, fontFamily: "var(--mono)", fontSize: 13 }}>
        {isAdmin
          ? scope === "all"
            ? "// auditing every event across all users"
            : "// showing only your own activity"
          : "// your activity history"}
      </p>

      {loading ? (
        <div className="empty">loading…</div>
      ) : items.length === 0 ? (
        <div className="empty">No log entries yet.</div>
      ) : (
        <div className="panel">
          <div className="panel-h">// {items.length} event(s)</div>
          <table>
            <thead>
              <tr>
                <th>action</th>
                <th>user</th>
                <th>detail</th>
                <th>timestamp</th>
              </tr>
            </thead>
            <tbody>
              {items.map((l) => (
                <tr key={l.id}>
                  <td>
                    <span className={"tag " + (TAG[l.action] || "blue")}>{LABEL[l.action] || l.action}</span>
                  </td>
                  <td className="mono">{l.username || "—"}</td>
                  <td>{l.detail}</td>
                  <td className="mono" style={{ color: "var(--muted)" }}>
                    {new Date(l.created_at).toLocaleString()}
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
