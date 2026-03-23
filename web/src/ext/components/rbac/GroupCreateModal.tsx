"use client";

import { useState } from "react";

import { Button } from "@opal/components";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import Text from "@/refresh-components/texts/Text";

import { createUserGroup } from "@/ext/components/rbac/svc";

interface GroupCreateModalProps {
  onClose: () => void;
  onCreated: () => void;
}

export default function GroupCreateModal({
  onClose,
  onCreated,
}: GroupCreateModalProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    if (!name.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      await createUserGroup({ name: name.trim() });
      onCreated();
    } catch (e: any) {
      setError(e.message || "Fehler beim Erstellen der Gruppe.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background-neutral-01 border border-border-01 rounded-lg p-6 w-full max-w-md shadow-lg">
        <Text mainContentBody>
          <strong>Neue Gruppe erstellen</strong>
        </Text>

        <div className="mt-4">
          <Text text03 mainContentBody>
            Gruppenname
          </Text>
          <div className="mt-1">
            <InputTypeIn
              placeholder="z.B. Geschäftsleitung"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit();
              }}
            />
          </div>
        </div>

        {error && (
          <div className="mt-3 text-status-error-01">
            <Text mainContentBody>{error}</Text>
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button onClick={onClose}>Abbrechen</Button>
          <Button variant="action" onClick={handleSubmit}>
            {loading ? "Erstellen..." : "Erstellen"}
          </Button>
        </div>
      </div>
    </div>
  );
}
