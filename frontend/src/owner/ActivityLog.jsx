export default function ActivityLog({ activityLog }) {
  return (
    <section className="panel shared-access-panel">
      <div className="panel-heading">
        <div>
          <h2>Activity history</h2>
          <p className="muted">A read-only record of activity on shared documents.</p>
        </div>
      </div>
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
            ) : activityLog.map((activity) => (
              <tr key={activity.id}>
                <td>{activity.timestamp}</td>
                <td className="activity-user">{activity.user}</td>
                <td className="activity-action">{activity.action}</td>
                <td>{activity.document}</td>
                <td><span className={`result-badge ${activity.result === "Success" ? "result-success" : "result-expired"}`}>{activity.result}</span></td>
                <td>{activity.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}