import { useEffect, useState } from "react";
import { apiRequest } from "../api";

export default function UserSettings({
  form,
  setForm,
  selectedRole,
  accessToken,
  logout,
}) {
  const [name, setName] = useState(form.name || "");
  const email = form.email || "";
  const [ownerRequest, setOwnerRequest] = useState(null);
  const [requestLoading, setRequestLoading] = useState(false);
  const [requestError, setRequestError] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (selectedRole !== "viewer") return undefined;

    let cancelled = false;
    apiRequest("/auth/owner-access-request", {}, accessToken)
      .then((request) => {
        if (!cancelled) setOwnerRequest(request);
      })
      .catch((err) => {
        if (!cancelled) {
          setRequestError(err.message || "Could not load Owner access request status.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, selectedRole]);

  async function requestOwnerAccess() {
    setRequestLoading(true);
    setRequestError("");
    try {
      const request = await apiRequest(
        "/auth/owner-access-request",
        { method: "POST" },
        accessToken
      );
      setOwnerRequest(request);
    } catch (err) {
      setRequestError(err.message || "Could not request Owner access.");
    } finally {
      setRequestLoading(false);
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Name cannot be empty.");
      return;
    }
    setLoading(true);
    try {
      const result = await apiRequest("/auth/profile", {
        method: "PATCH",
        body: JSON.stringify({ name: trimmed }),
      }, accessToken);
      setForm((previous) => ({ ...previous, name: result.name, email: result.email }));
      setMessage("Your profile name has been updated.");
    } catch (err) {
      setError(err.message || "Could not update your profile.");
    } finally {
      setLoading(false);
    }
  }

  async function deleteAccount() {
    const confirmed = window.confirm(
      "Are you sure you want to delete your TrustVault account? You will be signed out. Shared access will be revoked. Historical audit records and document records may be retained to preserve accountability."
    );
    if (!confirmed) return;
    setLoading(true);
    setMessage("");
    setError("");
    try {
      await apiRequest("/auth/account", { method: "DELETE" }, accessToken);
      logout();
    } catch (err) {
      setError(err.message || "Account deletion failed. Your account has not been signed out.");
      setLoading(false);
    }
  }

  return (
    <div className="settings-page">
      <div className="page-heading">
        <p className="eyebrow">ACCOUNT</p>
        <h1>User Settings</h1>
        <p className="muted">Manage your profile and account access.</p>
      </div>

      <section className="settings-card">
        <h2>Profile information</h2>
        <p className="muted">Your email identifies the account you signed in with and cannot be changed here.</p>
        <form onSubmit={saveProfile} className="settings-form">
          <label htmlFor="settings-name">Full name</label>
          <input id="settings-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={100} required />
          <label htmlFor="settings-email">Email address</label>
          <input id="settings-email" type="email" value={email} readOnly aria-readonly="true" />
          <button className="primary-button" type="submit" disabled={loading || !name.trim() || name.trim() === (form.name || "").trim()}>
            {loading ? "Please wait..." : "Save changes"}
          </button>
        </form>
        {message && <p className="settings-success" role="status">{message}</p>}
        {error && <p className="form-message" role="alert">{error}</p>}
      </section>

      {selectedRole === "viewer" && (
        <section className="settings-card">
          <h2>Request Owner access</h2>
          <p className="muted">
            An Admin must review your request before your account can create and share documents.
          </p>
          {ownerRequest?.status === "pending" ? (
            <p role="status">Your request is pending Admin review.</p>
          ) : ownerRequest?.status === "approved" ? (
            <p role="status">Your request was approved. Sign out and back in to refresh your dashboard role.</p>
          ) : ownerRequest?.status === "rejected" ? (
            <p role="status">Your request was rejected. You may submit a new request.</p>
          ) : (
            <button
              type="button"
              className="primary-button"
              disabled={requestLoading}
              onClick={requestOwnerAccess}
            >
              {requestLoading ? "Submitting..." : "Request Owner access"}
            </button>
          )}
          {requestError && <p className="form-message" role="alert">{requestError}</p>}
        </section>
      )}

      <section className="settings-card settings-danger-card">
        <h2>Delete account</h2>
        <p>Delete your sign-in account and revoke your active shares. TrustVault may retain document metadata or audit records when needed to preserve the integrity of its activity history.</p>
        <button type="button" className="danger-button" disabled={loading} onClick={deleteAccount}>
          Delete my account
        </button>
      </section>
    </div>
  );
}
