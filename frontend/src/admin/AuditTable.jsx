function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function eventResult(event) {
  const action = String(event.action || "").toLowerCase();
  if (action.includes("denied") || action.includes("failed") || action.includes("rejected")) {
    return "Denied";
  }
  return "Recorded";
}

export default function AuditTable({ auditLogs }) {
  return (
    <div className="activity-table-wrap">
      <table className="activity-table admin-table">
        <thead>
          <tr>
            <th>Activity</th>
            <th>Actor ID</th>
            <th>Document ID</th>
            <th>Timestamp</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          {auditLogs.length === 0 ? (
            <tr>
              <td className="activity-empty" colSpan="5">No audit events found.</td>
            </tr>
          ) : (
            auditLogs.map((event) => {
              const result = eventResult(event);
              return (
                <tr key={event.id}>
                  <td className="activity-action">{event.action}</td>
                  <td>{event.actor_id || "—"}</td>
                  <td>{event.document_id || "—"}</td>
                  <td>{formatDate(event.timestamp)}</td>
                  <td>
                    <span className={`audit-result ${result.toLowerCase()}`}>
                      <span aria-hidden="true">{result === "Denied" ? "!" : "✓"}</span>
                      {result}
                    </span>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}