import { useCallback, useState } from "react";
import { apiRequest } from "../api";

function formatDate(value) {
  if (!value) return "No expiry";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString();
}

export default function SharedAccess({
  sharedUsers,
  setSharedUsers,
  documents,
  accessToken,
  initialLoading,
}) {
  const [showAddUser, setShowAddUser] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [revokingShareId, setRevokingShareId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadShares = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await apiRequest("/owner/shares", {}, accessToken);
      if (!Array.isArray(data)) {
        throw new Error("The server returned an invalid share list.");
      }
      setSharedUsers(data);
    } catch (loadError) {
      setError(loadError.message || "Could not load shared access.");
    } finally {
      setLoading(false);
    }
  }, [accessToken, setSharedUsers]);

  async function addUser(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setError("");
    setMessage("");

    const formData = new FormData(event.currentTarget);
    const documentId = String(formData.get("document_id") || "");
    const expiration = new Date(String(formData.get("expiration") || ""));
    if (!documentId || Number.isNaN(expiration.getTime()) || expiration <= new Date()) {
      setError("Select a document and choose a future expiration date and time.");
      return;
    }

    const document = documents.find((item) => item.id === documentId);
    if (!document) {
      setError("The selected document is not available in your library.");
      return;
    }

    setSubmitting(true);
    try {
      await apiRequest(
        `/documents/${encodeURIComponent(documentId)}/share`,
        {
          method: "POST",
          body: JSON.stringify({
            recipient_name: String(formData.get("name") || "").trim(),
            recipient_email: String(formData.get("email") || "").trim(),
            expires_at: expiration.toISOString(),
            can_download: formData.get("can_download") === "on",
          }),
        },
        accessToken
      );
      form.reset();
      setShowAddUser(false);
      setMessage(`${document.filename} was shared successfully.`);
      await loadShares();
    } catch (submitError) {
      setError(submitError.message || "Could not share this document.");
    } finally {
      setSubmitting(false);
    }
  }

  async function revokeAccess(share) {
    if (!window.confirm(`Revoke ${share.recipient_name}'s access to "${share.filename}"?`)) {
      return;
    }

    setError("");
    setMessage("");
    setRevokingShareId(share.id);
    try {
      const result = await apiRequest(
        `/shares/${encodeURIComponent(share.id)}`,
        { method: "DELETE" },
        accessToken
      );
      setSharedUsers((previous) =>
        previous.map((item) =>
          item.id === share.id
            ? { ...item, revoked: true, revoked_at: new Date().toISOString() }
            : item
        )
      );
      setMessage(result?.message || "Document access was revoked.");
    } catch (revokeError) {
      setError(revokeError.message || "Could not revoke document access.");
    } finally {
      setRevokingShareId("");
    }
  }

  return (
    <section className="panel shared-access-panel">
      <div className="panel-heading">
        <div>
          <h2>Shared by me</h2>
          <p className="muted">Manage access you have granted to other people.</p>
        </div>
        <button
          type="button"
          className="primary-button"
          onClick={() => setShowAddUser((previous) => !previous)}
        >
          {showAddUser ? "Cancel" : "+ Add User"}
        </button>
      </div>

      {showAddUser && (
        <form className="add-user-form" onSubmit={addUser}>
          <label>
            Document
            <select name="document_id" defaultValue="" required>
              <option value="" disabled>Select a document</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.filename}
                </option>
              ))}
            </select>
          </label>
          <label>
            User name
            <input name="name" placeholder="Enter user's name" required maxLength={100} />
          </label>
          <label>
            Email
            <input name="email" type="email" placeholder="name@example.com" required />
          </label>
          <label>
            Expires
            <input name="expiration" type="datetime-local" required />
          </label>
          <label>
            <input name="can_download" type="checkbox" />
            Allow download
          </label>
          <button
            type="submit"
            className="primary-button"
            disabled={submitting || documents.length === 0}
          >
            {submitting ? "Sharing..." : "Share access"}
          </button>
        </form>
      )}

      {error && <p className="form-message error" role="alert">{error}</p>}
      {message && <p className="form-message" role="status">{message}</p>}
      {loading || initialLoading ? (
        <p className="muted" role="status">Loading shared access...</p>
      ) : sharedUsers.length === 0 ? (
        <div className="empty-state compact-empty-state">
          <div className="empty-icon">♧</div>
          <h3>No Shared Access</h3>
          <p>People you share documents with will appear here.</p>
        </div>
      ) : (
        <div className="shared-user-list">
          {sharedUsers.map((share) => (
            <article className="shared-user-row" key={share.id}>
              <div className="profile-avatar" aria-hidden="true">
                {(share.recipient_name || "?").charAt(0).toUpperCase()}
              </div>
              <div className="shared-user-info">
                <strong>{share.filename || "Document"}</strong>
                <span>
                  Shared with {share.recipient_name || "Unknown recipient"} (
                  {share.recipient_email || "No email"}) · {formatDate(share.created_at)}
                </span>
              </div>
              <span className="shared-permission">
                {share.revoked
                  ? "Revoked"
                  : share.can_download
                    ? "View and download"
                    : "View"}
              </span>
              <span className="shared-expiration">
                {share.revoked ? "Access revoked" : `Expires ${formatDate(share.expires_at)}`}
              </span>
              {!share.revoked && (
                <button
                  type="button"
                  className="revoke-button"
                  disabled={revokingShareId === share.id}
                  onClick={() => revokeAccess(share)}
                >
                  {revokingShareId === share.id ? "Revoking..." : "Revoke access"}
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
