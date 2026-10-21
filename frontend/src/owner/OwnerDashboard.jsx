import { useState } from "react";
import DashboardLayout from "../components/DashboardLayout";
import DocumentLibrary from "./DocumentLibrary";
import SharedAccess from "./SharedAccess";
import ActivityLog from "./ActivityLog";

export default function OwnerDashboard({ form, selectedRole, logout }) {
  const [selectedView, setSelectedView] = useState("dashboard");
  const [message, setMessage] = useState("");
  const [sharedUsers, setSharedUsers] = useState([]);
  const activityLog = [];

  const viewTitle = {
    dashboard: "Dashboard",
    documents: "My Documents",
    shared: "Shared Access",
    activity: "Activity Log",
  }[selectedView];

  return (
    <DashboardLayout viewTitle={viewTitle} selectedRole={selectedRole} selectedView={selectedView} setSelectedView={setSelectedView} form={form} logout={logout}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">{selectedRole.toUpperCase()} WORKSPACE</p>
          <h1>{selectedView === "dashboard" ? `Welcome, ${(form.name || form.username || "User").split(" ")[0]}` : viewTitle}</h1>
          <p className="muted">Manage your documents and the people who can access them.</p>
        </div>
        <span className="role-pill">{selectedRole}</span>
      </div>

      {selectedView === "dashboard" && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-icon">▤</span><p>Total documents</p><h2>0</h2><span className="stat-note">Your document library</span>
            </div>
            <div className="stat-card">
              <span className="stat-icon purple">♧</span><p>People with access</p><h2>{sharedUsers.length}</h2><span className="stat-note">Your sharing permissions</span>
            </div>
            <div className="stat-card">
              <span className="stat-icon green">◷</span><p>Recent activity</p><h2>0</h2><span className="stat-note">Recorded events</span>
            </div>
          </div>
          <DocumentLibrary setMessage={setMessage} />
        </>
      )}

      {selectedView === "documents" && <DocumentLibrary setMessage={setMessage} />}
      {selectedView === "shared" && <SharedAccess sharedUsers={sharedUsers} setSharedUsers={setSharedUsers} />}
      {selectedView === "activity" && <ActivityLog activityLog={activityLog} />}

      {message && <p className="form-message" role="status">{message}</p>}
    </DashboardLayout>
  );
}