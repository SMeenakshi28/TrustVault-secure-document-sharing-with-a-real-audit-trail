import { useState } from "react";
import DashboardLayout from "../components/DashboardLayout";

function getExpirationDate(expiration) {
  if (!expiration || expiration.toLowerCase() === "no expiry") return null;

  const date = new Date(`${expiration}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export default function ViewerDashboard({ form, selectedRole, logout, sharedDocuments = [] }) {
  const [selectedView, setSelectedView] = useState("dashboard");
  const [searchQuery, setSearchQuery] = useState("");
  const viewTitle = selectedView === "dashboard" ? "Dashboard" : "Shared With Me";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expirationLimit = new Date(today);
  expirationLimit.setDate(expirationLimit.getDate() + 30);
  const activeDocuments = sharedDocuments.filter((document) => {
    const expirationDate = getExpirationDate(document.expiration);
    return !expirationDate || expirationDate >= today;
  });
  const viewAccessCount = activeDocuments.filter((document) =>
    document.permission?.toLowerCase().includes("view"),
  ).length;
  const downloadAccessCount = activeDocuments.filter((document) =>
    document.permission?.toLowerCase().includes("download"),
  ).length;
  const expiringSoonCount = activeDocuments.filter((document) => {
    const expirationDate = getExpirationDate(document.expiration);
    return expirationDate && expirationDate <= expirationLimit;
  }).length;
  const filteredDocuments = sharedDocuments.filter((document) =>
    `${document.name || ""} ${document.owner || ""}`.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <DashboardLayout viewTitle={viewTitle} selectedRole={selectedRole} selectedView={selectedView} setSelectedView={setSelectedView} form={form} logout={logout}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">VIEWER WORKSPACE</p>
          <h1>{selectedView === "dashboard" ? "Your shared documents" : viewTitle}</h1>
          <p className="muted">Documents shared with you, with permissions set by their owners.</p>
        </div>
        <span className="role-pill">{selectedRole}</span>
      </div>

      {selectedView === "dashboard" && (
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
      )}

      <section className="panel viewer-documents">
        <div className="panel-heading">
          <div>
            <h2>Shared with me</h2>
            <p className="muted">Only files shared with your demo account are listed.</p>
          </div>
          <button type="button" className="primary-button" onClick={() => setSelectedView("shared_with_me")}>
            Browse Shared files <span aria-hidden="true">→</span>
          </button>
        </div>
        <div className="viewer-search">
          <input
            type="search"
            aria-label="Search shared files"
            placeholder="Search shared files..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </div>
        <div className="activity-table-wrap">
          <table className="activity-table viewer-table">
            <thead>
              <tr>
                <th scope="col">Document</th>
                <th scope="col">Shared By</th>
                <th scope="col">Permission</th>
                <th scope="col">Expires</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocuments.length === 0 ? (
                <tr>
                  <td className="activity-empty" colSpan="4">
                    Nothing Here
                    {searchQuery && <span className="viewer-empty-hint"> — no shared files match your search.</span>}
                  </td>
                </tr>
              ) : filteredDocuments.map((document) => (
                <tr key={document.id}>
                  <td className="activity-action">{document.name}</td>
                  <td>{document.owner}</td>
                  <td>{document.permission}</td>
                  <td>{document.expiration}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </DashboardLayout>
  );
}
