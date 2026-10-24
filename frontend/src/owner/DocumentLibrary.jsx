import { useRef, useState } from "react";
import { apiRequest } from "../api";

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString();
}

export default function DocumentLibrary({
  documents,
  setDocuments,
  accessToken,
  isLoading,
  refreshDocuments,
}) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All categories");
  const [shareTarget, setShareTarget] = useState(null);
  const [recipientName, setRecipientName] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [canDownload, setCanDownload] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  async function handleUpload(event) {
    const file = event.target.files?.[0];

    // Allow the same file to be selected again later.
    event.target.value = "";

    if (!file) return;

    if (file.size === 0) {
      setMessage("The selected file is empty.");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setMessage("File size cannot exceed 20 MB.");
      return;
    }

    setIsUploading(true);
    setMessage(`Uploading ${file.name}...`);

    try {
      const body = new FormData();
      body.append("file", file);

      await apiRequest(
        "/documents/upload",
        {
          method: "POST",
          body,
        },
        accessToken
      );

      setMessage(`${file.name} uploaded successfully.`);
      await refreshDocuments();
    } catch (error) {
      setMessage(error.message || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload(document) {
    try {
      const response = await apiRequest(
        `/documents/${encodeURIComponent(document.id)}/download`,
        {},
        accessToken
      );

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement("a");

      link.href = url;
      link.download = document.filename;
      window.document.body.appendChild(link);
      link.click();
      link.remove();

      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      setMessage(error.message || "Download failed.");
    }
  }

  async function handleDelete(document) {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${document.filename}"?`
    );

    if (!confirmed) return;

    try {
      await apiRequest(
        `/documents/${encodeURIComponent(document.id)}`,
        { method: "DELETE" },
        accessToken
      );

      setDocuments((previous) =>
        previous.filter((item) => item.id !== document.id)
      );

      setMessage(`${document.filename} deleted successfully.`);
    } catch (error) {
      setMessage(error.message || "Delete failed.");
    }
  }

  async function handleShare(event) {
    event.preventDefault();
    if (!shareTarget || !expiresAt) return;

    const expiration = new Date(expiresAt);
    if (Number.isNaN(expiration.getTime()) || expiration <= new Date()) {
      setMessage("Choose a future access expiration date and time.");
      return;
    }

    setIsSharing(true);
    setMessage("");

    try {
      await apiRequest(
        `/documents/${encodeURIComponent(shareTarget.id)}/share`,
        {
          method: "POST",
          body: JSON.stringify({
            recipient_name: recipientName.trim(),
            recipient_email: recipientEmail.trim(),
            expires_at: expiration.toISOString(),
            can_download: canDownload,
          }),
        },
        accessToken
      );

      setMessage(
        `${shareTarget.filename} was shared with ${recipientName.trim()}.`
      );
      setShareTarget(null);
      setRecipientName("");
      setRecipientEmail("");
      setExpiresAt("");
      setCanDownload(false);
    } catch (error) {
      setMessage(error.message || "Could not share this document.");
    } finally {
      setIsSharing(false);
    }
  }

  const visibleDocuments = documents.filter((document) => {
    const matchesSearch = document.filename
      .toLowerCase()
      .includes(search.trim().toLowerCase());

    // The backend does not currently store a category field.
    // Keep the existing category selector as a UI placeholder.
    const matchesCategory = category === "All categories";

    return matchesSearch && matchesCategory;
  });

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>My Documents</h2>
          <p className="muted">
            Upload and organise your confidential files.
          </p>
        </div>

        <div>
          <input
            ref={fileInputRef}
            type="file"
            hidden
            onChange={handleUpload}
            aria-label="Select a file to upload"
          />

          <button
            type="button"
            className="primary-button"
            disabled={isUploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? "Uploading..." : "+ Upload document"}
          </button>
        </div>
      </div>

      <p className="muted" style={{ fontSize: "11px" }}>
        Maximum file size: 20 MB.
      </p>

      {message && (
        <p className="upload-status" role="status" aria-live="polite">
          {message}
        </p>
      )}

      <div className="search-row">
        <input
          aria-label="Search documents"
          placeholder="Search documents..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <select
          aria-label="Filter documents"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          <option>All categories</option>
          <option>Contracts</option>
          <option>Reports</option>
          <option>Personal</option>
          <option>Other</option>
        </select>
      </div>

      {shareTarget && (
        <form className="share-form" onSubmit={handleShare}>
          <h3>Share “{shareTarget.filename}”</h3>
          <p className="muted">
            The recipient must have an active TrustVault Viewer or Owner account.
            Access is limited to one successful view.
          </p>

          <label>
            Recipient name
            <input
              type="text"
              autoComplete="name"
              maxLength={100}
              required
              value={recipientName}
              onChange={(event) => setRecipientName(event.target.value)}
            />
          </label>

          <label>
            Recipient email
            <input
              type="email"
              autoComplete="email"
              required
              value={recipientEmail}
              onChange={(event) => setRecipientEmail(event.target.value)}
            />
          </label>

          <label>
            Access expires
            <input
              type="datetime-local"
              required
              value={expiresAt}
              onChange={(event) => setExpiresAt(event.target.value)}
            />
          </label>

          <label className="share-download-option">
            <input
              type="checkbox"
              checked={canDownload}
              onChange={(event) => setCanDownload(event.target.checked)}
            />
            Allow downloading (uses the same one-time access)
          </label>

          <div className="share-form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={isSharing}
            >
              {isSharing ? "Sharing..." : "Share document"}
            </button>
            <button
              type="button"
              className="text-action"
              disabled={isSharing}
              onClick={() => setShareTarget(null)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="empty-state">
          <p>Loading documents...</p>
        </div>
      ) : visibleDocuments.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">▤</div>
          <h3>
            {search ? "No matching documents" : "Nothing Here"}
          </h3>
          <p>
            {search
              ? "Try another filename."
              : "Your documents will appear here after you upload them."}
          </p>
        </div>
      ) : (
        <div className="document-list">
          {visibleDocuments.map((document) => (
            <article className="document-row" key={document.id}>
              <div className="document-file-icon">▤</div>

              <div className="document-info">
                <strong title={document.filename}>
                  {document.filename}
                </strong>
                <span>
                  {formatBytes(document.size_bytes)} · Uploaded{" "}
                  {formatDate(document.created_at)}
                </span>
              </div>

              <button
                type="button"
                className="text-action"
                onClick={() => {
                  setShareTarget(document);
                  setRecipientName("");
                  setRecipientEmail("");
                  setExpiresAt("");
                  setCanDownload(false);
                  setMessage("");
                }}
              >
                Share
              </button>

              <button
                type="button"
                className="text-action"
                onClick={() => handleDownload(document)}
              >
                Download
              </button>

              <button
                type="button"
                className="revoke-button"
                onClick={() => handleDelete(document)}
              >
                Delete
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}