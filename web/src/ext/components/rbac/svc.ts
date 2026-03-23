/**
 * API client for ext-rbac group management.
 *
 * All functions use fetch() and throw on non-OK responses.
 */

const ADMIN_GROUP_URL = "/api/manage/admin/user-group";
const MINIMAL_GROUP_URL = "/api/manage/user-groups/minimal";

export async function fetchUserGroups(): Promise<any[]> {
  const res = await fetch(ADMIN_GROUP_URL);
  if (!res.ok) throw new Error(`Failed to fetch groups: ${res.status}`);
  return res.json();
}

export async function fetchMinimalGroups(): Promise<
  { id: number; name: string }[]
> {
  const res = await fetch(MINIMAL_GROUP_URL);
  if (!res.ok) throw new Error(`Failed to fetch groups: ${res.status}`);
  return res.json();
}

export async function createUserGroup(data: {
  name: string;
  user_ids?: string[];
  cc_pair_ids?: number[];
}): Promise<any> {
  const res = await fetch(ADMIN_GROUP_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create group: ${res.status}`);
  }
  return res.json();
}

export async function updateUserGroup(
  groupId: number,
  data: { user_ids: string[]; cc_pair_ids: number[] }
): Promise<any> {
  const res = await fetch(`${ADMIN_GROUP_URL}/${groupId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update group: ${res.status}`);
  }
  return res.json();
}

export async function deleteUserGroup(groupId: number): Promise<void> {
  const res = await fetch(`${ADMIN_GROUP_URL}/${groupId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to delete group: ${res.status}`);
  }
}

export async function addUsersToGroup(
  groupId: number,
  userIds: string[]
): Promise<void> {
  const res = await fetch(`${ADMIN_GROUP_URL}/${groupId}/add-users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_ids: userIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to add users: ${res.status}`);
  }
}

export async function setCuratorStatus(
  groupId: number,
  userId: string,
  isCurator: boolean
): Promise<void> {
  const res = await fetch(`${ADMIN_GROUP_URL}/${groupId}/set-curator`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, is_curator: isCurator }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to set curator: ${res.status}`);
  }
}
