"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";

import * as SettingsLayouts from "@/layouts/settings-layouts";
import { Button } from "@opal/components";
import { SvgPlusCircle, SvgUserManage, SvgChevronRight } from "@opal/icons";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { Content, ContentAction } from "@opal/layouts";
import Card from "@/refresh-components/cards/Card";
import SimpleLoader from "@/refresh-components/loaders/SimpleLoader";
import Text from "@/refresh-components/texts/Text";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { UserGroup } from "@/lib/types";

import GroupCreateModal from "@/ext/components/rbac/GroupCreateModal";

const USER_GROUP_URL = "/api/manage/admin/user-group";

function formatMemberCount(count: number): string {
  return count === 1 ? "1 Mitglied" : `${count} Mitglieder`;
}

function buildGroupDescription(group: UserGroup): string {
  const parts: string[] = [];
  if (group.cc_pairs.length > 0) {
    parts.push(
      `${group.cc_pairs.length} Connector${group.cc_pairs.length !== 1 ? "en" : ""}`
    );
  }
  if (group.document_sets.length > 0) {
    parts.push(`${group.document_sets.length} Dokumentensammlungen`);
  }
  if (group.personas.length > 0) {
    parts.push(
      `${group.personas.length} Agent${group.personas.length !== 1 ? "en" : ""}`
    );
  }
  return parts.length > 0
    ? parts.join(" · ")
    : "Keine Connectoren / Dokumentensammlungen / Agenten";
}

export default function GroupsListPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const {
    data: groups,
    error,
    isLoading,
    mutate,
  } = useSWR<UserGroup[]>(USER_GROUP_URL, errorHandlingFetcher);

  const filteredGroups = (groups || []).filter((g) =>
    g.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <SettingsLayouts.Root>
      <SettingsLayouts.Header
        icon={SvgUserManage}
        title="Gruppen"
        description="Verwalten Sie Benutzergruppen und Zugriffsberechtigungen"
        rightChildren={
          <Button
            icon={SvgPlusCircle}
            variant="action"
            prominence="primary"
            onClick={() => setShowCreateModal(true)}
          >
            Neue Gruppe
          </Button>
        }
      >
        <InputTypeIn
          placeholder="Gruppen durchsuchen..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </SettingsLayouts.Header>

      <SettingsLayouts.Body>
        {isLoading && <SimpleLoader />}

        {error && (
          <Text mainContentMuted>
            Fehler beim Laden der Gruppen.
          </Text>
        )}

        {!isLoading && !error && filteredGroups.length === 0 && (
          <Text mainContentMuted>
            {searchQuery
              ? "Keine Gruppen gefunden."
              : "Noch keine Gruppen erstellt. Klicken Sie auf \"Neue Gruppe\" um zu beginnen."}
          </Text>
        )}

        <div className="flex flex-col gap-2">
          {filteredGroups.map((group) => (
            <Card key={group.id}>
              <ContentAction
                sizePreset="main-ui"
                variant="section"
                icon={SvgUserManage}
                title={group.name}
                description={buildGroupDescription(group)}
                rightChildren={
                  <div className="flex items-center gap-3">
                    <Text mainContentMuted>
                      {formatMemberCount(group.users.length)}
                    </Text>
                    <Button
                      icon={SvgChevronRight}
                      variant="default"
                      prominence="tertiary"
                      size="sm"
                      onClick={() =>
                        router.push(`/admin/ext-groups/${group.id}`)
                      }
                    />
                  </div>
                }
              />
            </Card>
          ))}
        </div>
      </SettingsLayouts.Body>

      {showCreateModal && (
        <GroupCreateModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false);
            mutate();
          }}
        />
      )}
    </SettingsLayouts.Root>
  );
}
