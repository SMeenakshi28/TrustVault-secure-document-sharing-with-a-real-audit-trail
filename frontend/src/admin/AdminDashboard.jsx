import { useCallback, useEffect, useMemo, useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import { apiRequest } from "../api";
import AdminStats from "./AdminStats";
import PeopleTable from "./PeopleTable";
import AuditTable from "./AuditTable";
import UserSettings from "../components/UserSettings";
import OwnerAccessRequests from "./OwnerAccessRequests";

function eventResult(event) {
  const action = String(event.action || "").toLowerCase();
  if (action.includes("denied") || action.includes("failed") || action.includes("rejected")) {
    return "Denied";
  }
  return "Recorded";
}

export default function AdminDashboard({ form, setForm, selectedRole, accessToken, logout }) {
  const [selectedView, setSelectedView] = useState("dashboard");
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [documentCount, setDocumentCount] = useState(0);
  const [ownerAccessRequests, setOwnerAccessRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyUserId, setBusyUserId] = useState("");
  const [busyRequestId, setBusyRequestId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const fetchDashboardData = useCallback(async () => {
    if (!accessToken) {
      throw new Error("Login token missing. Please sign in again.");
    }

    return Promise.all([
      apiRequest("/admin/users", {}, accessToken),
      apiRequest("/admin/audit-logs", {}, accessToken),
      apiRequest("/admin/document-count", {}, accessToken),
      apiRequest("/admin/owner-access-requests", {}, accessToken),
    ]);
  }, [accessToken]);

  const loadDashboardData = useCallback(async () => {
    if (!accessToken) {
      setError("Login token missing. Please sign in again.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [userData, auditData, documentData, requestData] = await fetchDashboardData();

      setUsers(Array.isArray(userData) ? userData : []);
      setAuditLogs(Array.isArray(auditData) ? auditData : []);
      setOwnerAccessRequests(Array.isArray(requestData) ? requestData : []);
      setDocumentCount(
        Number.isSafeInteger(documentData?.count) && documentData.count >= 0
          ? documentData.count
          : 0
      );
    } catch (err) {
      setError(err.message || "Could not load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [accessToken, fetchDashboardData]);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      try {
        const [userData, auditData, documentData, requestData] = await fetchDashboardData();
        if (!cancelled) {
          setUsers(Array.isArray(userData) ? userData : []);
          setAuditLogs(Array.isArray(auditData) ? auditData : []);
          setOwnerAccessRequests(Array.isArray(requestData) ? requestData : []);
          setDocumentCount(
            Number.isSafeInteger(documentData?.count) && documentData.count >= 0
              ? documentData.count
              : 0
          );
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Could not load dashboard data.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadInitialData();
    return () => {
      cancelled = true;
    };
  }, [fetchDashboardData]);

  const titles = {
    dashboard: "Security Overview",
    users: "People & Access",
    audit_logs: "Audit Logs",
    owner_requests: "Owner Access Requests",
    settings: "User Settings",
  };

  const deniedAttempts = useMemo(
    () => auditLogs.filter((event) => eventResult(event) === "Denied").length,
    [auditLogs]
  );

  async function changeRole(user, role) {
    if (role === user.role) return;
    setBusyUserId(user.id);
    setError("");
    setNotice("");

    try {
      await apiRequest(
        `/admin/users/${encodeURIComponent(user.id)}/role`,
        { method: "PATCH", body: JSON.stringify({ role }) },
        accessToken
      );
      setNotice(`Updated ${user.email} to ${role}.`);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Could not update role.");
    } finally {
      setBusyUserId("");
    }
  }

  async function changeActive(user, active) {
    const action = active ? "activate" : "deactivate";
    if (!window.confirm(`Are you sure you want to ${action} ${user.email}?`)) return;

    setBusyUserId(user.id);
    setError("");
    setNotice("");

    try {
      await apiRequest(
        `/admin/users/${encodeURIComponent(user.id)}/active`,
        { method: "PATCH", body: JSON.stringify({ active }) },
        accessToken
      );
      setNotice(`${user.email} was ${active ? "activated" : "deactivated"}.`);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Could not update account status.");
    } finally {
      setBusyUserId("");
    }
  }

  async function deleteUser(user) {
    const confirmed = window.confirm(
      `Permanently delete ${user.email} from TrustVault? Active shares will be revoked. Their documents and audit history will be retained as historical records. This action cannot be undone.`
    );
    if (!confirmed) return;

    setBusyUserId(user.id);
    setError("");
    setNotice("");

    try {
      await apiRequest(
        `/admin/users/${encodeURIComponent(user.id)}`,
        { method: "DELETE" },
        accessToken
      );
      setNotice(`${user.email} was permanently deleted; documents and audit history were preserved.`);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Could not delete account.");
    } finally {
      setBusyUserId("");
    }
  }

  async function reviewOwnerRequest(request, decision) {
    const decisionLabel = decision === "approve" ? "approve" : "reject";
    if (!window.confirm(`${decisionLabel[0].toUpperCase()}${decisionLabel.slice(1)} the Owner access request from ${request.user_email || request.user_name}?`)) {
      return;
    }

    setBusyRequestId(request.id);
    setError("");
    setNotice("");
    try {
      await apiRequest(
        `/admin/owner-access-requests/${encodeURIComponent(request.id)}`,
        {
          method: "PATCH",
          body: JSON.stringify({ decision }),
        },
        accessToken
      );
      setNotice(
        decision === "approve"
          ? `${request.user_email || request.user_name} was approved for Owner access.`
          : `Owner access request from ${request.user_email || request.user_name} was rejected.`
      );
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Could not review Owner access request.");
    } finally {
      setBusyRequestId("");
    }
  }

  const peopleTableComponent = (
    <>
      {loading && <p className="muted" role="status">Loading workspace users…</p>}
      <PeopleTable
        users={users}
        onRoleChange={changeRole}
        onActiveChange={changeActive}
        onDeleteUser={deleteUser}
        busyUserId={busyUserId}
      />
    </>
  );

  return (
    <DashboardLayout
      viewTitle={titles[selectedView]}
      selectedRole={selectedRole}
      selectedView={selectedView}
      setSelectedView={setSelectedView}
      form={form}
      logout={logout}
    >
      <div className="welcome-row">
        <div>
          <p className="eyebrow">ADMIN WORKSPACE</p>
          <h1>{titles[selectedView]}</h1>
          <p className="muted">Monitor your workspace, people, and security activity.</p>
        </div>
        <span className="role-pill">{selectedRole}</span>
      </div>

      {error && <div className="form-message" role="alert">{error}</div>}
      {notice && <div className="upload-status" role="status">{notice}</div>}

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button type="button" className="text-action" onClick={loadDashboardData}>
          Refresh data ↻
        </button>
      </div>

      {selectedView === "dashboard" && (
        <>
          <AdminStats
            usersCount={users.length}
            documentCount={documentCount}
            auditLogsCount={auditLogs.length}
            deniedAttempts={deniedAttempts}
            loading={loading}
          />

          <section className="panel admin-section">
            <div className="panel-heading">
              <div>
                <h2>People &amp; Access</h2>
                <p className="muted">Workspace users and their account status.</p>
              </div>
              <button type="button" className="text-action" onClick={() => setSelectedView("users")}>
                View all →
              </button>
            </div>
            {peopleTableComponent}
          </section>

          <section className="panel admin-section">
            <div className="panel-heading">
              <div>
                <h2>Recent Security Activity</h2>
                <p className="muted">Events recorded by the backend audit log.</p>
              </div>
              <button type="button" className="text-action" onClick={() => setSelectedView("audit_logs")}>
                Review activity →
              </button>
            </div>
            <AuditTable auditLogs={[...auditLogs].reverse().slice(0, 5)} />
          </section>
        </>
      )}

      {selectedView === "users" && (
        <section className="panel admin-section">
          <div className="panel-heading">
            <div>
              <h2>People &amp; Access</h2>
              <p className="muted">Manage workspace roles and account status.</p>
            </div>
          </div>
          {peopleTableComponent}
        </section>
      )}

      {selectedView === "owner_requests" && (
        <OwnerAccessRequests
          requests={ownerAccessRequests}
          loading={loading}
          busyRequestId={busyRequestId}
          onReview={reviewOwnerRequest}
        />
      )}

      {selectedView === "audit_logs" && (
        <section className="panel admin-section">
          <div className="panel-heading">
            <div>
              <h2>Audit Logs</h2>
              <p className="muted">Audit events returned by the TrustVault backend.</p>
            </div>
          </div>
          {loading && <p className="muted" role="status">Loading audit events…</p>}
          <AuditTable auditLogs={[...auditLogs].reverse()} />
        </section>
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
    </DashboardLayout>
  );
}