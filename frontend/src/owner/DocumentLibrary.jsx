export default function DocumentLibrary({ setMessage }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>My Documents</h2>
          <p className="muted">Upload and organise your confidential files.</p>
        </div>
        <button type="button" className="primary-button" onClick={() => setMessage("Document upload will be connected to the backend later.")}>
          + Upload document
        </button>
      </div>

      <div className="search-row">
        <input aria-label="Search documents" placeholder="Search documents..." />
        <select aria-label="Filter documents">
          <option>All categories</option>
          <option>Contracts</option>
          <option>Reports</option>
          <option>Personal</option>
          <option>Other</option>
        </select>
      </div>

      <div className="empty-state">
        <div className="empty-icon">▤</div>
        <h3>Nothing Here</h3>
        <p>Your documents will appear here after you upload them.</p>
      </div>
    </section>
  );
}