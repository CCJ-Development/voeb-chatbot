"use client";

import { useState, useEffect, useCallback } from "react";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";

// --- Types ---

interface CustomPrompt {
  id: number;
  name: string;
  prompt_text: string;
  category: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface PromptPreview {
  assembled_text: string;
  active_count: number;
  total_count: number;
}

type ViewMode = "list" | "edit" | "preview";

const CATEGORIES = [
  { value: "compliance", label: "Compliance" },
  { value: "tone", label: "Tonality" },
  { value: "context", label: "Context" },
  { value: "instructions", label: "Instructions" },
  { value: "general", label: "General" },
];

const SOFT_LIMIT_ACTIVE = 20;
const SOFT_LIMIT_CHARS = 50_000;

// --- Component ---

export default function ExtPromptsAdminPage() {
  const [prompts, setPrompts] = useState<CustomPrompt[]>([]);
  const [preview, setPreview] = useState<PromptPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("list");
  const [editingPrompt, setEditingPrompt] = useState<CustomPrompt | null>(null);
  const [message, setMessage] = useState<{
    type: "success" | "error" | "warning";
    text: string;
  } | null>(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formText, setFormText] = useState("");
  const [formCategory, setFormCategory] = useState("general");
  const [formPriority, setFormPriority] = useState("100");
  const [formActive, setFormActive] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchPrompts = useCallback(async () => {
    try {
      const res = await fetch("/api/ext/prompts");
      if (res.ok) setPrompts(await res.json());
    } catch {
      /* ignore */
    }
  }, []);

  const fetchPreview = useCallback(async () => {
    try {
      const res = await fetch("/api/ext/prompts/preview");
      if (res.ok) setPreview(await res.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchPrompts(), fetchPreview()]).finally(() =>
      setLoading(false)
    );
  }, [fetchPrompts, fetchPreview]);

  const resetForm = () => {
    setFormName("");
    setFormText("");
    setFormCategory("general");
    setFormPriority("100");
    setFormActive(true);
    setEditingPrompt(null);
  };

  const openCreate = () => {
    resetForm();
    setView("edit");
  };

  const openEdit = (prompt: CustomPrompt) => {
    setEditingPrompt(prompt);
    setFormName(prompt.name);
    setFormText(prompt.prompt_text);
    setFormCategory(prompt.category);
    setFormPriority(String(prompt.priority));
    setFormActive(prompt.is_active);
    setView("edit");
  };

  const handleSave = async () => {
    setMessage(null);
    if (!formName.trim() || !formText.trim()) {
      setMessage({ type: "error", text: "Name and prompt text are required." });
      return;
    }

    setSaving(true);
    try {
      const body = {
        name: formName.trim(),
        prompt_text: formText.trim(),
        category: formCategory,
        priority: parseInt(formPriority, 10) || 100,
        is_active: formActive,
      };

      const url = editingPrompt
        ? `/api/ext/prompts/${editingPrompt.id}`
        : "/api/ext/prompts";
      const method = editingPrompt ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        setMessage({
          type: "success",
          text: editingPrompt ? "Prompt updated." : "Prompt created.",
        });
        resetForm();
        setView("list");
        fetchPrompts();
        fetchPreview();
      } else {
        const err = await res.json();
        setMessage({
          type: "error",
          text: err.detail || "Failed to save prompt.",
        });
      }
    } catch {
      setMessage({ type: "error", text: "Network error." });
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (prompt: CustomPrompt) => {
    try {
      await fetch(`/api/ext/prompts/${prompt.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !prompt.is_active }),
      });
      fetchPrompts();
      fetchPreview();
    } catch {
      /* ignore */
    }
  };

  const handleDelete = async (prompt: CustomPrompt) => {
    if (!confirm(`Delete prompt "${prompt.name}"?`)) return;
    try {
      await fetch(`/api/ext/prompts/${prompt.id}`, { method: "DELETE" });
      setMessage({ type: "success", text: "Prompt deleted." });
      fetchPrompts();
      fetchPreview();
    } catch {
      setMessage({ type: "error", text: "Failed to delete." });
    }
  };

  // Soft-limit warnings
  const activeCount = prompts.filter((p) => p.is_active).length;
  const totalChars = prompts
    .filter((p) => p.is_active)
    .reduce((sum, p) => sum + p.prompt_text.length, 0);
  const showLimitWarning =
    activeCount > SOFT_LIMIT_ACTIVE || totalChars > SOFT_LIMIT_CHARS;

  if (loading) {
    return (
      <div className="p-8">
        <Text headingH2>System Prompts</Text>
        <Text text03 className="p-4">
          Loading...
        </Text>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl">
      <Text headingH2>System Prompts</Text>
      <Text text03 className="pb-4">
        Global system prompt instructions that are prepended to every LLM call,
        regardless of the selected agent/persona.
      </Text>

      {message && (
        <div
          className={`p-3 rounded-08 mb-4 ${
            message.type === "success"
              ? "bg-status-success-01 text-status-success-03"
              : message.type === "warning"
                ? "bg-status-warning-01 text-status-warning-03"
                : "bg-status-error-01 text-status-error-03"
          }`}
        >
          <Text>{message.text}</Text>
        </div>
      )}

      {showLimitWarning && (
        <div className="p-3 rounded-08 mb-4 bg-status-warning-01 text-status-warning-03">
          <Text>
            Warning: {activeCount} active prompts ({totalChars.toLocaleString()}{" "}
            chars). Recommended limit: {SOFT_LIMIT_ACTIVE} prompts /{" "}
            {SOFT_LIMIT_CHARS.toLocaleString()} chars.
          </Text>
        </div>
      )}

      {/* Action bar */}
      <div className="flex gap-2 pb-4">
        <Button
          main
          primary={view !== "list"}
          onClick={() => {
            setView("list");
            resetForm();
          }}
        >
          Prompts
        </Button>
        <Button main primary={false} onClick={openCreate}>
          + New Prompt
        </Button>
        <Button
          main
          primary={false}
          onClick={() => {
            fetchPreview();
            setView("preview");
          }}
        >
          Preview
        </Button>
      </div>

      {/* Views */}
      {view === "list" && (
        <PromptList
          prompts={prompts}
          onEdit={openEdit}
          onToggle={handleToggle}
          onDelete={handleDelete}
        />
      )}

      {view === "edit" && (
        <PromptForm
          editing={!!editingPrompt}
          formName={formName}
          setFormName={setFormName}
          formText={formText}
          setFormText={setFormText}
          formCategory={formCategory}
          setFormCategory={setFormCategory}
          formPriority={formPriority}
          setFormPriority={setFormPriority}
          formActive={formActive}
          setFormActive={setFormActive}
          saving={saving}
          onSave={handleSave}
          onCancel={() => {
            setView("list");
            resetForm();
          }}
        />
      )}

      {view === "preview" && <PromptPreviewView preview={preview} />}
    </div>
  );
}

// --- List View ---

interface PromptListProps {
  prompts: CustomPrompt[];
  onEdit: (p: CustomPrompt) => void;
  onToggle: (p: CustomPrompt) => void;
  onDelete: (p: CustomPrompt) => void;
}

function PromptList({ prompts, onEdit, onToggle, onDelete }: PromptListProps) {
  if (prompts.length === 0) {
    return (
      <div className="p-6 bg-background-neutral-01 border border-border-02 rounded-08 text-center">
        <Text text03>No system prompts configured yet.</Text>
        <Text text03 className="pt-2">
          Create your first prompt to add global instructions to every LLM call.
        </Text>
      </div>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border-02">
          <th className="text-left p-2">
            <Text text03>Priority</Text>
          </th>
          <th className="text-left p-2">
            <Text text03>Name</Text>
          </th>
          <th className="text-left p-2">
            <Text text03>Category</Text>
          </th>
          <th className="text-center p-2">
            <Text text03>Status</Text>
          </th>
          <th className="text-right p-2">
            <Text text03>Chars</Text>
          </th>
          <th className="text-center p-2">
            <Text text03>Actions</Text>
          </th>
        </tr>
      </thead>
      <tbody>
        {prompts.map((p) => (
          <tr key={p.id} className="border-b border-border-01">
            <td className="p-2">
              <Text>{p.priority}</Text>
            </td>
            <td className="p-2">
              <Text>{p.name}</Text>
            </td>
            <td className="p-2">
              <CategoryBadge category={p.category} />
            </td>
            <td className="text-center p-2">
              <span
                className={`inline-block px-2 py-0.5 rounded-08 text-xs ${
                  p.is_active
                    ? "bg-status-success-01 text-status-success-03"
                    : "bg-background-neutral-02 text-text-03"
                }`}
              >
                {p.is_active ? "Active" : "Inactive"}
              </span>
            </td>
            <td className="text-right p-2">
              <Text>{p.prompt_text.length.toLocaleString()}</Text>
            </td>
            <td className="text-center p-2">
              <div className="flex gap-2 justify-center">
                <button
                  onClick={() => onEdit(p)}
                  className="text-xs font-medium text-text-02 hover:text-text-01 underline"
                >
                  Bearbeiten
                </button>
                <button
                  onClick={() => onToggle(p)}
                  className="text-xs font-medium text-text-02 hover:text-text-01 underline"
                >
                  {p.is_active ? "Deaktivieren" : "Aktivieren"}
                </button>
                <button
                  onClick={() => onDelete(p)}
                  className="text-xs font-medium text-status-error-03 hover:text-status-error-02 underline"
                >
                  Löschen
                </button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// --- Edit Form ---

interface PromptFormProps {
  editing: boolean;
  formName: string;
  setFormName: (v: string) => void;
  formText: string;
  setFormText: (v: string) => void;
  formCategory: string;
  setFormCategory: (v: string) => void;
  formPriority: string;
  setFormPriority: (v: string) => void;
  formActive: boolean;
  setFormActive: (v: boolean) => void;
  saving: boolean;
  onSave: () => void;
  onCancel: () => void;
}

function PromptForm({
  editing,
  formName,
  setFormName,
  formText,
  setFormText,
  formCategory,
  setFormCategory,
  formPriority,
  setFormPriority,
  formActive,
  setFormActive,
  saving,
  onSave,
  onCancel,
}: PromptFormProps) {
  return (
    <div className="bg-background-neutral-01 border border-border-02 rounded-08 p-6">
      <Text mainUiAction className="pb-4">
        {editing ? "Edit Prompt" : "New Prompt"}
      </Text>

      <div className="space-y-4">
        {/* Name */}
        <div>
          <Text text03 className="pb-1 text-xs">
            Name (max 100 chars)
          </Text>
          <InputTypeIn
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            placeholder="e.g., Compliance-Grundregeln"
          />
        </div>

        {/* Category + Priority row */}
        <div className="flex gap-4">
          <div className="flex-1">
            <Text text03 className="pb-1 text-xs">
              Category
            </Text>
            <select
              value={formCategory}
              onChange={(e) => setFormCategory(e.target.value)}
              className="w-full rounded-08 border border-border-02 bg-background-neutral-01 px-3 py-2 text-sm text-text-01"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="w-32">
            <Text text03 className="pb-1 text-xs">
              Priority (0-1000)
            </Text>
            <InputTypeIn
              value={formPriority}
              onChange={(e) => setFormPriority(e.target.value)}
              placeholder="100"
            />
          </div>
        </div>

        {/* Prompt text */}
        <div>
          <Text text03 className="pb-1 text-xs">
            Prompt Text (max 10,000 chars)
          </Text>
          <InputTextArea
            value={formText}
            onChange={(e) => setFormText(e.target.value)}
            placeholder="Enter the system prompt instructions..."
            className="min-h-[200px]"
          />
          <Text text03 className="pt-1 text-xs">
            {formText.length.toLocaleString()} / 10,000 chars
          </Text>
        </div>

        {/* Active toggle */}
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={formActive}
            onChange={(e) => setFormActive(e.target.checked)}
            className="rounded"
          />
          <Text>Active</Text>
        </label>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <Button main primary onClick={onSave} disabled={saving}>
            {saving ? "Saving..." : editing ? "Update" : "Create"}
          </Button>
          <Button main primary={false} onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

// --- Preview View ---

interface PromptPreviewViewProps {
  preview: PromptPreview | null;
}

function PromptPreviewView({ preview }: PromptPreviewViewProps) {
  if (!preview) {
    return (
      <Text text03 className="p-4">
        Unable to load preview.
      </Text>
    );
  }

  return (
    <div>
      <div className="flex gap-4 pb-4">
        <div className="bg-background-neutral-01 border border-border-02 rounded-08 p-3">
          <Text text03 className="text-xs">
            Active Prompts
          </Text>
          <Text headingH3>
            {preview.active_count} / {preview.total_count}
          </Text>
        </div>
        <div className="bg-background-neutral-01 border border-border-02 rounded-08 p-3">
          <Text text03 className="text-xs">
            Total Characters
          </Text>
          <Text headingH3>
            {preview.assembled_text.length.toLocaleString()}
          </Text>
        </div>
      </div>

      <Text mainUiAction className="pb-2">
        Assembled Prompt (sent before every LLM call)
      </Text>

      {preview.assembled_text ? (
        <pre className="bg-background-neutral-02 border border-border-01 rounded-08 p-4 text-sm whitespace-pre-wrap text-text-02 overflow-auto max-h-[500px]">
          {preview.assembled_text}
        </pre>
      ) : (
        <div className="p-6 bg-background-neutral-01 border border-border-02 rounded-08 text-center">
          <Text text03>No active prompts. The LLM receives only the standard Onyx system prompt.</Text>
        </div>
      )}
    </div>
  );
}

// --- Category Badge ---

interface CategoryBadgeProps {
  category: string;
}

function CategoryBadge({ category }: CategoryBadgeProps) {
  const label = CATEGORIES.find((c) => c.value === category)?.label || category;
  return (
    <span className="inline-block px-2 py-0.5 rounded-08 text-xs bg-background-tint-02 text-text-02">
      {label}
    </span>
  );
}
