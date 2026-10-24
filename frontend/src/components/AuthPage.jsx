import { useState } from "react";
import { apiRequest } from "../api";

export default function AuthPage({
  page,
  setPage,
  form,
  setForm,
  setSelectedRole,
  setAccessToken,
  message,
  setMessage,
}) {
  const [showPassword, setShowPassword] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptedPolicies, setAcceptedPolicies] = useState(false);
  const [policyTab, setPolicyTab] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    setMessage("");
  }

  async function handleSignup(event) {
    event.preventDefault();
    setMessage("");

    if (!form.name.trim() || !form.email.trim() || !form.password) {
      setMessage("Please fill in all fields.");
      return;
    }

    const password = form.password;
    const passwordErrors = [];

    if (password.length < 8) {
      passwordErrors.push("at least 8 characters");
    }
    if (!/[A-Z]/.test(password)) {
      passwordErrors.push("one capital letter");
    }
    if (!/[a-z]/.test(password)) {
      passwordErrors.push("one small letter");
    }
    if (!/[0-9]/.test(password)) {
      passwordErrors.push("one number");
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
      passwordErrors.push("one special character");
    }

    if (passwordErrors.length > 0) {
      setMessage(
        "Password must contain " +
          passwordErrors.join(", ") +
          "."
      );
      return;
    }

    if (form.password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    if (!acceptedPolicies) {
      setMessage("Please agree to the Terms & Conditions and Privacy Policy.");
      return;
    }

    setIsSubmitting(true);

    try {
      await apiRequest("/auth/signup", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
        }),
      });

      setForm((previous) => ({
        ...previous,
        password: "",
      }));
      setConfirmPassword("");
      setAcceptedPolicies(false);

      setPage("login");
      setMessage("Account created successfully. Please sign in.");
    } catch (error) {
      setMessage(error.message || "Signup failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setMessage("");

    if (!form.email.trim() || !form.password) {
      setMessage("Please enter your email and password.");
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.email.trim(),
          password: form.password,
        }),
      });

      setAccessToken(data.access_token);
      setSelectedRole(data.user.role);

      setForm({
        name: data.user.name || "",
        username: "",
        email: data.user.email || "",
        password: "",
      });

      setPage("dashboard");
      setMessage("");
    } catch (error) {
      setMessage(error.message || "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
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

            <h1>
              Your documents.
              <br />
              Your control.
            </h1>

            <p>
              Share sensitive files with confidence. Control who gets
              access and keep a record of document activity.
            </p>

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

          <p className="visual-footer">
            Secure document sharing · TrustVault
          </p>
        </div>
      </section>

      <section className="auth-form-side">
        <div className="auth-form-container">
          <div className="mobile-brand brand">
            <span className="brand-icon">T</span>
            <span>TrustVault</span>
          </div>

          <div className="auth-heading">
            <p className="eyebrow">
              {page === "login" ? "WELCOME BACK" : "GET STARTED"}
            </p>

            <h2>
              {page === "login"
                ? "Sign in to TrustVault"
                : "Create your account"}
            </h2>

            <p>
              {page === "login"
                ? "Enter your details to access your workspace."
                : "Create a secure account to get started."}
            </p>
          </div>

          <div className="auth-switch">
            <button
              type="button"
              className={page === "login" ? "switch-active" : ""}
              onClick={() => {
                setMessage("");
                setPage("login");
              }}
            >
              Sign in
            </button>

            <button
              type="button"
              className={page === "signup" ? "switch-active" : ""}
              onClick={() => {
                setMessage("");
                setPage("signup");
              }}
            >
              Sign up
            </button>
          </div>

          <form
            className="auth-form"
            onSubmit={page === "login" ? handleLogin : handleSignup}
          >
            {page === "signup" && (
              <>
                <label htmlFor="name">Full name</label>
                <input
                  id="name"
                  name="name"
                  placeholder="Enter your full name"
                  value={form.name}
                  onChange={handleChange}
                  autoComplete="name"
                  required
                />
              </>
            )}

            <label htmlFor="email">Email address</label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
              required
            />

            <div className="password-label">
              <label htmlFor="password">Password</label>
            </div>

            <div className="password-wrapper">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={form.password}
                onChange={handleChange}
                autoComplete={
                  page === "login"
                    ? "current-password"
                    : "new-password"
                }
                minLength={page === "signup" ? 8 : undefined}
                required
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() =>
                  setShowPassword((previous) => !previous)
                }
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>

            {page === "signup" && (
              <>
                <div className="password-label">
                  <label htmlFor="confirm-password">Confirm password</label>
                </div>
                <div className="password-wrapper">
                  <input
                    id="confirm-password"
                    name="confirmPassword"
                    type={showPassword ? "text" : "password"}
                    placeholder="Re-enter your password"
                    value={confirmPassword}
                    onChange={(event) => {
                      setConfirmPassword(event.target.value);
                      setMessage("");
                    }}
                    autoComplete="new-password"
                    minLength={8}
                    required
                  />
                </div>
                {confirmPassword && form.password !== confirmPassword && (
                  <p className="form-message" role="alert">Passwords do not match.</p>
                )}
                <p className="auth-legal">
                  New accounts start with Viewer access. Owner and Admin roles
                  must be assigned by an authorized administrator.
                </p>
                <label className="policy-consent">
                  <input
                    type="checkbox"
                    checked={acceptedPolicies}
                    onChange={(event) => {
                      setAcceptedPolicies(event.target.checked);
                      setMessage("");
                    }}
                    required
                  />
                  <span>
                    I agree to the{" "}
                    <button type="button" className="inline-policy-link" onClick={() => setPolicyTab("terms")}>
                      Terms &amp; Conditions
                    </button>{" "}and{" "}
                    <button type="button" className="inline-policy-link" onClick={() => setPolicyTab("privacy")}>
                      Privacy Policy
                    </button>.
                  </span>
                </label>
              </>
            )}

            {message && (
              <p className="form-message" role="alert">
                {message}
              </p>
            )}

            <button
              type="submit"
              className="primary-button submit-button"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? "Please wait..."
                : page === "login"
                  ? "Sign in"
                  : "Create account"}

              {!isSubmitting && <span>→</span>}
            </button>
          </form>
        </div>
      </section>
      {page === "signup" && policyTab && (
        <div className="policy-modal-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setPolicyTab("");
        }}>
          <section className="policy-modal" role="dialog" aria-modal="true" aria-labelledby="policy-title">
            <header className="policy-modal-header">
              <div>
                <p className="eyebrow">TRUSTVAULT · POLICY v1.0</p>
                <h2 id="policy-title">{policyTab === "terms" ? "Terms & Conditions" : "Privacy Policy"}</h2>
                <p>Effective date: October 23, 2026</p>
              </div>
              <button type="button" className="policy-close" onClick={() => setPolicyTab("")} aria-label="Close policy">×</button>
            </header>
            <nav className="policy-tabs" aria-label="Policy sections">
              <button type="button" className={policyTab === "terms" ? "active" : ""} onClick={() => setPolicyTab("terms")}>Terms &amp; Conditions</button>
              <button type="button" className={policyTab === "privacy" ? "active" : ""} onClick={() => setPolicyTab("privacy")}>Privacy Policy</button>
            </nav>
            <div className="policy-modal-content">
              {policyTab === "terms" ? (
                <>
                  <p>These terms explain the rules for using TrustVault, a platform for managing documents and sharing them with authorized users.</p>
                  <h3>1. Account use</h3><p>Provide accurate registration details, protect your password, and use only your own account. Notify the platform administrator if you suspect unauthorized access.</p>
                  <h3>2. Document ownership and uploads</h3><p>You are responsible for the documents you upload and must have the right to store or share them. Do not upload unlawful, harmful, or malicious content.</p>
                  <h3>3. Sharing and access permissions</h3><p>Owners should share documents only with intended recipients. Viewers may access documents made available to them. All users must respect permissions and must not try to access documents or roles they have not been granted.</p>
                  <h3>4. Activity records</h3><p>TrustVault may record document and account actions to support accountability and help investigate security issues. Users must not attempt to interfere with these records.</p>
                  <h3>5. Prohibited activity</h3><p>Do not bypass authentication, misuse another user's information, upload malicious files, or disrupt the service.</p>
                  <h3>6. Availability and account restrictions</h3><p>The service may be interrupted or changed. Accounts may be restricted for security or misuse. Retention of documents and activity records is subject to the platform's implemented data-handling rules.</p>
                  <h3>7. Updates</h3><p>These terms may change as TrustVault evolves. The displayed version and effective date should be updated when revised.</p>
                </>
              ) : (
                <>
                  <p>This policy describes the information TrustVault may process to provide account access and controlled document sharing.</p>
                  <h3>1. Information processed</h3><p>This may include your name, email address, account role and status, password hash, document metadata and content, sharing permissions, and activity records generated by the application.</p>
                  <h3>2. Why information is used</h3><p>Information is used to authenticate accounts, enforce permissions, display authorized documents, manage accounts, maintain relevant activity records, and troubleshoot problems.</p>
                  <h3>3. Document confidentiality</h3><p>Document access is intended to be limited to the owner and users authorized by the applicable sharing permissions. Backend authorization is essential to enforcing these restrictions.</p>
                  <h3>4. Activity records</h3><p>TrustVault may retain event details such as account identifiers, document references, action types, timestamps, and outcomes where those events are implemented.</p>
                  <h3>5. Storage and retention</h3><p>Account records, documents, permissions, and audit records may be stored separately. Deactivation and account deletion can affect these records differently; the application should not promise immediate erasure of every related record unless it is implemented.</p>
                  <h3>6. Safeguards and limitations</h3><p>TrustVault uses authentication and access controls intended to reduce unauthorized access, but no software service can guarantee the elimination of every security risk.</p>
                  <h3>7. Policy updates and questions</h3><p>This policy may be revised when the application's practices change. For questions, contact the TrustVault project administrator through the support contact provided by the application.</p>
                </>
              )}
            </div>
            <footer className="policy-modal-footer">
              <span>TrustVault · Document access and accountability</span>
              <button type="button" className="primary-button" onClick={() => setPolicyTab("")}>Close</button>
            </footer>
          </section>
        </div>
      )}
    </main>
  );
}