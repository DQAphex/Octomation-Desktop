

import { tenantsApi } from "./clients";

export interface Member {
  memberId: string;
  iamUserId: string;
  tenantId: string;
  name?: string;
  lastname?: string;
  profilePicture?: string;
  status: string;
}

export async function getMemberByIamUserId(
  iamUserId: string
): Promise<Member> {
  const { data } = await tenantsApi.get<Member>(
    `/members/data/iam-user/${encodeURIComponent(iamUserId)}`
  );

  return data;
}
