"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";

import * as SettingsLayouts from "@/layouts/settings-layouts";
import { Button } from "@opal/components";
import { SvgUserManage, SvgTrash } from "@opal/icons";
import Card from "@/refresh-components/cards/Card";
import { ContentAction } from "@opal/layouts";
import SimpleLoader from "@/refresh-components/loaders/SimpleLoader";
import Text from "@/refresh-components/texts/Text";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { UserGroup } from "@/lib/types";

import {
  deleteUserGroup,
  setCuratorStatus,
} from "@/ext/components/rbac/svc";

const USER_GROUP_URL = "/api/manage/admin/user-group";

export default function GroupDetailPage() {
  const params = useParams();
  const router = useRouter();
  const groupId = Number(params.groupId);

  const [deleting, setDeleting] = useState(false);

  const {
    data: groups,
    error,
    isLoading,
    mutate,
  } = useSWR<UserGroup[]>(USER_GROUP_URL, errorHandlingFetcher);

  const group = groups?.find((g) => g.id === groupId);

  async function handleDelete() {
    if (deleting) return;
    if (!confirm(`Gruppe "${group?.name}" wirklich löschen?`)) return;
    setDeleting(true);
    try {
      await deleteUserGroup(groupId);
      router.push("/admin/ext-groups");
    } catch (e: any) {
      alert(e.message || "Fehler beim Löschen.");
      setDeleting(false);
    }
  }

  async function handleToggleCurator(
    userId: string,
    currentlyIsCurator: boolean
  ) {
    try {
      await setCuratorStatus(groupId, userId, !currentlyIsCurator);
      mutate();
    } catch (e: any) {
      alert(e.message || "Fehler beim Ändern des Curator-Status.");
    }
  }

  if (isLoading) {
    return (
      <SettingsLayouts.Root>
        <SettingsLayouts.Body>
          <SimpleLoader />
        </SettingsLayouts.Body>
      </SettingsLayouts.Root>
    );
  }

  if (error || !group) {
    return (
      <SettingsLayouts.Root>
        <SettingsLayouts.Body>
          <Text mainContentBody>Gruppe nicht gefunden.</Text>
        </SettingsLayouts.Body>
      </SettingsLayouts.Root>
    );
  }

  return (
    <SettingsLayouts.Root>
      <SettingsLayouts.Header
        icon={SvgUserManage}
        title={group.name}
        description={`${group.users.length} Mitglieder · ${group.cc_pairs.length} Connectoren · ${group.personas.length} Agenten`}
        rightChildren={
          <Button icon={SvgTrash} variant="danger" onClick={handleDelete}>
            {deleting ? "Löschen..." : "Gruppe löschen"}
          </Button>
        }
      />

      <SettingsLayouts.Body>
        {/* Members */}
        <div className="mb-6">
          <Text mainContentEmphasis>Mitglieder</Text>
          <div className="mt-2 flex flex-col gap-1">
            {group.users.length === 0 && (
              <Text mainContentMuted>Keine Mitglieder.</Text>
            )}
            {group.users.map((user: any) => {
              const isCurator = group.curator_ids.includes(user.id);
              return (
                <Card key={user.id}>
                  <ContentAction
                    sizePreset="main-ui"
                    variant="section"
                    title={user.email}
                    description={
                      isCurator
                        ? "Curator"
                        : user.role === "admin"
                          ? "Admin"
                          : "Mitglied"
                    }
                    rightChildren={
                      user.role !== "admin" ? (
                        <Button
                          variant={isCurator ? "danger" : "action"}
                          size="sm"
                          onClick={() =>
                            handleToggleCurator(user.id, isCurator)
                          }
                        >
                          {isCurator
                            ? "Curator entfernen"
                            : "Als Curator setzen"}
                        </Button>
                      ) : undefined
                    }
                  />
                </Card>
              );
            })}
          </div>
        </div>

        {/* Connectors */}
        {group.cc_pairs.length > 0 && (
          <div className="mb-6">
            <Text mainContentEmphasis>Connectoren</Text>
            <div className="mt-2 flex flex-col gap-1">
              {group.cc_pairs.map((cc: any) => (
                <Card key={cc.id}>
                  <ContentAction
                    sizePreset="main-ui"
                    variant="section"
                    title={cc.name || `Connector ${cc.id}`}
                    description={cc.connector?.source || ""}
                  />
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Agents */}
        {group.personas.length > 0 && (
          <div className="mb-6">
            <Text mainContentEmphasis>Agenten</Text>
            <div className="mt-2 flex flex-col gap-1">
              {group.personas.map((p: any) => (
                <Card key={p.id}>
                  <ContentAction
                    sizePreset="main-ui"
                    variant="section"
                    title={p.name || `Agent ${p.id}`}
                  />
                </Card>
              ))}
            </div>
          </div>
        )}
      </SettingsLayouts.Body>
    </SettingsLayouts.Root>
  );
}
