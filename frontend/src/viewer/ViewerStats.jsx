export default function ViewerStats({ activeDocuments, today, expirationLimit, getExpirationDate }) {
  const viewAccessCount = activeDocuments.filter((document) =>
    document.permission.toLowerCase().includes("view")
  ).length;

  const downloadAccessCount = activeDocuments.filter((document) =>
    document.permission.toLowerCase().includes("download")
  ).length;

  const expiringSoonCount = activeDocuments.filter((document) => {
    const expirationDate = getExpirationDate(document.expiration);
    return expirationDate && expirationDate >= today && expirationDate <= expirationLimit;
  }).length;

  return (
    <section className="viewer-summary-grid" aria-label="Shared document summary">
      <article className="stat-card">
        <span className="stat-icon">▤</span>
        <p>Shared with me</p>
        <h2>{activeDocuments.length}</h2>
        <span className="stat-note">Active file shares</span>
      </article>

      <article className="stat-card">
        <span className="stat-icon green">◉</span>
        <p>View access</p>
        <h2>{viewAccessCount}</h2>
        <span className="stat-note">Available to open</span>
      </article>

      <article className="stat-card">
        <span className="stat-icon purple">⇩</span>
        <p>Download access</p>
        <h2>{downloadAccessCount}</h2>
        <span className="stat-note">Allowed by owner</span>
      </article>

      <article className="stat-card">
        <span className="stat-icon amber">◷</span>
        <p>Expiring soon</p>
        <h2>{expiringSoonCount}</h2>
        <span className="stat-note">Within 30 days</span>
      </article>
    </section>
  );
}