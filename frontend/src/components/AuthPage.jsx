import { useState } from "react";

const roles = ["admin", "owner", "viewer"];

export default function AuthPage({ page, setPage, form, setForm, selectedRole, setSelectedRole, message, setMessage }) {
  const [showPassword, setShowPassword] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
    setMessage("");
  }

  function handleSignup(event) {
    event.preventDefault();

    if (!form.name.trim() || !form.username.trim() || !form.email.trim() || !form.password) {
      setMessage("Please fill in all fields.");
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setMessage("Please enter a valid email address.");
      return;
    }

    const password = form.password;
    const passwordErrors = [];
    if (password.length < 8) passwordErrors.push("At least 8 characters");
    if (!/[A-Z]/.test(password)) passwordErrors.push("At least one capital letter (A-Z)");
    if (!/[a-z]/.test(password)) passwordErrors.push("At least one small letter (a-z)");
    if (!/[0-9]/.test(password)) passwordErrors.push("At least one number (0-9)");
    if (!/[^A-Za-z0-9]/.test(password)) passwordErrors.push("At least one special character");

    if (passwordErrors.length > 0) {
      setMessage("Password must contain: " + passwordErrors.join(", ") + ".");
      return;
    }

    setPage("dashboard");
    setMessage("");
  }

  function handleLogin(event) {
    event.preventDefault();
    setMessage("Login is not connected to authentication yet. Use Sign up to preview the dashboard.");
  }

  return (
    <main className="auth-page">
      <section className="auth-visual">
        <div className="visual-content">
          <div className="brand brand-light">
            <span className="brand-icon">T</span>
            <span>TrustVault</span>
          </div>
          <div className="visual-message">
            <span className="visual-tag">
              <span className="status-dot" /> CONFIDENTIAL BY DESIGN
            </span>
            <h1>Your documents.<br />Your control.</h1>
            <p>Share sensitive files with confidence. Control who gets access and keep a record of document activity.</p>
            <div className="visual-feature">
              <span className="feature-icon">✓</span>
              <div>
                <strong>Controlled access</strong>
                <span>Permissions for the right people.</span>
              </div>
            </div>
            <div className="visual-feature">
              <span className="feature-icon">◷</span>
              <div>
                <strong>Accountability</strong>
                <span>Designed for traceable document activity.</span>
              </div>
            </div>
          </div>
          <p className="visual-footer">Secure document sharing · TrustVault</p>
        </div>
      </section>

      <section className="auth-form-side">
        <div className="auth-form-container">
          <div className="mobile-brand brand">
            <span className="brand-icon">T</span>
            <span>TrustVault</span>
          </div>

          <div className="auth-heading">
            <p className="eyebrow">{page === "login" ? "WELCOME BACK" : "GET STARTED"}</p>
            <h2>{page === "login" ? "Sign in to TrustVault" : "Create your account"}</h2>
            <p>{page === "login" ? "Enter your details to access your workspace." : "Set up your account and choose your workspace role."}</p>
          </div>

          <div className="auth-switch">
            <button type="button" className={page === "login" ? "switch-active" : ""} onClick={() => { setMessage(""); setPage("login"); }}>Sign in</button>
            <button type="button" className={page === "signup" ? "switch-active" : ""} onClick={() => { setMessage(""); setPage("signup"); }}>Sign up</button>
          </div>

          <form className="auth-form" onSubmit={page === "login" ? handleLogin : handleSignup}>
            {page === "signup" && (
              <>
                <label htmlFor="name">Full name</label>
                <input id="name" name="name" placeholder="Enter your full name" value={form.name} onChange={handleChange} autoComplete="name" required />
                <label htmlFor="username">Username</label>
                <input id="username" name="username" placeholder="Choose a username" value={form.username} onChange={handleChange} autoComplete="username" required />
              </>
            )}

            <label htmlFor="email">{page === "login" ? "Email or username" : "Email address"}</label>
            <input id="email" name="email" type={page === "login" ? "text" : "email"} placeholder={page === "login" ? "Enter your email or username" : "you@example.com"} value={form.email} onChange={handleChange} autoComplete={page === "login" ? "username" : "email"} required />

            <div className="password-label">
              <label htmlFor="password">Password</label>
              {page === "login" && <span className="helper-text"></span>}
            </div>

            <div className="password-wrapper">
              <input id="password" name="password" type={showPassword ? "text" : "password"} placeholder="Enter your password" value={form.password} onChange={handleChange} autoComplete={page === "login" ? "current-password" : "new-password"} minLength={page === "signup" ? 8 : undefined} required />
              <button type="button" className="password-toggle" onClick={() => setShowPassword((prev) => !prev)}>{showPassword ? "Hide" : "Show"}</button>
            </div>

            {page === "signup" && (
              <fieldset className="role-fieldset">
                <legend>Choose your role</legend>
                <div className="role-options">
                  {roles.map((role) => (
                    <label key={role} className={`role-option ${selectedRole === role ? "role-selected" : ""}`}>
                      <input type="radio" name="role" value={role} checked={selectedRole === role} onChange={() => { setSelectedRole(role); setMessage(""); }} />
                      <span className="radio-indicator" />
                      <span className="role-option-text">
                        <strong>{role.charAt(0).toUpperCase() + role.slice(1)}</strong>
                        <small>{role === "admin" ? "Administration" : role === "owner" ? "Manage documents" : "View shared files"}</small>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            {message && <p className="form-message" role="alert">{message}</p>}

            <button type="submit" className="primary-button submit-button">{page === "login" ? "Sign in" : "Create account"} <span>→</span></button>
          </form>
        </div>
      </section>
    </main>
  );
}