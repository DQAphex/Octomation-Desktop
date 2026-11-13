
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useEffect, useState } from "react";
import {
  getWorkspacesByIamUserId,
  type Workspace
} from "../api/workspaces.api";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user?.id) {
      setWorkspaces([]);
      return;
    }

    let cancelled = false;

    async function loadWorkspaces() {
      setLoading(true);
      setError(null);

      try {
        const data = await getWorkspacesByIamUserId(user!.id);

        if (!cancelled) {
          setWorkspaces(data);
        }
      } catch {
        if (!cancelled) {
          setError("No se pudieron cargar los workspaces.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadWorkspaces();

    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">Octomation</div>

          <div className="sidebar-user">
            <div className="sidebar-user-label">Nombre de Usuario</div>
            <div className="sidebar-user-name">
              {user?.fullName || "-"}
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="material-symbols-outlined">
              home
            </span>
            Inicio
          </NavLink>

          <NavLink
            to="/plugins"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="material-symbols-outlined">
              extension
            </span>
            Plugins
          </NavLink>
          <NavLink
            to="/workspaces"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="material-symbols-outlined">
              groups
            </span>
            Workspaces
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <button
            className="sidebar-logout"
            onClick={logout}
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
