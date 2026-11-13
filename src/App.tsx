
import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import ProtectedRoute from "./auth/ProtectedRoute";
import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Plugins from "./pages/Plugins";
import Workspaces from "./pages/Workspaces";
import { useAuth } from "./auth/AuthContext";
import TitleBar from "./components/TitleBar";

function RootRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ padding: "2rem", color: "#d4d4d4" }}>
        Cargando...
      </div>
    );
  }

  return <Navigate to={user ? "/" : "/login"} replace />;
}

export default function App() {
  return (
    <div className="app-container">

      <TitleBar />
      <div className="app-body">

      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/plugins" element={<Plugins />} />
            <Route path="/workspaces" element={<Workspaces />} />
          </Route>
        </Route>

        <Route path="*" element={<RootRedirect />} />
      </Routes>
      </div>
    </div>
  );
}
