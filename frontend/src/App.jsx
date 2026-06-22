import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Shell from "./components/Shell";
import Dashboard from "./pages/Dashboard";
import Explorer from "./pages/Explorer";
import FileEditor from "./pages/FileEditor";
import Search from "./pages/Search";
import CommandHistory from "./pages/CommandHistory";
import RecycleBin from "./pages/RecycleBin";
import Logs from "./pages/Logs";
import AdminPanel from "./pages/AdminPanel";
import AllWorkspaces from "./pages/AllWorkspaces";

function Protected({ children }) {
  const { isAuthed } = useAuth();
  return isAuthed ? children : <Navigate to="/login" replace />;
}

function AdminOnly({ children }) {
  const { user } = useAuth();
  const isAdmin = user?.is_admin_role || user?.is_staff;
  return isAdmin ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Shell />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="explorer" element={<Explorer />} />
        <Route path="file/:id" element={<FileEditor />} />
        <Route path="search" element={<Search />} />
        <Route path="history" element={<CommandHistory />} />
        <Route path="recycle" element={<RecycleBin />} />
        <Route path="logs" element={<Logs />} />
        <Route
          path="admin"
          element={
            <AdminOnly>
              <AdminPanel />
            </AdminOnly>
          }
        />
        <Route
          path="workspaces"
          element={
            <AdminOnly>
              <AllWorkspaces />
            </AdminOnly>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
