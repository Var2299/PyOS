import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

function formatBytes(chars) {
  // Content is stored as text; treat 1 char ~= 1 byte for a friendly figure.
  if (chars < 1024) return `${chars} B`;
  if (chars < 1024 * 1024) return `${(chars / 1024).toFixed(1)} KB`;
  return `${(chars / (1024 * 1024)).toFixed(1)} MB`;
}

export default function AdminPanel() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    const res = await api.get("/auth/users/");
    setUsers(res.data.results || res.data);
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  async function toggleActive(u) {
    setError("");
    try {
      await api.patch(`/auth/users/${u.id}/`, { is_active: !u.is_active });
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not update user.");
    }
  }

  async function toggleAdmin(u) {
    const promoting = !(u.is_admin_role || u.is_staff);
    const verb = promoting ? "promote" : "revoke admin rights from";
    if (!confirm(`Are you sure you want to ${verb} "${u.username}"?`)) return;
    setError("");
    try {
      await api.patch(`/auth/users/${u.id}/`, { is_admin_role: promoting });
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not change role.");
    }
  }

  async function removeUser(u) {
    if (!confirm(`Permanently delete user "${u.username}" and all their files? This cannot be undone.`))
      return;
    setError("");
    try {
      await api.delete(`/auth/users/${u.id}/`);
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Could not delete user.");
    }
  }

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>admin / users
        </div>
        <span className="tag amber">admin only</span>
      </div>

      <p style={{ color: "var(--muted)", marginBottom: 18, fontFamily: "var(--mono)", fontSize: 13 }}>
        Every registered account, with workspace usage. Deactivating blocks login;
        deleting removes the user and their files.
      </p>

      {error && <div className="err">{error}</div>}

      {loading ? (
        <div className="empty">loading…</div>
      ) : (
        <div className="panel">
          <div className="panel-h">// {users.length} user(s)</div>
          <table>
            <thead>
              <tr>
                <th>user</th>
                <th>role</th>
                <th>status</th>
                <th>files</th>
                <th>folders</th>
                <th>space used</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div>{u.username}</div>
                    <div className="mono" style={{ color: "var(--muted)", fontSize: 12 }}>
                      {u.email || "—"}
                    </div>
                  </td>
                  <td>
                    {u.is_admin_role || u.is_staff ? (
                      <span className="tag amber">admin</span>
                    ) : (
                      <span className="tag">user</span>
                    )}
                  </td>
                  <td>
                    {u.is_active ? (
                      <span className="tag green">active</span>
                    ) : (
                      <span className="tag red">deactivated</span>
                    )}
                  </td>
                  <td className="mono">{u.files_created}</td>
                  <td className="mono">{u.directories_created}</td>
                  <td className="mono">{formatBytes(u.space_used)}</td>
                  <td>
                    {u.id === me.id ? (
                      <span style={{ color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 12 }}>
                        (you)
                      </span>
                    ) : (
                      <div className="row-actions">
                        <button className="icon-btn role" onClick={() => toggleAdmin(u)}>
                          {u.is_admin_role || u.is_staff ? "revoke admin" : "make admin"}
                        </button>
                        <button className="icon-btn" onClick={() => toggleActive(u)}>
                          {u.is_active ? "deactivate" : "activate"}
                        </button>
                        <button className="icon-btn danger" onClick={() => removeUser(u)}>
                          delete
                        </button>
                      </div>
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
