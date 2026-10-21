import Sidebar from "./Sidebar";

export default function DashboardLayout({ children, viewTitle, selectedRole, selectedView, setSelectedView, form, logout }) {
  return (
    <div className="dashboard-layout">
      <Sidebar 
        selectedRole={selectedRole} 
        selectedView={selectedView} 
        setSelectedView={setSelectedView} 
        form={form} 
        logout={logout} 
      />
      <main className="dashboard-main">
        <header className="dashboard-topbar">
          <span>Workspace / {viewTitle}</span>
          <span className="secure-label">♧ Secure workspace</span>
        </header>
        <section className="dashboard-content">
          {children}
          <p className="prototype-notice">Frontend prototype · No real accounts or documents are stored.</p>
        </section>
      </main>
    </div>
  );
}