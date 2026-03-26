# ext-analytics — Plattform-Nutzungsanalysen + Compliance-KPIs

**Status:** Implementiert (2026-03-26)
**Feature Flag:** `EXT_ANALYTICS_ENABLED` (existiert in config.py)
**Scope:** Grafana Dashboard (SQL auf Onyx-Tabellen) + API-Endpoints mit CSV-Export
**Keine Core-Patches noetig.** Reine SELECT-Queries auf bestehende Tabellen.

---

## 1. Uebersicht KPIs

### 1.1 Nutzung

| KPI | Metrik | SQL-Quelle | Granularitaet |
|-----|--------|------------|---------------|
| Aktive User (DAU) | `COUNT(DISTINCT user_id) FROM chat_session WHERE DATE(time_created) = ?` | `chat_session` | Tag |
| Aktive User (WAU) | `COUNT(DISTINCT user_id) FROM chat_session WHERE time_created >= now() - interval '7 days'` | `chat_session` | Woche |
| Aktive User (MAU) | `COUNT(DISTINCT user_id) FROM chat_session WHERE time_created >= now() - interval '30 days'` | `chat_session` | Monat |
| Sessions gesamt | `COUNT(*) FROM chat_session WHERE NOT deleted` | `chat_session` | Zeitraum |
| Sessions pro User | `COUNT(*) ... GROUP BY user_id` | `chat_session` | Zeitraum |
| Nachrichten pro Session | `COUNT(*) FROM chat_message WHERE message_type IN ('USER','ASSISTANT') GROUP BY chat_session_id` | `chat_message` | Zeitraum |
| Session-Dauer | `AVG(EXTRACT(EPOCH FROM (time_updated - time_created)))` | `chat_session` | Zeitraum |
| Peak-Zeiten (Stunde) | `COUNT(*) FROM chat_message GROUP BY EXTRACT(HOUR FROM time_sent)` | `chat_message` | Stunde |
| Antwortzeit (Median) | `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY processing_duration_seconds)` | `chat_message` WHERE `message_type = 'ASSISTANT'` | Zeitraum |
| Antwortzeit (P95) | `PERCENTILE_CONT(0.95) ...` | `chat_message` WHERE `message_type = 'ASSISTANT'` | Zeitraum |

### 1.2 Agenten/Personas

| KPI | Metrik | SQL-Quelle | Granularitaet |
|-----|--------|------------|---------------|
| Nutzung pro Agent | `COUNT(*) FROM chat_session GROUP BY persona_id` JOIN `persona.name` | `chat_session` + `persona` | Zeitraum |
| Top-Agenten | ORDER BY count DESC LIMIT 10 | `chat_session` + `persona` | Zeitraum |
| Nachrichten pro Agent | `COUNT(*) FROM chat_message JOIN chat_session ON ... GROUP BY persona_id` | `chat_message` + `chat_session` + `persona` | Zeitraum |
| Ungenutzte Agenten | `persona.id NOT IN (SELECT DISTINCT persona_id FROM chat_session WHERE ...)` | `persona` + `chat_session` | Zeitraum |

### 1.3 Token/Kosten

| KPI | Metrik | SQL-Quelle | Granularitaet |
|-----|--------|------------|---------------|
| Token-Verbrauch gesamt | `SUM(total_tokens)` | `ext_token_usage` | Zeitraum |
| Token pro User | `SUM(total_tokens) GROUP BY user_id` WHERE `user_id IS NOT NULL` | `ext_token_usage` | Zeitraum |
| Token pro Modell | `SUM(total_tokens) GROUP BY model_name` | `ext_token_usage` | Zeitraum |
| Modell-Verteilung (%) | `SUM(total_tokens) GROUP BY model_name / SUM(total_tokens)` | `ext_token_usage` | Zeitraum |
| Token-Trend | Timeseries `date_trunc('day', created_at)` | `ext_token_usage` | Tag |
| Prompt vs Completion Ratio | `SUM(prompt_tokens) / SUM(completion_tokens)` | `ext_token_usage` | Zeitraum |
| Requests gesamt | `COUNT(*)` | `ext_token_usage` | Zeitraum |

### 1.4 Qualitaet

| KPI | Metrik | SQL-Quelle | Granularitaet |
|-----|--------|------------|---------------|
| Feedback-Rate | `COUNT(chat_feedback) / COUNT(chat_message WHERE message_type='ASSISTANT')` | `chat_feedback` + `chat_message` | Zeitraum |
| Zufriedenheit (%) | `COUNT(WHERE is_positive=true) / COUNT(*)` | `chat_feedback` | Zeitraum |
| Negatives Feedback | `COUNT(WHERE is_positive=false)` | `chat_feedback` | Zeitraum |
| Fehlerrate | `COUNT(WHERE error IS NOT NULL) / COUNT(WHERE message_type='ASSISTANT')` | `chat_message` | Zeitraum |
| Fehler-Trend | Timeseries errors per day | `chat_message` | Tag |

### 1.5 Content/RAG

| KPI | Metrik | SQL-Quelle | Granularitaet |
|-----|--------|------------|---------------|
| Indexierte Dokumente | `SUM(total_docs_indexed)` | `connector_credential_pair` | Snapshot |
| Aktive Connectors | `COUNT(WHERE status='ACTIVE')` | `connector_credential_pair` | Snapshot |
| Fehlerhafte Connectors | `COUNT(WHERE status!='ACTIVE' OR in_repeated_error_state=true)` | `connector_credential_pair` | Snapshot |
| Document Sets | `COUNT(*)` | `document_set` | Snapshot |

**Entfernt:** Citations pro Antwort — `chat_message.citations` ist auf DEV/PROD nur jsonb `null`, nicht auswertbar.

### 1.6 Compliance/Adoption

| KPI | Metrik | SQL-Quelle | Granularitaet |
|-----|--------|------------|---------------|
| Admin-Aktionen | `COUNT(*) FROM ext_audit_log` | `ext_audit_log` | Zeitraum |
| Aktionen nach Typ | `COUNT(*) GROUP BY action` | `ext_audit_log` | Zeitraum |
| Registrierte User gesamt | `COUNT(*) FROM "user"` | `user` | Snapshot |
| Neue User pro Zeitraum | `COUNT(*) WHERE created_at BETWEEN ...` | `user` | Zeitraum |
| Inaktive User | User ohne `chat_session` seit 30 Tagen | `user` + `chat_session` | Snapshot |

---

## 2. Architektur

### 2.1 Grafana Dashboard

**Voraussetzung (erledigt 2026-03-26):**
- PostgreSQL Datasource in Grafana konfiguriert (ConfigMap `grafana-datasource-postgresql`)
- `db_readonly_user` mit SELECT-Grants auf alle Tabellen (DEV + PROD)
- NetworkPolicy `14-allow-grafana-pg-egress.yaml` (Grafana → PG:5432)

**Dashboard:** `analytics-overview.json` — 19 Data-Panels in 7 Rows

| Row | Panel | Typ | KPIs |
|-----|-------|-----|------|
| 1 | Uebersicht | 4x Stat | Registrierte User, MAU, Sessions heute, Token heute |
| 2 | Nutzungstrends | 2x Timeseries | DAU pro Tag, Sessions pro Tag |
| 3 | Muster + Agenten | 2x Bar Chart | Nachrichten pro Stunde, Top Agenten |
| 4 | Token + Kosten | Pie + Timeseries | Token pro Modell, Token Trend (stacked) |
| 5 | Antwortzeit + Feedback | Timeseries + 2x Stat | Median/P95, Zufriedenheit %, Feedback Anzahl |
| 6 | Fehler + Content | Timeseries + 3x Stat | Fehlerrate, Indexierte Docs, Connectors, Nachrichten/Session |
| 7 | Compliance + User | 2x Table | Admin-Aktionen (ext_audit_log), User-Aktivitaet |

### 2.2 API-Endpoints + CSV-Export

**Router:** `/ext/analytics` (hinter `EXT_ANALYTICS_ENABLED`)

| Methode | Pfad | Beschreibung | Parameter |
|---------|------|-------------|-----------|
| GET | `/ext/analytics/summary` | Alle KPIs als JSON | `from_date`, `to_date` (Default: 30d) |
| GET | `/ext/analytics/users` | User-Tabelle mit Aktivitaetsmetriken | `from_date`, `to_date` |
| GET | `/ext/analytics/agents` | Agent-Nutzungsstatistiken | `from_date`, `to_date` |
| GET | `/ext/analytics/export` | CSV-Export aller KPIs + User-Tabelle | `from_date`, `to_date` (max 365d) |

### 2.3 Dateien

```
backend/ext/
  schemas/analytics.py       — 8 Pydantic Response Models
  services/analytics.py      — 7 KPI-Kategorien (raw SQL via text()), CSV-Export
  routers/analytics.py       — 4 FastAPI Endpoints (admin-only)
  tests/test_analytics.py    — 9 Unit Tests

deployment/k8s/monitoring-exporters/
  grafana-dashboards/analytics-overview.json    — Dashboard (19 Panels)
  grafana-datasource-postgresql.yaml            — PG-Datasource Template

deployment/k8s/network-policies/monitoring/
  14-allow-grafana-pg-egress.yaml               — Grafana → PG Egress
```

---

## 3. DB-Abhaengigkeiten

### Onyx-Tabellen (SELECT only)

| Tabelle | Genutzte Spalten |
|---------|-----------------|
| `user` | `id`, `email`, `role`, `is_active`, `created_at` |
| `chat_session` | `id`, `user_id`, `persona_id`, `time_created`, `time_updated`, `deleted` |
| `chat_message` | `id`, `chat_session_id`, `message_type` (**UPPERCASE: 'ASSISTANT', 'USER', 'SYSTEM'**), `token_count`, `time_sent`, `processing_duration_seconds`, `error` |
| `persona` | `id`, `name`, `is_visible`, `deleted` |
| `chat_feedback` | `id`, `chat_message_id`, `is_positive` (**kein created_at — Zeitfilter via JOIN chat_message.time_sent**) |
| `connector_credential_pair` | `status`, `total_docs_indexed`, `in_repeated_error_state` |
| `document_set` | `id` |

### Ext-Tabellen (SELECT only)

| Tabelle | Genutzte Spalten |
|---------|-----------------|
| `ext_token_usage` | `user_id` (**53% NULL bei System-Calls**), `model_name`, `total_tokens`, `prompt_tokens`, `completion_tokens`, `created_at` |
| `ext_audit_log` | `actor_email`, `action`, `resource_type`, **`timestamp`** (nicht created_at) |

### Keine neuen Tabellen

Kein Alembic-Migration noetig. Alle KPIs aus bestehenden Daten ableitbar.

---

## 4. Infrastruktur

### db_readonly_user
- Erstellt per Terraform (`deployment/terraform/modules/stackit/main.tf:111-116`)
- SELECT-Grants erteilt: 2026-03-26 (DEV + PROD)
- `ALTER DEFAULT PRIVILEGES` gesetzt fuer zukuenftige Tabellen

### Grafana PG-Datasource
- ConfigMap `grafana-datasource-postgresql` in monitoring-NS (DEV + PROD)
- Sidecar-Provisioning (Label `grafana_datasource: "1"`)
- **Nicht in Git** (enthaelt Credentials) — Template in `grafana-datasource-postgresql.yaml`

### NetworkPolicy
- `14-allow-grafana-pg-egress.yaml`: Grafana Pods → PG:5432 Egress
- Analog zu `06-allow-pg-exporter-egress.yaml` (Least Privilege, podSelector auf Grafana)

---

## 5. Entscheidungen (aus Tiefenanalyse 2026-03-26)

| Entscheidung | Begruendung |
|-------------|-------------|
| `message_type = 'ASSISTANT'` (UPPERCASE) | DB speichert Enum-Werte uppercase, nicht lowercase wie in Onyx-Docs |
| KPI "Citations pro Antwort" entfernt | `chat_message.citations` enthaelt nur jsonb `null` — kein verwertbares Datenfeld |
| `chat_feedback` Zeitfilter via JOIN | Tabelle hat kein eigenes Timestamp-Feld, nur FK zu `chat_message` |
| `ext_token_usage.user_id` NULL-Filter | 53% der Eintraege sind System-Calls ohne User-Kontext — per-User Queries mit `WHERE user_id IS NOT NULL` |
| `loki-loki-stack` ConfigMap gepatcht | Doppeltes `isDefault: true` (Prometheus + Loki) verhinderte Grafana-Start — Loki auf `isDefault: false` gesetzt |
| Heatmap → Bar Chart | Grafana Heatmap-Panel mit SQL-Datasource komplex; Bar Chart "Nachrichten pro Stunde" ist lesbarer |

---

## 6. Offene Fragen (aus Spec)

1. ~~Zeitraum-Default~~ → **Entschieden:** Letzte 30 Tage (API Default)
2. **DSGVO:** User-Email in Analytics sichtbar fuer Admins — berechtigtes Interesse (Plattform-Administration). Nur Admin-Endpoints.
3. **Performance:** Bei >10k Sessions koennten Aggregate langsam werden → materialized Views (optional, nicht implementiert)
4. **Zugang Grafana:** Aktuell nur via `kubectl port-forward` (intern). VÖB-Admins nutzen API/CSV.
5. **Kosten-Zuordnung:** Nicht implementiert. Kann spaeter als separates Panel ergaenzt werden.
