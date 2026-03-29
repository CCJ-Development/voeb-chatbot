"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Text from "@/refresh-components/texts/Text";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import Button from "@/refresh-components/buttons/Button";
import LogoCropModal from "@/ext/components/LogoCropModal";
import { useRouter } from "next/navigation";

interface BrandingConfig {
  application_name: string | null;
  use_custom_logo: boolean;
  use_custom_logotype: boolean;
  logo_display_style: "logo_and_name" | "logo_only" | "name_only" | null;
  custom_nav_items: { link: string; title: string }[];
  custom_lower_disclaimer_content: string | null;
  custom_header_content: string | null;
  two_lines_for_chat_header: boolean | null;
  custom_popup_header: string | null;
  custom_popup_content: string | null;
  enable_consent_screen: boolean | null;
  consent_screen_prompt: string | null;
  show_first_visit_notice: boolean | null;
  custom_greeting_message: string | null;
}

const DEFAULTS: BrandingConfig = {
  application_name: null,
  use_custom_logo: false,
  use_custom_logotype: false,
  logo_display_style: null,
  custom_nav_items: [],
  custom_lower_disclaimer_content: null,
  custom_header_content: null,
  two_lines_for_chat_header: null,
  custom_popup_header: null,
  custom_popup_content: null,
  enable_consent_screen: null,
  consent_screen_prompt: null,
  show_first_visit_notice: null,
  custom_greeting_message: null,
};

export default function ExtBrandingAdminPage() {
  const [config, setConfig] = useState<BrandingConfig>(DEFAULTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [logoVersion, setLogoVersion] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/admin/enterprise-settings");
      if (res.ok) {
        setConfig(await res.json());
      }
    } catch {
      setMessage({ type: "error", text: "Konfiguration konnte nicht geladen werden" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/enterprise-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Erfolgreich gespeichert" });
        router.refresh();
      } else {
        const err = await res.json();
        setMessage({
          type: "error",
          text: err.detail || "Speichern fehlgeschlagen",
        });
      }
    } catch {
      setMessage({ type: "error", text: "Netzwerkfehler" });
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCropFile(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleCropComplete = async (blob: Blob) => {
    setCropFile(null);
    const formData = new FormData();
    formData.append("file", new File([blob], "logo.png", { type: "image/png" }));

    try {
      const res = await fetch("/api/admin/enterprise-settings/logo", {
        method: "PUT",
        body: formData,
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Logo hochgeladen" });
        setConfig((prev) => ({ ...prev, use_custom_logo: true }));
        setLogoVersion((v) => v + 1);
        router.refresh();
      } else {
        const err = await res.json();
        setMessage({
          type: "error",
          text: err.detail || "Logo-Upload fehlgeschlagen",
        });
      }
    } catch {
      setMessage({ type: "error", text: "Netzwerkfehler" });
    }
  };

  const handleLogoDelete = async () => {
    try {
      const res = await fetch("/api/admin/enterprise-settings/logo", {
        method: "DELETE",
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Logo entfernt" });
        setConfig((prev) => ({ ...prev, use_custom_logo: false }));
        setLogoVersion((v) => v + 1);
        router.refresh();
      } else {
        setMessage({ type: "error", text: "Logo konnte nicht entfernt werden" });
      }
    } catch {
      setMessage({ type: "error", text: "Netzwerkfehler" });
    }
  };

  const update = <K extends keyof BrandingConfig>(
    key: K,
    value: BrandingConfig[K]
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="p-8">
        <Text headingH2 className="block">Branding</Text>
        <Text text03 className="block p-4">Laden...</Text>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl">
      <Text headingH2 className="block pb-1">Branding-Konfiguration</Text>
      <Text text03 className="block pb-6">Erscheinungsbild der Anwendung konfigurieren.</Text>

      {message && (
        <div
          className={`p-3 rounded-08 mb-4 ${
            message.type === "success"
              ? "bg-status-success-01 text-status-success-03"
              : "bg-status-error-01 text-status-error-03"
          }`}
        >
          <Text>{message.text}</Text>
        </div>
      )}

      {/* App Name */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Anwendungsname</Text>
        <InputTypeIn
          value={config.application_name || ""}
          onChange={(e) =>
            update(
              "application_name",
              e.target.value || null
            )
          }
          placeholder="e.g. VÖB Chatbot"
          maxLength={50}
        />
      </div>

      {/* Logo */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Logo</Text>
        <div className="flex items-center gap-4">
          {config.use_custom_logo && (
            <img
              src={`/api/enterprise-settings/logo?v=${logoVersion}`}
              alt="Aktuelles Logo"
              className="w-10 h-10 rounded-full object-cover"
            />
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg"
            onChange={handleFileSelect}
            className="text-sm text-text-03"
          />
          {config.use_custom_logo && (
            <Button secondary action onClick={handleLogoDelete}>
              Logo entfernen
            </Button>
          )}
        </div>
        <Text text03 className="block pt-1">PNG oder JPEG, max. 2 MB</Text>
      </div>

      {/* Crop Modal */}
      {cropFile && (
        <LogoCropModal
          imageFile={cropFile}
          onCrop={handleCropComplete}
          onCancel={() => setCropFile(null)}
        />
      )}

      {/* Logo Display Style */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Logo-Anzeigestil</Text>
        <select
          value={config.logo_display_style || ""}
          onChange={(e) =>
            update(
              "logo_display_style",
              (e.target.value || null) as BrandingConfig["logo_display_style"]
            )
          }
          className="w-full p-2 rounded-08 border border-border-02 bg-background-neutral-01 text-text-01"
        >
          <option value="">Standard</option>
          <option value="logo_and_name">Logo + Name</option>
          <option value="logo_only">Nur Logo</option>
          <option value="name_only">Nur Name</option>
        </select>
      </div>

      {/* Chat Header */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Kopfzeilen-Inhalt</Text>
        <InputTypeIn
          value={config.custom_header_content || ""}
          onChange={(e) =>
            update("custom_header_content", e.target.value || null)
          }
          placeholder="e.g. Bundesverband Öffentlicher Banken"
          maxLength={100}
        />
      </div>

      {/* Chat Greeting */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Chat-Begrüßungsnachricht</Text>
        <InputTypeIn
          value={config.custom_greeting_message || ""}
          onChange={(e) =>
            update("custom_greeting_message", e.target.value || null)
          }
          placeholder="e.g. Wie kann ich Ihnen helfen?"
          maxLength={50}
        />
      </div>

      {/* Chat Footer */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Chat-Fußzeile / Haftungsausschluss</Text>
        <InputTypeIn
          value={config.custom_lower_disclaimer_content || ""}
          onChange={(e) =>
            update(
              "custom_lower_disclaimer_content",
              e.target.value || null
            )
          }
          placeholder="e.g. KI-generierte Antworten können fehlerhaft sein."
          maxLength={200}
        />
      </div>

      {/* Welcome Popup */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Erstbesuch-Hinweis</Text>
        <label className="flex items-center gap-2 pb-2">
          <input
            type="checkbox"
            checked={config.show_first_visit_notice || false}
            onChange={(e) =>
              update("show_first_visit_notice", e.target.checked || null)
            }
          />
          <Text>Popup beim ersten Besuch anzeigen</Text>
        </label>
        {config.show_first_visit_notice && (
          <div className="space-y-3 pt-2">
            <InputTypeIn
              value={config.custom_popup_header || ""}
              onChange={(e) =>
                update("custom_popup_header", e.target.value || null)
              }
              placeholder="Popup-Titel"
              maxLength={100}
            />
            <InputTextArea
              value={config.custom_popup_content || ""}
              onChange={(e) =>
                update("custom_popup_content", e.target.value || null)
              }
              placeholder="Popup-Inhalt (Markdown unterstützt)"
              maxLength={500}
              rows={4}
            />
          </div>
        )}
      </div>

      {/* Consent Screen */}
      <div className="pb-6">
        <Text mainUiAction className="block pb-2">Einwilligungsbildschirm</Text>
        <label className="flex items-center gap-2 pb-2">
          <input
            type="checkbox"
            checked={config.enable_consent_screen || false}
            onChange={(e) =>
              update("enable_consent_screen", e.target.checked || null)
            }
          />
          <Text>Einwilligung vor Nutzung erforderlich</Text>
        </label>
        {config.enable_consent_screen && (
          <InputTypeIn
            value={config.consent_screen_prompt || ""}
            onChange={(e) =>
              update("consent_screen_prompt", e.target.value || null)
            }
            placeholder="Einwilligungstext"
            maxLength={200}
          />
        )}
      </div>

      {/* Save */}
      <div className="flex gap-3">
        <Button main primary onClick={handleSave} disabled={saving}>
          {saving ? "Speichern..." : "Konfiguration speichern"}
        </Button>
      </div>
    </div>
  );
}
