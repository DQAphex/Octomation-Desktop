
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getWorkspacesByIamUserId,
  type Workspace
} from "../api/workspaces.api";
import {
  getWorkspacePlugins
} from "../api/plugins.api";
import { useAuth } from "../auth/AuthContext";

interface WorkspaceWithPlugins extends Workspace {
  pluginCount: number;
}

export default function Workspaces() {
  const { user } = useAuth();

  const [workspaces, setWorkspaces] = useState<WorkspaceWithPlugins[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.id) {
      setWorkspaces([]);
      setLoading(false);
      setError("No se pudo identificar al usuario autenticado.");
      return;
    }

    let cancelled = false;

    async function loadWorkspaces() {
      setLoading(true);
      setError(null);

      try {
        const userWorkspaces = await getWorkspacesByIamUserId(user!.id);

        const results = await Promise.all(
          userWorkspaces.map(async (workspace) => {
            let pluginCount = 0;

            try {
              const plugins = await getWorkspacePlugins(
                workspace.workspaceId
              );
              pluginCount = plugins.length;
            } catch (err) {
              console.error(
                `Error al cargar plugins del workspace ${workspace.workspaceId}:`,
                err
              );
            }

            return {
              ...workspace,
              pluginCount
            };
          })
        );

        if (!cancelled) {
          setWorkspaces(results);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "No se pudieron cargar los workspaces."
          );
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

  if (loading) {
    return (
      <div className="page-container">
        <p>Cargando tus workspaces...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1>Mis workspaces</h1>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Mis workspaces</h1>
          <p>Consulta tus espacios de trabajo y sus plugins asociados.</p>
        </div>

        <span>{workspaces.length} workspaces</span>
      </div>

      {workspaces.length === 0 ? (
        <div className="plugin-card">
          <h2>Sin workspaces</h2>
          <p>No tienes workspaces asociados a tu usuario.</p>
        </div>
      ) : (
        <section className="workspace-detail-grid">
          {workspaces.map((workspace) => (
            <article
              className="plugin-card"
              key={workspace.workspaceId}
            >
              <h2>{workspace.workspaceNombre}</h2>

              <div className="plugin-meta">
                <span>
                  <strong>ID:</strong> {workspace.workspaceId}
                </span>

                <span>
                  <strong>Tenant:</strong> {workspace.tenantId}
                </span>

                <span>
                  <strong>Estado:</strong> {workspace.status}
                </span>

                <span>
                  <strong>Plugins asociados:</strong>{" "}
                  {workspace.pluginCount}
                </span>

                <span>
                  <strong>Creado:</strong>{" "}
                  {workspace.createdAt
                    ? new Date(workspace.createdAt).toLocaleDateString("es-CL")
                    : "-"}
                </span>
              </div>

              <Link to={`/workspaces/${workspace.workspaceId}`}>
                Ver workspace
              </Link>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
