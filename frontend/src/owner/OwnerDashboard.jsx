import { useEffect, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import UserSettings from "../components/UserSettings";
import { apiRequest } from "../api";
import DocumentLibrary from "./DocumentLibrary";
import SharedAccess from "./SharedAccess";
import ActivityLog from "./ActivityLog";
import SharedDocuments from "../viewer/SharedDocuments";
import { openSandboxedPreview } from "../security/openSandboxedPreview";

function mapActivityEvents(data) {
  const events = Array.isArray(data)
    ? data
    : Array.isArray(data?.items)
      ? data.items
      : Array.isArray(data?.events)
        ? data.events
        : [];

  return events
    .filter((event) => event && typeof event === "object")
    .map((event) => ({
      id: event.id || `${event.timestamp || "event"}-${event.action || "activity"}`,
      timestamp:
        event.timestamp ||
        event.created_at ||
        event.created_at_utc ||
        "—",
      user:
        event.user_name ||
        event.actor_email ||
        event.actor_id ||
        "User",
      action:
        event.action ||
        event.event_type ||
        event.action_type ||
        "Activity",
      document:
        event.document_name ||
        event.document_id ||
        "—",
      result:
        event.result ||
        (String(event.action || "").toLowerCase().includes("denied")
          ? "Denied"
          : "Recorded"),
      details:
        typeof event.details === "string"
          ? event.details
          : event.details && typeof event.details === "object"
            ? JSON.stringify(event.details)
            : "",
    }));
}

export default function OwnerDashboard({
  form,
  setForm,
  selectedRole,
  accessToken,
  logout,
}) {
  const [selectedView, setSelectedView] = useState("dashboard");
  const [message, setMessage] = useState("");
  const [sharedUsers, setSharedUsers] = useState([]);
  const [sharedAccessLoading, setSharedAccessLoading] = useState(true);
  const [documents, setDocuments] = useState([]);
  const [receivedShares, setReceivedShares] = useState([]);
  const [receivedSearchQuery, setReceivedSearchQuery] = useState("");
  const [receivedSharesLoading, setReceivedSharesLoading] = useState(false);
  const [receivedSharesError, setReceivedSharesError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [activityLog, setActivityLog] = useState([]);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityError, setActivityError] = useState("");

  async function refreshDocuments() {
    try {
      const data = await apiRequest(
        "/documents",
        {},
        accessToken
      );

      setDocuments(Array.isArray(data) ? data : []);
      setMessage("");
    } catch (error) {
      setMessage(error.message || "Could not load documents.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function loadDocuments() {
      try {
        const data = await apiRequest("/documents", {}, accessToken);
        if (!cancelled) {
          setDocuments(Array.isArray(data) ? data : []);
          setMessage("");
        }
      } catch (error) {
        if (!cancelled) {
          setMessage(error.message || "Could not load documents.");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadDocuments();
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  useEffect(() => {
    let cancelled = false;

    async function loadOwnerShares() {
      try {
        const data = await apiRequest("/owner/shares", {}, accessToken);
        if (!cancelled) {
          setSharedUsers(Array.isArray(data) ? data : []);
        }
      } catch (error) {
        if (!cancelled) {
          setMessage(error.message || "Could not load shared access.");
        }
      } finally {
        if (!cancelled) setSharedAccessLoading(false);
      }
    }

    loadOwnerShares();
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  useEffect(() => {
    let cancelled = false;

    async function loadReceivedShares() {
      setReceivedSharesLoading(true);
      setReceivedSharesError("");
      try {
        const data = await apiRequest("/shared-with-me", {}, accessToken);
        const shares = Array.isArray(data)
          ? data
          : Array.isArray(data?.items)
            ? data.items
            : [];
        if (!cancelled) {
          setReceivedShares(shares.map((share) => ({
            ...share,
            name: share.filename || "Untitled document",
            owner: share.owner_name || share.owner_email || share.owner_id || "Document owner",
            permission: share.can_download ? "View and download" : "View",
            expiration: share.expires_at || "No expiry",
          })));
        }
      } catch (error) {
        if (!cancelled) {
          setReceivedSharesError(error.message || "Could not load shared documents.");
        }
      } finally {
        if (!cancelled) setReceivedSharesLoading(false);
      }
    }

    loadReceivedShares();
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  async function accessReceivedShare(document, download = false) {
    const action = download ? "download" : "view";
    if (!window.confirm(`You can successfully access "${document.name}" only once. Continue?`)) {
      return;
    }

    const previewWindow = download ? null : window.open("about:blank", "_blank");
    if (!download && !previewWindow) {
      setReceivedSharesError("Allow pop-ups for this site, then try opening the document again.");
      return;
    }

    setReceivedSharesError("");
    try {
      const response = await apiRequest(
        `/documents/${encodeURIComponent(document.document_id)}/${download ? "download" : "file"}`,
        { method: "GET" },
        accessToken
      );
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setReceivedShares((previous) => previous.map((share) =>
        share.id === document.id
          ? { ...share, viewed: true, viewed_at: new Date().toISOString() }
          : share
      ));

      if (download) {
        const link = window.document.createElement("a");
        link.href = url;
        link.download = document.filename || document.name;
        window.document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        openSandboxedPreview(previewWindow, url);
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      previewWindow?.close();
      setReceivedSharesError(error.message || `Could not ${action} this document.`);
    }
  }

  async function requestActivityLog() {
    const data = await apiRequest(
      "/owner/audit-logs",
      {},
      accessToken
    );
    return mapActivityEvents(data);
  }

  async function refreshActivityLog() {
    try {
      setActivityLog(await requestActivityLog());
      setActivityError("");
    } catch (error) {
      setActivityLog([]);
      setActivityError(
        error.message || "Could not load activity history."
      );
    } finally {
      setActivityLoading(false);
    }
  }

  function navigateToView(view) {
    if (view === "activity") {
      setActivityLoading(true);
      setActivityError("");
      if (selectedView === "activity") {
        refreshActivityLog();
      }
    }
    setSelectedView(view);
  }

  useEffect(() => {
    if (selectedView !== "activity" || !accessToken) return undefined;

    let cancelled = false;
    requestActivityLog()
      .then((events) => {
        if (!cancelled) {
          setActivityLog(events);
          setActivityError("");
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setActivityLog([]);
          setActivityError(error.message || "Could not load activity history.");
        }
      })
      .finally(() => {
        if (!cancelled) setActivityLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // requestActivityLog reads the current access token and is tied to this effect's token dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedView, accessToken]);

  const viewTitle = {
    dashboard: "Dashboard",
    documents: "My Documents",
    shared: "Shared Access",
    shared_with_me: "Shared With Me",
    activity: "Activity Log",
    settings: "User Settings",
  }[selectedView];

  return (
    <DashboardLayout
      viewTitle={viewTitle}
      selectedRole={selectedRole}
      selectedView={selectedView}
      setSelectedView={navigateToView}
      form={form}
      setForm={setForm}
      logout={logout}
    >
      <div className="welcome-row">
        <div>
          <p className="eyebrow">
            {selectedRole.toUpperCase()} WORKSPACE
          </p>

          <h1>
            {selectedView === "dashboard"
              ? `Welcome, ${(form.name || "User").split(" ")[0]}`
              : viewTitle}
          </h1>

          <p className="muted">
            Manage your documents and the people who can access them.
          </p>
        </div>

        <span className="role-pill">{selectedRole}</span>
      </div>

      {selectedView === "dashboard" && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-icon">▤</span>
              <p>Total documents</p>
              <h2>{documents.length}</h2>
              <span className="stat-note">
                Your document library
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-icon purple">♧</span>
              <p>Sharing permissions</p>
              <h2>{sharedUsers.length}</h2>
              <span className="stat-note">
                Your sharing permissions
              </span>
            </div>

            <div className="stat-card">
              <span className="stat-icon green">◷</span>
              <p>Recent activity</p>
              <h2>0</h2>
              <span className="stat-note">
                Activity summary
              </span>
            </div>
          </div>

          <DocumentLibrary
            documents={documents}
            setDocuments={setDocuments}
            accessToken={accessToken}
            isLoading={isLoading}
            refreshDocuments={refreshDocuments}
          />
        </>
      )}

      {selectedView === "documents" && (
        <DocumentLibrary
          documents={documents}
          setDocuments={setDocuments}
          accessToken={accessToken}
          isLoading={isLoading}
          refreshDocuments={refreshDocuments}
        />
      )}

      {selectedView === "shared" && (
        <SharedAccess
          sharedUsers={sharedUsers}
          setSharedUsers={setSharedUsers}
          documents={documents}
          accessToken={accessToken}
          initialLoading={sharedAccessLoading}
        />
      )}

      {selectedView === "shared_with_me" && (
        <SharedDocuments
          sharedDocuments={receivedShares}
          searchQuery={receivedSearchQuery}
          setSearchQuery={setReceivedSearchQuery}
          loading={receivedSharesLoading}
          error={receivedSharesError}
          accessDocument={accessReceivedShare}
          setSelectedView={setSelectedView}
        />
      )}

      {selectedView === "settings" && (
        <UserSettings
          form={form}
          setForm={setForm}
          selectedRole={selectedRole}
          accessToken={accessToken}
          logout={logout}
        />
      )}

      {selectedView === "activity" && (
        <ActivityLog
          activityLog={activityLog}
          loading={activityLoading}
          error={activityError}
        />
      )}

      {message && (
        <p className="form-message" role="status">
          {message}
        </p>
      )}
    </DashboardLayout>
  );
}