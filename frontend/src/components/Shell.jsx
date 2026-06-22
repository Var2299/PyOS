import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/", ic: "▸", label: "Dashboard", end: true },
  { to: "/explorer", ic: "▤", label: "Explorer" },
  { to: "/search", ic: "⌕", label: "Search" },
  { to: "/history", ic: "↻", label: "Terminal" },
  { to: "/recycle", ic: "⌫", label: "Recycle Bin" },
  { to: "/logs", ic: "≡", label: "Logs" },
];

// Only revealed when the logged-in user is an admin.
const ADMIN_NAV = [
  { to: "/admin", ic: "★", label: "Admin Panel" },
  { to: "/workspaces", ic: "❏", label: "All Workspaces" },
];

export default function Shell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = !!(user?.is_admin_role || user?.is_staff);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          pyos<span className="caret">_</span>
        </div>
        <nav>
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
            >
              <span className="ic">{n.ic}</span>
              {n.label}
            </NavLink>
          ))}
          {isAdmin &&
            ADMIN_NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) => "nav-item admin" + (isActive ? " active" : "")}
              >
                <span className="ic">{n.ic}</span>
                {n.label}
              </NavLink>
            ))}
        </nav>
        <div className="sidebar-foot">
          <div className="user-chip">
            {user?.username}
            {user?.is_admin_role ? " · admin" : ""}
          </div>
          <button
            className="btn ghost sm"
            style={{ width: "100%", marginTop: 6 }}
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
