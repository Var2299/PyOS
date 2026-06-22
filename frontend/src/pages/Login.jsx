import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(form.username, form.password);
      else await register(form.username, form.email, form.password);
      navigate("/");
    } catch (err) {
      const data = err.response?.data;
      setError(
        data?.detail ||
          (data && typeof data === "object" ? Object.values(data).flat().join(" ") : "Something went wrong")
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <div className="brand">
          pyos<span className="caret">_</span>
        </div>
        <div className="auth-sub">
          {mode === "login" ? "// sign in to your workspace" : "// create a new account"}
        </div>

        {error && <div className="err">{error}</div>}

        {mode === "register" && (
          <div className="info-note">
            The first account created becomes the system administrator. Every
            account after that is a standard user.
          </div>
        )}

        <div className="field">
          <label>username</label>
          <input value={form.username} onChange={upd("username")} autoFocus required />
        </div>
        {mode === "register" && (
          <div className="field">
            <label>email</label>
            <input type="email" value={form.email} onChange={upd("email")} />
          </div>
        )}
        <div className="field">
          <label>password</label>
          <input
            type="password"
            value={form.password}
            onChange={upd("password")}
            required
            minLength={6}
          />
        </div>

        <button className="btn" disabled={busy}>
          {busy ? "..." : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <div className="switch-link">
          {mode === "login" ? (
            <>
              No account?{" "}
              <a onClick={() => setMode("register")} style={{ cursor: "pointer" }}>
                Register
              </a>
            </>
          ) : (
            <>
              Have an account?{" "}
              <a onClick={() => setMode("login")} style={{ cursor: "pointer" }}>
                Sign in
              </a>
            </>
          )}
        </div>
      </form>
    </div>
  );
}
