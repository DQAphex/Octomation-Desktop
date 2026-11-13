
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  getWorkspacesByIamUserId,
  type Workspace
} from "../api/workspaces.api";
import {
  getWorkspacePlugins,
  getLatestPluginRelease,
  type PluginRelease
} from "../api/plugins.api";

interface PluginRow {
  workspacePluginId: string;
  workspaceId: string;
  workspaceNombre: string;
  pluginId: string;
  installedAt: string;
  release: PluginRelease | null;
}

export default function Plugins() {
  const { user } = useAuth();

  const [plugins, setPlugins] = useState<PluginRow[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("all");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [installing, setInstalling] = useState<string | null>(null);
  const [installed, setInstalled] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  const loadInstalledPlugins = useCallback(async () => {
    if (!user?.id) {
      setPlugins([]);
      setWorkspaces([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const userWorkspaces = await getWorkspacesByIamUserId(user.id);
      setWorkspaces(userWorkspaces);

      const workspaceResults = await Promise.all(
        userWorkspaces.map(async (workspace) => {
          try {
            const workspacePlugins = await getWorkspacePlugins(
              workspace.workspaceId
            );

            return workspacePlugins.map((plugin) => ({
              ...plugin,
              workspaceNombre: workspace.workspaceNombre
            }));
          } catch (err) {
            console.error(
              `No se pudieron cargar los plugins de ${workspace.workspaceNombre}:`,
              err
            );

            return [];
          }
        })
      );

      const associations = workspaceResults.flat();

      const rows = await Promise.all(
        associations.map(async (plugin) => {
          let release: PluginRelease | null = null;

          try {
            release = await getLatestPluginRelease(plugin.pluginId);
          } catch (err) {
            console.error(
              `No se pudo obtener la release de ${plugin.pluginId}:`,
              err
            );
          }

          return {
            workspacePluginId: plugin.workspacePluginId,
            workspaceId: plugin.workspaceId,
            workspaceNombre: plugin.workspaceNombre,
            pluginId: plugin.pluginId,
            installedAt: plugin.installedAt,
            release
          };
        })
      );

      setPlugins(rows);
    } catch (err) {
      console.error("Error al cargar los plugins:", err);

      setError(
        err instanceof Error
          ? err.message
          : "No se pudieron cargar los plugins."
      );

      setPlugins([]);
      setWorkspaces([]);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    void loadInstalledPlugins();
  }, [loadInstalledPlugins]);

  const filteredPlugins = useMemo(() => {
    if (selectedWorkspaceId === "all") {
      return plugins;
    }

    return plugins.filter(
      (plugin) => plugin.workspaceId === selectedWorkspaceId
    );
  }, [plugins, selectedWorkspaceId]);

  const installPlugin = async (pluginId: string) => {
    setInstalling(pluginId);
    setMessage(`Instalando plugin ${pluginId}...`);

    try {
      const result = await window.api.downloadPlugin(pluginId);

      if (!result.success) {
        throw new Error(result.error || "No se pudo instalar el plugin.");
      }

      setInstalled((previous) =>
        previous.includes(pluginId)
          ? previous
          : [...previous, pluginId]
      );

      setMessage(
        `${result.message || "Plugin instalado correctamente."}\n` +
        "Revisa la carpeta local de plugins."
      );
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Ocurrió un error al instalar el plugin.";

      setMessage(`Error al instalar ${pluginId}: ${errorMessage}`);
    } finally {
      setInstalling(null);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Plugins</h1>
          <p>Plugins asociados a tus workspaces</p>
        </div>

        <button
          className="btn-primary"
          onClick={() => void loadInstalledPlugins()}
          disabled={loading || installing !== null}
        >
          {loading ? "Cargando..." : "Recargar plugins"}
        </button>
      </div>

      <div className="workspace-filter">
        <label htmlFor="workspace-filter">
          Filtrar por workspace
        </label>

        <select
          id="workspace-filter"
          value={selectedWorkspaceId}
          onChange={(event) => setSelectedWorkspaceId(event.target.value)}
          disabled={loading}
        >
          <option value="all">Todos los workspaces</option>

          {workspaces.map((workspace) => (
            <option
              key={workspace.workspaceId}
              value={workspace.workspaceId}
            >
              {workspace.workspaceNombre}
            </option>
          ))}
        </select>

        <span>
          {filteredPlugins.length}{" "}
          {filteredPlugins.length === 1 ? "plugin" : "plugins"}
        </span>
      </div>

      {error && (
        <div className="login-error">
          Error al cargar plugins: {error}
        </div>
      )}

      {loading && <p>Cargando plugins y versiones...</p>}

      {message && <pre className="plugins-log">{message}</pre>}

      {!loading && !error && filteredPlugins.length === 0 && (
        <p>
          {selectedWorkspaceId === "all"
            ? "No hay plugins asociados a tus workspaces."
            : "Este workspace no tiene plugins asociados."}
        </p>
      )}

      {filteredPlugins.length > 0 && (
        <div className="plugins-table-wrapper">
          <table className="plugins-table">
            <thead>
              <tr>
                <th>Plugin</th>
                <th>Versión</th>
                <th>Workspace</th>
                <th>Estado</th>
                <th>Acción</th>
              </tr>
            </thead>

            <tbody>
              {filteredPlugins.map((plugin) => {
                const isInstalling = installing === plugin.pluginId;
                const isInstalled = installed.includes(plugin.pluginId);

                return (
                  <tr key={plugin.workspacePluginId}>
                    <td>{plugin.release?.name || plugin.pluginId}</td>

                    <td>
                      {plugin.release?.version || "No disponible"}
                    </td>

                    <td>{plugin.workspaceNombre}</td>

                    <td>
                      {isInstalling
                        ? "Instalando..."
                        : isInstalled
                          ? "Instalado en esta sesión"
                          : "Disponible"}
                    </td>

                    <td>
                      <button
                        className="btn-download"
                        disabled={
                          isInstalling ||
                          installing !== null ||
                          isInstalled ||
                          !plugin.release
                        }
                        onClick={() => void installPlugin(plugin.pluginId)}
                      >
                        {isInstalling
                          ? "Instalando..."
                          : isInstalled
                            ? "Instalado"
                            : !plugin.release
                              ? "Release no disponible"
                              : "Instalar"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
