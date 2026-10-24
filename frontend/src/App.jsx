import { useState } from "react";
import AuthPage from "./components/AuthPage";
import OwnerDashboard from "./owner/OwnerDashboard";
import AdminDashboard from "./admin/AdminDashboard";
import ViewerDashboard from "./viewer/ViewerDashboard";
import "./App.css";

const emptyForm = {
  name: "",
  username: "",
  email: "",
  password: "",
};

function App() {
  const [page, setPage] = useState("login");
  const [selectedRole, setSelectedRole] = useState("viewer");
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const [accessToken, setAccessToken] = useState("");

  function logout() {
    setForm(emptyForm);
    setSelectedRole("viewer");
    setAccessToken("");
    setPage("login");
    setMessage("");
  }

  if (page === "dashboard" && accessToken) {
    if (selectedRole === "owner") {
      return (
        <OwnerDashboard
          form={form}
          setForm={setForm}
          selectedRole={selectedRole}
          accessToken={accessToken}
          logout={logout}
        />
      );
    }

    if (selectedRole === "admin") {
      return (
        <AdminDashboard
          form={form}
          setForm={setForm}
          selectedRole={selectedRole}
          accessToken={accessToken}
          logout={logout}
        />
      );
    }

    if (selectedRole === "viewer") {
      return (
        <ViewerDashboard
          form={form}
          setForm={setForm}
          selectedRole={selectedRole}
          accessToken={accessToken}
          logout={logout}
        />
      );
    }
  }

  return (
    <AuthPage
      page={page}
      setPage={setPage}
      form={form}
      setForm={setForm}
      selectedRole={selectedRole}
      setSelectedRole={setSelectedRole}
      setAccessToken={setAccessToken}
      message={message}
      setMessage={setMessage}
    />
  );
}

export default App;