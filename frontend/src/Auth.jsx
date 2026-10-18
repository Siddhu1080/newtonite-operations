import { useState } from "react";
import { ArrowRight, Eye, EyeOff, Leaf, LockKeyhole, Mail, UserRound } from "lucide-react";
import { login, register } from "./api";
import "./Auth.css";

export default function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "register") {
        await register(name.trim(), email.trim(), password);
      }

      await login(email.trim(), password);
      await onLogin();
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function changeMode(nextMode) {
    setMode(nextMode);
    setError("");
  }

  return (
    <main className="auth-page">
      <section className="auth-brand-panel">
        <div className="auth-brand">
          <div className="auth-logo"><Leaf size={22} /></div>
          <div>
            <strong>newtonite</strong>
            <span>OPERATIONS</span>
          </div>
        </div>

        <div className="auth-message">
          <span className="auth-kicker">A BETTER WAY TO WORK</span>
          <h1>Good work starts with a little more clarity.</h1>
          <p>Bring your team's work, conversations, and progress together in one place.</p>
          <div className="auth-feature">
            <span><LockKeyhole size={17} /></span>
            <div>
              <strong>Your workspace, organized</strong>
              <p>Keep tasks and team collaboration connected.</p>
            </div>
          </div>
        </div>

        <span className="auth-copyright">Newtonite Operations</span>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-wrap">
          <div className="auth-mobile-brand">
            <div className="auth-logo"><Leaf size={21} /></div>
            <strong>newtonite</strong>
          </div>

          <span className="auth-kicker">
            {mode === "login" ? "WELCOME BACK" : "GET STARTED"}
          </span>

          <h2>{mode === "login" ? "Sign in to your workspace" : "Create your account"}</h2>
          <p className="auth-intro">
            {mode === "login"
              ? "Enter your details below to continue."
              : "A few details and you're ready to get started."}
          </p>

          <div className="auth-tabs">
            <button
              type="button"
              className={mode === "login" ? "selected" : ""}
              onClick={() => changeMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              className={mode === "register" ? "selected" : ""}
              onClick={() => changeMode("register")}
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {mode === "register" && (
              <label className="auth-label">
                Full name
                <span className="auth-input-wrap">
                  <UserRound size={17} />
                  <input
                    autoComplete="name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Your name"
                    maxLength={100}
                    required
                  />
                </span>
              </label>
            )}

            <label className="auth-label">
              Email address
              <span className="auth-input-wrap">
                <Mail size={17} />
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </span>
            </label>

            <label className="auth-label">
              Password
              <span className="auth-input-wrap">
                <LockKeyhole size={17} />
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={mode === "register" ? "At least 8 characters" : "Enter your password"}
                  minLength={mode === "register" ? 8 : undefined}
                  maxLength={128}
                  required
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </span>
            </label>

            {error && <div className="auth-error" role="alert">{error}</div>}

            <button className="auth-submit" type="submit" disabled={loading}>
              {loading
                ? "Please wait..."
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>

          <p className="auth-switch">
            {mode === "login" ? "New to Newtonite?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => changeMode(mode === "login" ? "register" : "login")}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>

          <p className="auth-security">
            <LockKeyhole size={13} />
            Your workspace is protected by secure authentication.
          </p>
        </div>
      </section>
    </main>
  );
}