import { useState } from "react";
import DashboardLayout from "../components/DashboardLayout";

const users = [];
const documents = [];
const auditLogs = [];

function PeopleTable() {
  return (
    <div className="activity-table-wrap">
      <table className="activity-table admin-table">
        <thead>
          <tr>
            <th scope="col">User</th>
            <th scope="col">Role</th>
            <th scope="col">Status</th>
            <th scope="col">Joined</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          {users.length === 0 ? (
            <tr><td className="activity-empty" colSpan="5">Nothing Here</td></tr>
          ) : users.map((user) => (
            <tr key={user.id}>
              <td className="activity-user">{user.name}</td>
              <td>{user.role}</td>
              <td><span className="admin-status">{user.status}</span></td>
              <td>{user.joined}</td>
              <td>{user.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditTable() {
  return (
    <div className="activity-table-wrap">
      <table className="activity-table admin-table">
        <thead>
          <tr>
            <th scope="col">Activity</th>
            <th scope="col">User</th>
            <th scope="col">Document</th>
            <th scope="col">Timestamp</th>
            <th scope="col">Result</th>
          </tr>
        </thead>
        <tbody>
          {auditLogs.length === 0 ? (
            <tr><td className="activity-empty" colSpan="5">Nothing Here</td></tr>
          ) : auditLogs.map((event) => (
            <tr key={event.id}>
              <td className="activity-action">{event.action}</td>
              <td>{event.user}</td>
              <td>{event.document}</td>
              <td>{event.timestamp}</td>
              <td>
                <span className={`audit-result ${event.result.toLowerCase()}`}>
                  <span aria-hidden="true">{event.result === "Success" ? "✓" : "!"}</span>
                  {event.result}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminDashboard({ form, selectedRole, logout }) {
  const [selectedView, setSelectedView] = useState("dashboard");

  const viewTitle = {
    dashboard: "Security Overview",
    users: "People & Access",
    audit_logs: "Audit Logs",
  }[selectedView];

  const deniedAttempts = auditLogs.filter((event) => event.result === "Denied").length;

  return (
    <DashboardLayout viewTitle={viewTitle} selectedRole={selectedRole} selectedView={selectedView} setSelectedView={setSelectedView} form={form} logout={logout}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">ADMIN WORKSPACE</p>
          <h1>{selectedView === "dashboard" ? "Security Overview" : viewTitle}</h1>
          <p className="muted">Monitor your workspace, people, and security activity.</p>
        </div>
        <span className="role-pill">{selectedRole}</span>
      </div>

      {selectedView === "dashboard" && (
        <>
          <section className="admin-stats-grid" aria-label="Security overview">
            <article className="stat-card">
              <span className="stat-icon">♙</span>
              <p>Registered users</p>
              <h2>{users.length}</h2>
              <span className="stat-note">People in your workspace</span>
            </article>
            <article className="stat-card">
              <span className="stat-icon purple">▤</span>
              <p>Total documents</p>
              <h2>{documents.length}</h2>
              <span className="stat-note">Documents in TrustVault</span>
            </article>
            <article className="stat-card">
              <span className="stat-icon green">◷</span>
              <p>Security events</p>
              <h2>{auditLogs.length}</h2>
              <span className="stat-note">Recorded audit log entries</span>
            </article>
            <article className="stat-card">
              <span className="stat-icon red">⊘</span>
              <p>Denied attempts</p>
              <h2>{deniedAttempts}</h2>
              <span className="stat-note">Access attempts denied</span>
            </article>
          </section>

          <section className="panel admin-section">
            <div className="panel-heading">
              <div>
                <h2>People &amp; Access</h2>
                <p className="muted">Workspace users and their account status.</p>
              </div>
              <button type="button" className="text-action" onClick={() => setSelectedView("users")}>
                View all <span aria-hidden="true">→</span>
              </button>
            </div>
            <PeopleTable />
          </section>

          <section className="panel admin-section">
            <div className="panel-heading">
              <div>
                <h2>Recent Security Activity</h2>
                <p className="muted">Document views and access outcomes.</p>
              </div>
              <button type="button" className="text-action" onClick={() => setSelectedView("audit_logs")}>
                Review activity <span aria-hidden="true">→</span>
              </button>
            </div>
            <div className="activity-table-wrap">
              <table className="activity-table admin-table">
                <thead>
                  <tr>
                    <th scope="col">Activity</th>
                    <th scope="col">Document</th>
                    <th scope="col">Timestamp</th>
                    <th scope="col">Result</th>
                    <th scope="col"> </th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.length === 0 ? (
                    <tr><td className="activity-empty" colSpan="5">Nothing Here</td></tr>
                  ) : auditLogs.slice(0, 5).map((event) => (
                    <tr key={event.id}>
                      <td className="activity-action">{event.action}</td>
                      <td>{event.document}</td>
                      <td>{event.timestamp}</td>
                      <td>
                        <span className={`audit-result ${event.result.toLowerCase()}`}>
                          <span aria-hidden="true">{event.result === "Success" ? "✓" : "!"}</span>
                          {event.result}
                        </span>
                      </td>
                      <td>
                        <button type="button" className="row-arrow" aria-label="Open audit logs" onClick={() => setSelectedView("audit_logs")}>→</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {selectedView === "users" && (
        <section className="panel admin-section">
          <div className="panel-heading">
            <div>
              <h2>People &amp; Access</h2>
              <p className="muted">A read-only overview of registered workspace users.</p>
            </div>
          </div>
          <PeopleTable />
        </section>
      )}

      {selectedView === "audit_logs" && (
        <section className="panel admin-section">
          <div className="panel-heading">
            <div>
              <h2>Audit Logs</h2>
              <p className="muted">A read-only record of document views and security events.</p>
            </div>
          </div>
          <AuditTable />
        </section>
      )}
    </DashboardLayout>
  );
}
