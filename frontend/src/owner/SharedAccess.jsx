import { useState } from "react";

export default function SharedAccess({ sharedUsers, setSharedUsers }) {
  const [showAddUser, setShowAddUser] = useState(false);

  function addUser(event) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const user = {
      id: crypto.randomUUID(),
      name: formData.get("name").trim(),
      email: formData.get("email").trim(),
      document: formData.get("document").trim(),
      permission: formData.get("permission"),
      sharedAt: new Date().toLocaleString(),
      expiration: formData.get("expiration") || "No expiry",
    };
    setSharedUsers((previous) => [...previous, user]);
    setShowAddUser(false);
    event.currentTarget.reset();
  }

  function revokeAccess(userId) {
    setSharedUsers((previous) => previous.filter((user) => user.id !== userId));
  }

  return (
    <section className="panel shared-access-panel">
      <div className="panel-heading">
        <div>
          <h2>Shared with me</h2>
          <p className="muted">Manage access you have granted to other people.</p>
        </div>
        <button type="button" className="primary-button" onClick={() => setShowAddUser((prev) => !prev)}>
          {showAddUser ? "Cancel" : "+ Add User"}
        </button>
      </div>

      {showAddUser && (
        <form className="add-user-form" onSubmit={addUser}>
          <label>User name <input name="name" placeholder="Enter user's name" required /></label>
          <label>Email <input name="email" type="email" placeholder="name@example.com" required /></label>
          <label>Document <input name="document" placeholder="e.g. picture.jpg" required /></label>
          <label>Permission 
            <select name="permission" defaultValue="View">
              <option>View</option>
              <option>View and download</option>
            </select>
          </label>
          <label>Expires <input name="expiration" type="date" /></label>
          <button type="submit" className="primary-button">Share access</button>
        </form>
      )}

      {sharedUsers.length === 0 ? (
        <div className="empty-state compact-empty-state">
          <div className="empty-icon">♧</div>
          <h3>No Shared Access</h3>
          <p>People you share documents with will appear here.</p>
        </div>
      ) : (
        <div className="shared-user-list">
          {sharedUsers.map((user) => (
            <article className="shared-user-row" key={user.id}>
              <div className="profile-avatar" aria-hidden="true">{user.name.charAt(0).toUpperCase()}</div>
              <div className="shared-user-info">
                <strong>{user.document}</strong>
                <span>Shared with {user.name} ({user.email}) · {user.sharedAt}</span>
              </div>
              <span className="shared-permission">{user.permission}</span>
              <span className="shared-expiration">{user.expiration === "No expiry" ? "No expiry" : `Expires ${user.expiration}`}</span>
              <button type="button" className="revoke-button" onClick={() => revokeAccess(user.id)}>Revoke access</button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}