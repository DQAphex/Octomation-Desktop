export interface WorkspacePlugin {
  workspacePluginId: string;
  workspaceId: string;
  pluginId: string;
  installedAt: string;
  updatedAt: string;
}

export interface PluginRelease {
  id: number;
  tag: string;
  version: string;
  name: string;
  downloadUrl: string;
}

const PLUGINS_URL = "http://localhost:4005";

export async function getWorkspacePlugins(
  workspaceId: string
): Promise<WorkspacePlugin[]> {
  const response = await fetch(
    `${PLUGINS_URL}/workspaces/${encodeURIComponent(workspaceId)}/plugins`
  );

  if (!response.ok) {
    throw new Error(
      `Error al obtener los plugins del workspace: ${response.status} ${response.statusText}`
    );
  }

  const data: WorkspacePlugin[] = await response.json();

  return data;
}

export async function getLatestPluginRelease(
  pluginId: string
): Promise<PluginRelease> {
  const response = await fetch(
    `${PLUGINS_URL}/plugins/${encodeURIComponent(pluginId)}/releases/latest`
  );

  if (!response.ok) {
    throw new Error(
      `Error al obtener la última release del plugin: ${response.status} ${response.statusText}`
    );
  }

  const data: PluginRelease = await response.json();

  return data;
}