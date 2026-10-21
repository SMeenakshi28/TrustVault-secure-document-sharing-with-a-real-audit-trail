import { useState } from "react";
import AuthPage from "./components/AuthPage";
import OwnerDashboard from "./owner/OwnerDashboard";
import AdminDashboard from "./admin/AdminDashboard";
import ViewerDashboard from "./viewer/ViewerDashboard";
import "./App.css";

function App() {
  const [page, setPage] = useState("login");
  const [selectedRole, setSelectedRole] = useState("owner");
  const [form, setForm] = useState({
    name: "",
    username: "",
    email: "",
    password: "",
  });
  const [message, setMessage] = useState("");

  function logout() {
    setForm({ name: "", username: "", email: "", password: "" });
    setSelectedRole("owner");
    setPage("login");
    setMessage("");
  }

  if (page === "dashboard") {
    if (selectedRole === "owner") return <OwnerDashboard form={form} selectedRole={selectedRole} logout={logout} />;
    if (selectedRole === "admin") return <AdminDashboard form={form} selectedRole={selectedRole} logout={logout} />;
    if (selectedRole === "viewer") return <ViewerDashboard form={form} selectedRole={selectedRole} logout={logout} />;
  }

  return (
    <AuthPage 
      page={page} 
      setPage={setPage} 
      form={form} 
      setForm={setForm} 
      selectedRole={selectedRole} 
      setSelectedRole={setSelectedRole}
      message={message}
      setMessage={setMessage}
    />
  );
}

export default App;