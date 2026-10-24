function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

export default function OwnerAccessRequests({
  requests,
  loading,
  busyRequestId,
  onReview,
}) {
  return (
    <section className="panel admin-section">
      <div className="panel-heading">
        <div>
          <h2>Owner access requests</h2>
          <p className="muted">Review Viewer requests to become document Owners.</p>
        </div>
      </div>
      {loading && <p className="muted" role="status">Loading requests…</p>}
      <div className="activity-table-wrap">
        <table className="activity-table admin-table">
          <thead>
            <tr>
              <th>Requester</th>
              <th>Requested</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {requests.length === 0 ? (
              <tr>
                <td className="activity-empty" colSpan="3">No pending Owner access requests.</td>
              </tr>
            ) : requests.map((request) => (
              <tr key={request.id}>
                <td>
                  <strong>{request.user_name || "Unnamed user"}</strong>
                  <div className="muted">{request.user_email || request.user_id}</div>
                  {!request.user_active && <div className="muted">Account inactive</div>}
                </td>
                <td>{formatDate(request.created_at)}</td>
                <td>
                  <button
                    type="button"
                    className="text-action"
                    disabled={busyRequestId === request.id || !request.user_active}
                    onClick={() => onReview(request, "approve")}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="text-action"
                    style={{ color: "#bd3030", marginLeft: "12px" }}
                    disabled={busyRequestId === request.id}
                    onClick={() => onReview(request, "reject")}
                  >
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
