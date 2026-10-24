export default function AdminStats({
  usersCount,
  documentCount,
  auditLogsCount,
  deniedAttempts,
  loading,
}) {
  return (
    <section className="admin-stats-grid">
      <article className="stat-card">
        <span className="stat-icon">♙</span>
        <p>Registered users</p>
        <h2>{loading ? "—" : usersCount}</h2>
        <span className="stat-note">People in your workspace</span>
      </article>

      <article className="stat-card">
        <span className="stat-icon purple">▤</span>
        <p>Total documents</p>
        <h2>{loading ? "—" : documentCount}</h2>
        <span className="stat-note">Active documents in the workspace</span>
      </article>

      <article className="stat-card">
        <span className="stat-icon green">◷</span>
        <p>Security events</p>
        <h2>{loading ? "—" : auditLogsCount}</h2>
        <span className="stat-note">Recorded audit log entries</span>
      </article>

      <article className="stat-card">
        <span className="stat-icon red">⊘</span>
        <p>Denied attempts</p>
        <h2>{loading ? "—" : deniedAttempts}</h2>
        <span className="stat-note">Events explicitly marked denied or failed</span>
      </article>
    </section>
  );
}