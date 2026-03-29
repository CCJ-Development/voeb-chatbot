"use client";

import { useState, useEffect, useCallback } from "react";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";

// --- Types ---

interface UsageByUser {
  user_id: string;
  user_email: string | null;
  total_tokens: number;
  total_requests: number;
}

interface UsageByModel {
  model_name: string;
  total_tokens: number;
  total_requests: number;
}

interface UsageSummary {
  period_hours: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
  by_user: UsageByUser[];
  by_model: UsageByModel[];
}

interface TimeseriesBucket {
  timestamp: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
}

interface UsageTimeseries {
  granularity: string;
  data: TimeseriesBucket[];
}

interface UserLimit {
  id: number;
  user_id: string;
  user_email: string | null;
  token_budget: number;
  period_hours: number;
  enabled: boolean;
  current_usage: number;
}

interface SystemUser {
  id: string;
  email: string;
}

type TabKey = "overview" | "timeseries" | "users" | "limits";

// --- Helper ---

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

// --- Component ---

export default function ExtTokenAdminPage() {
  const [tab, setTab] = useState<TabKey>("overview");
  const [periodHours, setPeriodHours] = useState(168);
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [timeseries, setTimeseries] = useState<UsageTimeseries | null>(null);
  const [limits, setLimits] = useState<UserLimit[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // New limit form
  const [newUserId, setNewUserId] = useState("");
  const [newBudget, setNewBudget] = useState("");
  const [newPeriod, setNewPeriod] = useState("168");
  const [allUsers, setAllUsers] = useState<SystemUser[]>([]);

  const fetchUsers = useCallback(async () => {
    try {
      const res = await fetch("/api/manage/users");
      if (res.ok) {
        const data = await res.json();
        setAllUsers(
          (data.accepted || []).map((u: { id: string; email: string }) => ({
            id: u.id,
            email: u.email,
          }))
        );
      }
    } catch {
      /* ignore */
    }
  }, []);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/ext/token/usage/summary?period_hours=${periodHours}`
      );
      if (res.ok) setSummary(await res.json());
    } catch {
      /* ignore */
    }
  }, [periodHours]);

  const fetchTimeseries = useCallback(async () => {
    const gran = periodHours <= 48 ? "hour" : "day";
    try {
      const res = await fetch(
        `/api/ext/token/usage/timeseries?period_hours=${periodHours}&granularity=${gran}`
      );
      if (res.ok) setTimeseries(await res.json());
    } catch {
      /* ignore */
    }
  }, [periodHours]);

  const fetchLimits = useCallback(async () => {
    try {
      const res = await fetch("/api/ext/token/limits/users");
      if (res.ok) setLimits(await res.json());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchSummary(), fetchTimeseries(), fetchLimits(), fetchUsers()]).finally(() =>
      setLoading(false)
    );
  }, [fetchSummary, fetchTimeseries, fetchLimits, fetchUsers]);

  const handleCreateLimit = async () => {
    setMessage(null);
    if (!newUserId || !newBudget || !newPeriod) {
      setMessage({ type: "error", text: "Alle Felder sind erforderlich" });
      return;
    }
    try {
      const res = await fetch("/api/ext/token/limits/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: newUserId,
          token_budget: parseInt(newBudget, 10),
          period_hours: parseInt(newPeriod, 10),
          enabled: true,
        }),
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Limit erstellt" });
        setNewUserId("");
        setNewBudget("");
        setNewPeriod("168");
        fetchLimits();
      } else {
        const err = await res.json();
        setMessage({ type: "error", text: err.detail || "Fehlgeschlagen" });
      }
    } catch {
      setMessage({ type: "error", text: "Netzwerkfehler" });
    }
  };

  const handleToggleLimit = async (limit: UserLimit) => {
    try {
      await fetch(`/api/ext/token/limits/users/${limit.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token_budget: limit.token_budget,
          period_hours: limit.period_hours,
          enabled: !limit.enabled,
        }),
      });
      fetchLimits();
    } catch {
      /* ignore */
    }
  };

  const handleDeleteLimit = async (limitId: number) => {
    try {
      await fetch(`/api/ext/token/limits/users/${limitId}`, {
        method: "DELETE",
      });
      fetchLimits();
    } catch {
      /* ignore */
    }
  };

  const tabs: { key: TabKey; label: string }[] = [
    { key: "overview", label: "Übersicht" },
    { key: "timeseries", label: "Zeitverlauf" },
    { key: "users", label: "Pro Benutzer" },
    { key: "limits", label: "Benutzer-Limits" },
  ];

  if (loading) {
    return (
      <div className="p-8">
        <Text headingH2 className="block">Token-Verbrauch</Text>
        <Text text03 className="block p-4">Laden...</Text>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl">
      <Text headingH2 className="block pb-1">Token-Verbrauch</Text>
      <Text text03 className="block pb-4">LLM-Token-Verbrauch und Benutzer-Limits.</Text>

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

      {/* Period selector */}
      <div className="flex items-center gap-3 pb-4">
        <Text text03>Zeitraum:</Text>
        {[24, 168, 720].map((h) => (
          <button
            key={h}
            onClick={() => setPeriodHours(h)}
            className={`px-3 py-1 rounded-08 text-sm ${
              periodHours === h
                ? "bg-background-neutral-inverted-00 text-text-inverted-05"
                : "bg-background-neutral-02 text-text-02"
            }`}
          >
            {h === 24 ? "24h" : h === 168 ? "7 Tage" : "30 Tage"}
          </button>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border-02 mb-4">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm ${
              tab === t.key
                ? "text-text-05 border-b-2 border-b-text-05"
                : "text-text-03"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && summary && <OverviewTab summary={summary} />}
      {tab === "timeseries" && timeseries && (
        <TimeseriesTab timeseries={timeseries} />
      )}
      {tab === "users" && summary && <UsersTab summary={summary} />}
      {tab === "limits" && (
        <LimitsTab
          limits={limits}
          allUsers={allUsers}
          newUserId={newUserId}
          setNewUserId={setNewUserId}
          newBudget={newBudget}
          setNewBudget={setNewBudget}
          newPeriod={newPeriod}
          setNewPeriod={setNewPeriod}
          onCreateLimit={handleCreateLimit}
          onToggleLimit={handleToggleLimit}
          onDeleteLimit={handleDeleteLimit}
        />
      )}
    </div>
  );
}

// --- Tab: Overview ---

interface OverviewTabProps {
  summary: UsageSummary;
}

function OverviewTab({ summary }: OverviewTabProps) {
  return (
    <div>
      {/* Stats cards */}
      <div className="grid grid-cols-2 gap-4 pb-6">
        <StatCard label="Tokens gesamt" value={formatTokens(summary.total_tokens)} />
        <StatCard label="Anfragen" value={String(summary.total_requests)} />
        <StatCard
          label="Prompt-Tokens"
          value={formatTokens(summary.total_prompt_tokens)}
        />
        <StatCard
          label="Completion-Tokens"
          value={formatTokens(summary.total_completion_tokens)}
        />
      </div>

      {/* By model */}
      <Text mainUiAction className="block pb-2">Nach Modell</Text>
      <table className="w-full text-sm mb-6">
        <thead>
          <tr className="border-b border-border-02">
            <th className="text-left p-2">
              <Text text03>Modell</Text>
            </th>
            <th className="text-right p-2">
              <Text text03>Tokens</Text>
            </th>
            <th className="text-right p-2">
              <Text text03>Anfragen</Text>
            </th>
          </tr>
        </thead>
        <tbody>
          {summary.by_model.map((m) => (
            <tr key={m.model_name} className="border-b border-border-01">
              <td className="p-2">
                <Text>{m.model_name}</Text>
              </td>
              <td className="text-right p-2">
                <Text>{formatTokens(m.total_tokens)}</Text>
              </td>
              <td className="text-right p-2">
                <Text>{m.total_requests}</Text>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Tab: Timeseries ---

interface TimeseriesTabProps {
  timeseries: UsageTimeseries;
}

function TimeseriesTab({ timeseries }: TimeseriesTabProps) {
  if (timeseries.data.length === 0) {
    return (
      <Text text03 className="block p-4">Keine Daten für diesen Zeitraum.</Text>
    );
  }

  const maxTokens = Math.max(...timeseries.data.map((d) => d.total_tokens), 1);

  return (
    <div>
      <Text mainUiAction className="block pb-2">Token-Verbrauch im Zeitverlauf ({timeseries.granularity})</Text>
      <div className="space-y-1">
        {timeseries.data.map((bucket) => {
          const pct = (bucket.total_tokens / maxTokens) * 100;
          const label =
            timeseries.granularity === "hour"
              ? new Date(bucket.timestamp).toLocaleString([], {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : new Date(bucket.timestamp).toLocaleDateString([], {
                  month: "short",
                  day: "numeric",
                });
          return (
            <div key={bucket.timestamp} className="flex items-center gap-2">
              <Text text03 className="w-32 text-right text-xs shrink-0">
                {label}
              </Text>
              <div className="flex-1 bg-background-neutral-02 rounded-08 h-5">
                <div
                  className="bg-theme-primary-05 rounded-08 h-5"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <Text className="w-16 text-right text-xs shrink-0">
                {formatTokens(bucket.total_tokens)}
              </Text>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- Tab: Per-User ---

interface UsersTabProps {
  summary: UsageSummary;
}

function UsersTab({ summary }: UsersTabProps) {
  return (
    <div>
      <Text mainUiAction className="block pb-2">Aufschlüsselung pro Benutzer</Text>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border-02">
            <th className="text-left p-2">
              <Text text03>Benutzer</Text>
            </th>
            <th className="text-right p-2">
              <Text text03>Tokens</Text>
            </th>
            <th className="text-right p-2">
              <Text text03>Anfragen</Text>
            </th>
            <th className="text-right p-2">
              <Text text03>Anteil</Text>
            </th>
          </tr>
        </thead>
        <tbody>
          {summary.by_user.map((u) => (
            <tr key={u.user_id} className="border-b border-border-01">
              <td className="p-2">
                <Text>{u.user_email || u.user_id.slice(0, 8)}</Text>
              </td>
              <td className="text-right p-2">
                <Text>{formatTokens(u.total_tokens)}</Text>
              </td>
              <td className="text-right p-2">
                <Text>{u.total_requests}</Text>
              </td>
              <td className="text-right p-2">
                <Text>
                  {summary.total_tokens > 0
                    ? `${((u.total_tokens / summary.total_tokens) * 100).toFixed(1)}%`
                    : "0%"}
                </Text>
              </td>
            </tr>
          ))}
          {summary.by_user.length === 0 && (
            <tr>
              <td colSpan={4} className="p-4 text-center">
                <Text text03 className="block">Keine Benutzerdaten für diesen Zeitraum.</Text>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// --- Tab: User Limits ---

interface LimitsTabProps {
  limits: UserLimit[];
  allUsers: SystemUser[];
  newUserId: string;
  setNewUserId: (v: string) => void;
  newBudget: string;
  setNewBudget: (v: string) => void;
  newPeriod: string;
  setNewPeriod: (v: string) => void;
  onCreateLimit: () => void;
  onToggleLimit: (limit: UserLimit) => void;
  onDeleteLimit: (limitId: number) => void;
}

function LimitsTab({
  limits,
  allUsers,
  newUserId,
  setNewUserId,
  newBudget,
  setNewBudget,
  newPeriod,
  setNewPeriod,
  onCreateLimit,
  onToggleLimit,
  onDeleteLimit,
}: LimitsTabProps) {
  // Filter out users that already have a limit
  const existingUserIds = new Set(limits.map((l) => l.user_id));
  const availableUsers = allUsers.filter((u) => !existingUserIds.has(u.id));
  return (
    <div>
      {/* Existing limits */}
      <Text mainUiAction className="block pb-2">Konfigurierte Benutzer-Limits</Text>
      <Text text03 className="block pb-3">Budget in Tausend Token (z.B. 500 = 500.000 Token).</Text>

      {limits.length > 0 ? (
        <table className="w-full text-sm mb-6">
          <thead>
            <tr className="border-b border-border-02">
              <th className="text-left p-2">
                <Text text03>Benutzer</Text>
              </th>
              <th className="text-right p-2">
                <Text text03>Budget (k)</Text>
              </th>
              <th className="text-right p-2">
                <Text text03>Zeitraum</Text>
              </th>
              <th className="text-right p-2">
                <Text text03>Verbrauch</Text>
              </th>
              <th className="text-center p-2">
                <Text text03>Status</Text>
              </th>
              <th className="text-center p-2">
                <Text text03>Aktionen</Text>
              </th>
            </tr>
          </thead>
          <tbody>
            {limits.map((lim) => {
              const budgetTokens = lim.token_budget * 1000;
              const pct =
                budgetTokens > 0
                  ? Math.min((lim.current_usage / budgetTokens) * 100, 100)
                  : 0;
              return (
                <tr key={lim.id} className="border-b border-border-01">
                  <td className="p-2">
                    <Text>{lim.user_email || lim.user_id.slice(0, 8)}</Text>
                  </td>
                  <td className="text-right p-2">
                    <Text>{lim.token_budget}</Text>
                  </td>
                  <td className="text-right p-2">
                    <Text>{lim.period_hours}h</Text>
                  </td>
                  <td className="text-right p-2">
                    <Text>
                      {formatTokens(lim.current_usage)} ({pct.toFixed(0)}%)
                    </Text>
                  </td>
                  <td className="text-center p-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-08 text-xs ${
                        lim.enabled
                          ? "bg-status-success-01 text-status-success-03"
                          : "bg-background-neutral-02 text-text-03"
                      }`}
                    >
                      {lim.enabled ? "Aktiv" : "Deaktiviert"}
                    </span>
                  </td>
                  <td className="text-center p-2">
                    <div className="flex gap-2 justify-center">
                      <button
                        onClick={() => onToggleLimit(lim)}
                        className="text-xs text-action-link-01 underline"
                      >
                        {lim.enabled ? "Deaktivieren" : "Aktivieren"}
                      </button>
                      <button
                        onClick={() => onDeleteLimit(lim.id)}
                        className="text-xs text-action-danger-01 underline"
                      >
                        Löschen
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <Text text03 className="block pb-6">Keine Benutzer-Limits konfiguriert.</Text>
      )}

      {/* Create new limit */}
      <Text mainUiAction className="block pb-2">Benutzer-Limit hinzufügen</Text>
      <div className="flex gap-3 items-end flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <Text text03 className="block pb-1 text-xs">Benutzer</Text>
          <select
            value={newUserId}
            onChange={(e) => setNewUserId(e.target.value)}
            className="w-full rounded-08 border border-border-02 bg-background-neutral-01 px-3 py-2 text-sm text-text-01"
          >
            <option value="">Benutzer auswählen...</option>
            {availableUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.email}
              </option>
            ))}
          </select>
        </div>
        <div className="w-28">
          <Text text03 className="block pb-1 text-xs">Budget (k Token)</Text>
          <InputTypeIn
            value={newBudget}
            onChange={(e) => setNewBudget(e.target.value)}
            placeholder="500"
          />
        </div>
        <div className="w-28">
          <Text text03 className="block pb-1 text-xs">Zeitraum (Stunden)</Text>
          <InputTypeIn
            value={newPeriod}
            onChange={(e) => setNewPeriod(e.target.value)}
            placeholder="168"
          />
        </div>
        <Button main primary onClick={onCreateLimit}>
          Limit hinzufügen
        </Button>
      </div>
    </div>
  );
}

// --- Stat Card ---

interface StatCardProps {
  label: string;
  value: string;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="bg-background-neutral-01 border border-border-02 rounded-08 p-4">
      <Text text03 className="block pb-1 text-xs">{label}</Text>
      <Text headingH3 className="block">{value}</Text>
    </div>
  );
}
