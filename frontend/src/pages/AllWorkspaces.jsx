import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

const PERM_LABEL = {
  private: { text: "private", cls: "" },
  read_only: { text: "read-only", cls: "amber" },
  public: { text: "public", cls: "green" },
};

export default function AllWorkspaces() {
  const navigate = useNavigate();
  // Two-level navigation:
  //   level "users": top screen, list of users as folders
  //   level "tree":  browsing a selected user's filesystem
  const [users, setUsers] = useState([]);
  const [activeUser, setActiveUser] = useState(null); // {id, username}
  // path within the active user's tree; first crumb is the username (id=null=root)
  const [path, setPath] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [newName, setNewName] = useState("");

  const inTree = !!activeUser;
  const current = path[path.length - 1] || { id: null };

  async function loadUsers() {
    setLoading(true);
    const res = await api.get("/nodes/workspaces/");
    setUsers(res.data);
    setLoading(false);
  }

  async function loadTree(userId, parentId) {
    setLoading(true);
    const q = parentId == null ? "" : `&parent=${parentId}`;
    const res = await api.get(`/nodes/workspace/?user=${userId}${q}`);
    setNodes(res.data);
    setLoading(false);
  }

  useEffect(() => {
    loadUsers();
  }, []);

  useEffect(() => {
    if (activeUser) loadTree(activeUser.id, current.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeUser, current.id]);

  function openUser(u) {
    setActiveUser({ id: u.id, username: u.username });
    setPath([{ id: null, name: u.username }]);
  }

  function openNode(n) {
    if (n.node_type === "directory") {
      setPath([...path, { id: n.id, name: n.name }]);
    } else {
      navigate(`/file/${n.id}`); // admin can edit any file (sudo)
    }
  }

  function goCrumb(idx) {
    if (idx === -1) {
      // back to the user list
      setActiveUser(null);
      setPath([]);
      loadUsers();
      return;
    }
    setPath(path.slice(0, idx + 1));
  }

  async function createNode() {
    if (!newName.trim()) return;
    await api.post("/nodes/", {
      name: newName.trim(),
      node_type: modal.type,
      parent: current.id,
      content: "",
      owner_id: activeUser.id, // node belongs to the workspace's user
    });
    setModal(null);
    setNewName("");
    loadTree(activeUser.id, current.id);
  }

  async function remove(node) {
    if (!confirm(`Move "${node.name}" to ${activeUser.username}'s recycle bin?`)) return;
    try {
      await api.delete(`/nodes/${node.id}/`);
      loadTree(activeUser.id, current.id);
    } catch (e) {
      alert(e.response?.data?.detail || "Could not delete this item.");
    }
  }

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">~/</span>all workspaces
        </div>
        <span className="tag amber">admin · full access</span>
      </div>

      <p style={{ color: "var(--muted)", marginBottom: 16, fontFamily: "var(--mono)", fontSize: 13 }}>
        {inTree
          ? `Browsing ${activeUser.username}'s workspace — you can view, create, edit and delete anything here.`
          : "Every user's workspace. Open one to browse and manage their files."}
      </p>

      {/* Breadcrumbs (only when inside a workspace) */}
      {inTree && (
        <div className="crumbs">
          <span className="seg" onClick={() => goCrumb(-1)}>
            workspaces
          </span>
          {path.map((p, i) => (
            <span key={i}>
              <span> / </span>
              <span className="seg" onClick={() => goCrumb(i)}>
                {p.name}
              </span>
            </span>
          ))}
        </div>
      )}

      {/* Toolbar (only when inside a folder of a workspace) */}
      {inTree && (
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
      ) : !inTree ? (
        /* ---- USER LIST ---- */
        users.length === 0 ? (
          <div className="empty">No users yet.</div>
        ) : (
          <ul className="node-list">
            {users.map((u) => (
              <li className="node-row" key={u.id}>
                <span className="ic" style={{ color: "var(--violet)" }}>
                  ◈
                </span>
                <span className="nm" onClick={() => openUser(u)}>
                  {u.username}
                </span>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {u.is_admin && <span className="tag amber">admin</span>}
                  <span className="meta">
                    {u.files} files · {u.directories} folders
                  </span>
                </div>
                <div className="row-actions">
                  <button className="icon-btn" onClick={() => openUser(u)}>
                    open
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : /* ---- USER'S TREE ---- */ nodes.length === 0 ? (
        <div className="empty">This folder is empty.</div>
      ) : (
        <ul className="node-list">
          {nodes.map((n) => {
            const perm = PERM_LABEL[n.permission_level] || PERM_LABEL.private;
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
                  ) : (
                    <button className="icon-btn danger" onClick={() => remove(n)}>
                      del
                    </button>
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
            <h3>
              New {modal.type === "directory" ? "folder" : "file"} in {activeUser.username}'s
              workspace
            </h3>
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
    </>
  );
}
