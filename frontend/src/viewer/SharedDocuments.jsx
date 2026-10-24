function formatExpiration(expiration) {
  if (!expiration) return "No expiry";
  const date = new Date(expiration);
  if (Number.isNaN(date.getTime())) return "No expiry";
  return date.toLocaleString();
}

export default function SharedDocuments({
  sharedDocuments,
  searchQuery,
  setSearchQuery,
  loading,
  error,
  accessDocument,
  setSelectedView
}) {
  const filteredDocuments = sharedDocuments.filter((document) =>
    `${document.name} ${document.owner}`.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <section className="panel viewer-documents">
      <div className="panel-heading">
        <div>
          <h2>Shared with me</h2>
          <p className="muted">Only documents shared with your signed-in account are listed.</p>
        </div>
        <button type="button" className="primary-button" onClick={() => setSelectedView("shared_with_me")}>
          Browse Shared files <span aria-hidden="true">→</span>
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="viewer-search">
        <input
          type="search"
          aria-label="Search shared files"
          placeholder="Search shared files..."
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
        />
      </div>

      <div className="activity-table-wrap">
        <table className="activity-table viewer-table">
          <thead>
            <tr>
              <th scope="col">Document</th>
              <th scope="col">Shared By</th>
              <th scope="col">Permission</th>
              <th scope="col">Expires</th>
              <th scope="col">Access</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="activity-empty" colSpan="5">Loading shared documents...</td>
              </tr>
            ) : filteredDocuments.length === 0 ? (
              <tr>
                <td className="activity-empty" colSpan="5">
                  Nothing Here{searchQuery && " — no shared files match your search."}
                </td>
              </tr>
            ) : (
              filteredDocuments.map((document) => (
                <tr key={document.id}>
                  <td className="activity-action">{document.name}</td>
                  <td>{document.owner}</td>
                  <td>{document.permission}</td>
                  <td>{formatExpiration(document.expiration === "No expiry" ? null : document.expiration)}</td>
                  <td>
                    {document.viewed || document.viewed_at ? (
                      <span className="muted">Used</span>
                    ) : (
                      <>
                        <button type="button" className="text-action" onClick={() => accessDocument(document)}>
                          Open
                        </button>
                        {document.can_download && (
                          <button type="button" className="text-action" onClick={() => accessDocument(document, true)}>
                            Download
                          </button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}