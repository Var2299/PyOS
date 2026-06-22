import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const PERM_LABEL = {
  private: { text: "private", cls: "" },
  read_only: { text: "read-only", cls: "amber" },
  public: { text: "public", cls: "green" },
};

export default function Explorer() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = !!(user?.is_admin_role || user?.is_staff);
  const [mode, setMode] = useState("mine"); // "mine" | "shared"
  const [path, setPath] = useState([{ id: null, name: "~" }]);
  const [nodes, setNodes] = useState([]);
  const [modal, setModal] = useState(null); // { type } for create
  const [shareModal, setShareModal] = useState(null); // node being shared
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);

  const current = path[path.length - 1];
  const atSharedRoot = mode === "shared" && path.length === 1;

  async function loadDir(parentId) {
    setLoading(true);
    // At the root of "Shared with me", load the shared-with-me list instead.
    if (mode === "shared" && parentId == null) {
      const res = await api.get("/nodes/shared_with_me/");
      setNodes(res.data);
    } else {
      const res = await api.get(`/nodes/?parent=${parentId ?? "root"}`);
      setNodes(res.data);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadDir(current.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current.id, mode]);

  function switchMode(next) {
    if (next === mode) return;
    setMode(next);
    setPath([{ id: null, name: next === "shared" ? "shared" : "~" }]);
  }

  function openNode(node) {
    if (node.node_type === "directory") {
      setPath([...path, { id: node.id, name: node.name }]);
    } else {
      navigate(`/file/${node.id}`);
    }
  }

  function goCrumb(idx) {
    setPath(path.slice(0, idx + 1));
  }

  async function createNode() {
    if (!newName.trim()) return;
    await api.post("/nodes/", {
      name: newName.trim(),
      node_type: modal.type,
      parent: current.id,
      content: "",
    });
    setModal(null);
    setNewName("");
    loadDir(current.id);
  }

  async function remove(node) {
    if (!confirm(`Move "${node.name}" to the recycle bin?`)) return;
    await api.delete(`/nodes/${node.id}/`);
    loadDir(current.id);
  }

  async function setPermission(node, level) {
    await api.patch(`/nodes/${node.id}/`, { permission_level: level });
    setShareModal(null);
    loadDir(current.id);
  }

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>explorer
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {isAdmin && <span className="tag amber">sudo: all workspaces</span>}
          <div className="toggle">
            <button
              className={"toggle-btn" + (mode === "mine" ? " active" : "")}
              onClick={() => switchMode("mine")}
            >
              My files
            </button>
            <button
              className={"toggle-btn" + (mode === "shared" ? " active" : "")}
              onClick={() => switchMode("shared")}
            >
              Shared with me
            </button>
          </div>
        </div>
      </div>

      <div className="crumbs">
        {path.map((p, i) => (
          <span key={i}>
            <span className="seg" onClick={() => goCrumb(i)}>
              {p.name}
            </span>
            {i < path.length - 1 && <span> / </span>}
          </span>
        ))}
      </div>

      {mode === "mine" && (
        <div className="toolbar">
          <button className="btn sm" onClick={() => setModal({ type: "directory" })}>
            + New folder
          </button>
          <button className="btn ghost sm" onClick={() => setModal({ type: "file" })}>
            + New file
          </button>
        </div>
      )}

      {loading ? (
        <div className="empty">loading…</div>
      ) : nodes.length === 0 ? (
        <div className="empty">
          {atSharedRoot
            ? "Nothing has been shared with you yet."
            : mode === "shared"
            ? "This shared folder has no items visible to you."
            : "This folder is empty. Create a file or folder to begin."}
        </div>
      ) : (
        <ul className="node-list">
          {nodes.map((n) => {
            const perm = PERM_LABEL[n.permission_level] || PERM_LABEL.private;
            const shared = !n.is_owner;
            return (
              <li className="node-row" key={n.id}>
                <span className={"ic" + (n.node_type === "file" ? " file" : "")}>
                  {n.node_type === "directory" ? "▣" : "≡"}
                </span>
                <span className="nm" onClick={() => openNode(n)}>
                  {n.name}
                </span>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {n.permission_level !== "private" && (
                    <span className={"tag " + perm.cls}>{perm.text}</span>
                  )}
                  {shared && (
                    <span className="tag blue" title="Owned by another user">
                      @{n.owner_username}
                    </span>
                  )}
                  <span className="meta">
                    {n.node_type === "directory" ? `${n.children_count} items` : "file"}
                  </span>
                </div>
                <div className="row-actions">
                  {n.node_type === "file" && (
                    <button className="icon-btn" onClick={() => navigate(`/file/${n.id}`)}>
                      open
                    </button>
                  )}
                  {n.is_protected ? (
                    <span className="tag" title="System directory — cannot be deleted">
                      system
                    </span>
                  ) : n.is_owner || isAdmin ? (
                    <>
                      <button className="icon-btn" onClick={() => setShareModal(n)}>
                        share
                      </button>
                      <button className="icon-btn danger" onClick={() => remove(n)}>
                        del
                      </button>
                    </>
                  ) : (
                    <span
                      className="mono"
                      style={{ color: "var(--muted)", fontSize: 11, padding: "4px 8px" }}
                    >
                      {n.can_edit ? "shared" : "view only"}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {modal && (
        <div className="modal-bg" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>New {modal.type === "directory" ? "folder" : "file"}</h3>
            <div className="field">
              <label>name</label>
              <input
                autoFocus
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createNode()}
                placeholder={modal.type === "directory" ? "my-folder" : "file.txt"}
              />
            </div>
            <div className="row">
              <button className="btn" onClick={createNode}>
                Create
              </button>
              <button className="btn ghost" onClick={() => setModal(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {shareModal && (
        <div className="modal-bg" onClick={() => setShareModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Sharing — {shareModal.name}</h3>
            <p style={{ color: "var(--muted)", fontSize: 12, marginBottom: 16 }}>
              Choose who else can access this {shareModal.node_type}.
            </p>
            {[
              ["private", "Private", "Only you can see it."],
              ["read_only", "Read-only", "Other users can view but not change it."],
              ["public", "Public", "Other users can view and edit it."],
            ].map(([val, title, desc]) => (
              <button
                key={val}
                className="perm-option"
                data-active={shareModal.permission_level === val}
                onClick={() => setPermission(shareModal, val)}
              >
                <strong>{title}</strong>
                <span>{desc}</span>
              </button>
            ))}
            <div className="row">
              <button className="btn ghost" onClick={() => setShareModal(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
