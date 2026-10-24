export default function ActivityLog({
  activityLog = [],
  loading = false,
  error = "",
}) {
  return (
    <section className="panel shared-access-panel">
      <div className="panel-heading">
        <div>
          <h2>Activity history</h2>
          <p className="muted">A read-only record of activity on shared documents.</p>
        </div>
      </div>
      {loading && <p className="muted" role="status">Loading activity history…</p>}
      {error && <p className="form-message" role="alert">{error}</p>}
      <div className="activity-table-wrap">
        <table className="activity-table">
          <thead>
            <tr>
              <th scope="col">Timestamp</th><th scope="col">User</th><th scope="col">Action</th>
              <th scope="col">Document</th><th scope="col">Result</th><th scope="col">Details</th>
            </tr>
          </thead>
          <tbody>
            {activityLog.length === 0 ? (
              <tr><td className="activity-empty" colSpan="6">Nothing to show</td></tr>
            ) : activityLog.filter((activity) => activity && typeof activity === "object").map((activity) => (
              <tr key={activity.id}>
                <td>{String(activity.timestamp || "—")}</td>
                <td className="activity-user">{String(activity.user || "User")}</td>
                <td className="activity-action">{String(activity.action || "Activity")}</td>
                <td>{String(activity.document || "—")}</td>
                <td><span className={`result-badge ${activity.result === "Success" || activity.result === "Recorded" ? "result-success" : "result-expired"}`}>{String(activity.result || "Recorded")}</span></td>
                <td>{typeof activity.details === "string" ? activity.details : activity.details == null ? "" : JSON.stringify(activity.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}