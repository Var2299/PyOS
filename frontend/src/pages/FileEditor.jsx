import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/client";

export default function FileEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [node, setNode] = useState(null);
  const [content, setContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const readOnly = node && !node.can_edit;

  useEffect(() => {
    api.get(`/nodes/${id}/`).then((res) => {
      setNode(res.data);
      setContent(res.data.content);
    });
  }, [id]);

  async function save() {
    setError("");
    try {
      await api.patch(`/nodes/${id}/`, { content });
      await api.post("/commands/", {
        command: `edit ${node.path}`,
        output: `Saved ${content.length} chars`,
      });
      setDirty(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 1500);
    } catch (e) {
      setError(e.response?.data?.detail || "Could not save — you may not have edit access.");
    }
  }

  if (!node) return <div className="empty">loading…</div>;

  return (
    <>
      <div className="page-head">
        <div className="page-title">
          <span className="dim">{node.path.replace(/\/[^/]*$/, "/")}</span>
          {node.name}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {!node.is_owner && <span className="tag blue">@{node.owner_username}</span>}
          {readOnly && <span className="tag amber">read-only</span>}
          {saved && <span className="tag green">saved</span>}
          {dirty && <span className="tag amber">unsaved</span>}
          <button className="btn ghost sm" onClick={() => navigate("/explorer")}>
            ← Back
          </button>
          {!readOnly && (
            <button className="btn sm" onClick={save} disabled={!dirty}>
              Save
            </button>
          )}
        </div>
      </div>

      {error && <div className="err">{error}</div>}
      {readOnly && (
        <p style={{ color: "var(--amber)", fontFamily: "var(--mono)", fontSize: 12, marginBottom: 10 }}>
          // This file is shared read-only by {node.owner_username}. You can view but not edit it.
        </p>
      )}

      <div className="editor">
        <textarea
          value={content}
          spellCheck={false}
          readOnly={readOnly}
          style={readOnly ? { opacity: 0.75, cursor: "default" } : undefined}
          onChange={(e) => {
            if (readOnly) return;
            setContent(e.target.value);
            setDirty(true);
          }}
          onKeyDown={(e) => {
            if (!readOnly && (e.metaKey || e.ctrlKey) && e.key === "s") {
              e.preventDefault();
              if (dirty) save();
            }
          }}
        />
      </div>
      <p style={{ color: "var(--muted)", fontFamily: "var(--mono)", fontSize: 12, marginTop: 8 }}>
        {content.length} chars · {content.split("\n").length} lines
        {!readOnly && " · ⌘/Ctrl+S to save"}
      </p>
    </>
  );
}
