export interface Workspace {
  tenantId: string;
  workspaceId: string;
  workspaceNombre: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

interface WorkspacesResponse {
  data: Workspace[];
}

const TENANTS_URL = "http://localhost:4004";

export async function getWorkspacesByIamUserId(
  iamUserId: string
): Promise<Workspace[]> {
  const response = await fetch(
    `${TENANTS_URL}/workspaces/get-all-workspaces-by-iam-id/${encodeURIComponent(iamUserId)}`
  );

  if (!response.ok) {
    throw new Error(
      `Error al obtener workspaces: ${response.status} ${response.statusText}`
    );
  }

  const result: WorkspacesResponse = await response.json();

  return result.data ?? [];
}