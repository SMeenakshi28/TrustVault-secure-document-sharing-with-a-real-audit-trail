function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function PeopleTable({
  users,
  onRoleChange,
  onActiveChange,
  onDeleteUser,
  busyUserId,
}) {
  return (
    <div className="activity-table-wrap">
      <table className="activity-table admin-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Role</th>
            <th>Status</th>
            <th>Joined</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {users.length === 0 ? (
            <tr>
              <td className="activity-empty" colSpan="5">No users found.</td>
            </tr>
          ) : (
            users.map((user) => (
              <tr key={user.id}>
                <td>
                  <div className="activity-user">{user.name || "Unnamed user"}</div>
                  <div className="muted">{user.email}</div>
                </td>
                <td>
                  <select
                    aria-label={`Change role for ${user.email}`}
                    value={user.role}
                    disabled={busyUserId === user.id}
                    onChange={(event) => onRoleChange(user, event.target.value)}
                  >
                    <option value="viewer">Viewer</option>
                    <option value="owner">Owner</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td>
                  <span
                    className="admin-status"
                    style={!user.active ? { background: "#fff0ef", color: "#bd3030" } : undefined}
                  >
                    {user.active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>{formatDate(user.created_at)}</td>
                <td>
                  <button
                    type="button"
                    className="text-action"
                    disabled={busyUserId === user.id}
                    onClick={() => onActiveChange(user, !user.active)}
                  >
                    {busyUserId === user.id ? "Saving…" : user.active ? "Deactivate" : "Activate"}
                  </button>
                  {user.role !== "admin" && (
                    <button
                      type="button"
                      className="text-action"
                      style={{ color: "#bd3030", marginLeft: "12px" }}
                      disabled={busyUserId === user.id}
                      onClick={() => onDeleteUser(user)}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}