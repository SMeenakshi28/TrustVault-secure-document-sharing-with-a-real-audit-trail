import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import UserSettings from "../components/UserSettings";
import ViewerStats from "./ViewerStats";
import SharedDocuments from "./SharedDocuments";
import { apiRequest } from "../api";

function getExpirationDate(expiration) {
  if (!expiration || expiration.toLowerCase() === "no expiry") return null;
  const date = new Date(expiration);
  return Number.isNaN(date.getTime()) ? null : date;
}

export default function ViewerDashboard({
  form,
  setForm,
  selectedRole,
  logout,
  accessToken,
}) {
  const [selectedView, setSelectedView] = useState("dashboard");
  const [searchQuery, setSearchQuery] = useState("");
  const [sharedDocuments, setSharedDocuments] = useState([]);
  const [loading, setLoading] = useState(Boolean(accessToken));
  const [error, setError] = useState(
    accessToken ? "" : "Please sign in again to view shared documents."
  );

  useEffect(() => {
    let cancelled = false;

    async function loadSharedDocuments() {
      setLoading(true);
      setError("");

      try {
        const response = await apiRequest("/shared-with-me", { method: "GET" }, accessToken);
        const documents = Array.isArray(response) ? response : response?.documents || response?.items || [];

        if (!cancelled) {
          setSharedDocuments(
            documents.map((doc) => ({
              ...doc,
              name: doc.name || doc.filename || "Untitled document",
              owner: doc.owner || doc.owner_name || doc.owner_email || "Document owner",
              permission: doc.permission || [doc.can_view ? "View" : "", doc.can_download ? "Download" : ""].filter(Boolean).join(" / ") || "View",
              expiration: doc.expiration || doc.expires_at || doc.expires_on || "No expiry",
            }))
          );
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not load shared documents.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    if (accessToken) loadSharedDocuments();

    return () => { cancelled = true; };
  }, [accessToken]);

  async function accessDocument(document, download = false) {
    const action = download ? "download" : "view";
    const approved = window.confirm(
      `You can successfully access "${document.name}" only once. ${download ? "Downloading" : "Opening"} it will use this share's one-time access. Continue?`
    );

    if (!approved) return;

    const previewWindow = download ? null : window.open("about:blank", "_blank");
    if (!download && !previewWindow) {
      setError("Allow pop-ups for this site, then try opening the document again.");
      return;
    }

    setError("");
    try {
      const response = await apiRequest(
        `/documents/${encodeURIComponent(document.document_id)}/${download ? "download" : "file"}`,
        { method: "GET" },
        accessToken
      );

      const viewedAt = new Date().toISOString();
      setSharedDocuments((previous) =>
        previous.map((item) => item.id === document.id ? { ...item, viewed: true, viewed_at: viewedAt } : item)
      );

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      if (download) {
        const link = window.document.createElement("a");
        link.href = url;
        link.download = document.filename || document.name;
        window.document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        previewWindow.location.replace(url);
      }

      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) {
      previewWindow?.close();
      setError(err.message || `Could not ${action} this document.`);
    }
  }

  const viewTitle = {
    dashboard: "Dashboard",
    shared_with_me: "Shared With Me",
    settings: "User Settings",
  }[selectedView];

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const expirationLimit = new Date(today);
  expirationLimit.setDate(expirationLimit.getDate() + 30);

  const activeDocuments = sharedDocuments.filter((document) => {
    const expirationDate = getExpirationDate(document.expiration);
    return !expirationDate || expirationDate >= today;
  });

  return (
    <DashboardLayout
      viewTitle={viewTitle}
      selectedRole={selectedRole}
      selectedView={selectedView}
      setSelectedView={setSelectedView}
      form={form}
      logout={logout}
    >
      <div className="welcome-row">
        <div>
          <p className="eyebrow">VIEWER WORKSPACE</p>
          <h1>{selectedView === "dashboard" ? "Your shared documents" : viewTitle}</h1>
          <p className="muted">Documents shared with you, with permissions set by their owners.</p>
          <p className="upload-status" role="note">
            Each share allows one successful document delivery. Opening or downloading uses that access; a delivered copy may be retained or captured by its recipient.
          </p>
        </div>
        <span className="role-pill">{selectedRole}</span>
      </div>

      {selectedView === "settings" && (
        <UserSettings
          form={form}
          setForm={setForm}
          selectedRole={selectedRole}
          accessToken={accessToken}
          logout={logout}
        />
      )}

      {selectedView === "dashboard" && (
        <ViewerStats
          activeDocuments={activeDocuments}
          today={today}
          expirationLimit={expirationLimit}
          getExpirationDate={getExpirationDate}
        />
      )}

      {(selectedView === "dashboard" || selectedView === "shared_with_me") && (
        <SharedDocuments
          sharedDocuments={sharedDocuments}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          loading={loading}
          error={error}
          accessDocument={accessDocument}
          setSelectedView={setSelectedView}
        />
      )}
    </DashboardLayout>
  );
}