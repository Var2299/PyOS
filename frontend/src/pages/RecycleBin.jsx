import { useEffect, useState } from "react";
import api from "../api/client";

export default function RecycleBin() {
  const [items, setItems] = useState([]);

  async function load() {
    const res = await api.get("/nodes/recycle_bin/");
    setItems(res.data);
  }
  useEffect(() => {
    load();
  }, []);

  async function restore(id) {
    await api.post(`/nodes/${id}/restore/`);
    load();
  }
  async function purge(node) {
    if (!confirm(`Permanently delete "${node.name}"? This cannot be undone.`)) return;
    await api.delete(`/nodes/${node.id}/purge/`);
    load();
  }

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>recycle bin
        </div>
      </div>

      {items.length === 0 ? (
        <div className="empty">The recycle bin is empty.</div>
      ) : (
        <div className="panel">
          <div className="panel-h">// {items.length} deleted item(s)</div>
          <table>
            <thead>
              <tr>
                <th>name</th>
                <th>type</th>
                <th>original path</th>
                <th>deleted</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((n) => (
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
                  <td className="mono" style={{ color: "var(--muted)" }}>
                    {n.deleted_at ? new Date(n.deleted_at).toLocaleString() : "—"}
                  </td>
                  <td>
                    <div className="row-actions">
                      <button className="icon-btn" onClick={() => restore(n.id)}>
                        restore
                      </button>
                      <button className="icon-btn danger" onClick={() => purge(n)}>
                        purge
                      </button>
                    </div>
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
