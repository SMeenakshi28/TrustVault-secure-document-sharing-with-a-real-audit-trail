export default function Sidebar({ selectedRole, selectedView, setSelectedView, form, logout }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-icon">T</span>
        <span>TrustVault</span>
      </div>

      <div className="sidebar-label">WORKSPACE</div>

      <button type="button" className={`sidebar-link ${selectedView === "dashboard" ? "active" : ""}`} onClick={() => setSelectedView("dashboard")}>
        <span>▦</span> Dashboard
      </button>

      {selectedRole === "owner" && (
        <>
          <button type="button" className={`sidebar-link ${selectedView === "documents" ? "active" : ""}`} onClick={() => setSelectedView("documents")}>
            <span>▤</span> My Documents
          </button>
          <button type="button" className={`sidebar-link ${selectedView === "shared" ? "active" : ""}`} onClick={() => setSelectedView("shared")}>
            <span>♧</span> Shared Access
          </button>
          <button type="button" className={`sidebar-link ${selectedView === "activity" ? "active" : ""}`} onClick={() => setSelectedView("activity")}>
            <span>◷</span> Activity Log
          </button>
        </>
      )}

      {selectedRole === "admin" && (
        <>
          <button type="button" className={`sidebar-link ${selectedView === "users" ? "active" : ""}`} onClick={() => setSelectedView("users")}>
            <span>♙</span> People &amp; Access
          </button>
          <button type="button" className={`sidebar-link ${selectedView === "audit_logs" ? "active" : ""}`} onClick={() => setSelectedView("audit_logs")}>
            <span>◷</span> Audit Logs
          </button>
        </>
      )}

      {selectedRole === "viewer" && (
        <button type="button" className={`sidebar-link ${selectedView === "shared_with_me" ? "active" : ""}`} onClick={() => setSelectedView("shared_with_me")}>
          <span>▤</span> Shared With Me
        </button>
      )}

      <div className="sidebar-bottom">
        <div className="profile-avatar">
          {(form.name || form.username || "U").charAt(0).toUpperCase()}
        </div>
        <div className="profile-info">
          <strong>{form.name || form.username || "Demo User"}</strong>
          <span>{selectedRole}</span>
        </div>
        <button className="logout-button" onClick={logout} aria-label="Log out" title="Log out">
          ↪
        </button>
      </div>
    </aside>
  );
}