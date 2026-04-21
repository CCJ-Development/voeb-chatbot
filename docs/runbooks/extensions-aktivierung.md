# Extensions aktivieren (9 ext-Module)

**Zielgruppe:** Tech Lead beim Kunden-Klon
**Dauer:** 1–2 h
**Phase:** teilweise 5 (Deploy) + 9 (Whitelabel) im [Master-Playbook](./kunden-klon-onboarding.md)

Dieses Runbook erklärt, welche ext-Module verfügbar sind, wie sie aktiviert werden und in welcher Reihenfolge. Alle Module sind per Feature-Flag schaltbar — bei `false` laufen sie nicht, bei `true` sind sie aktiv.

---

## Überblick aller 9 Module

| # | Modul | Zweck | Feature-Flag | Abhängigkeit |
|---|---|---|---|---|
| 4a | `ext-framework` | Basis (Router, Health, Config) | `EXT_ENABLED` | — |
| 4b | `ext-branding` | Whitelabel: Logo, App-Name, Consent | `EXT_BRANDING_ENABLED` (+ `NEXT_PUBLIC_EXT_BRANDING_ENABLED`) | 4a |
| 4c | `ext-token` | LLM-Usage-Tracking + Per-User-Limits | `EXT_TOKEN_LIMITS_ENABLED` | 4a |
| 4d | `ext-prompts` | Custom System Prompts (Compliance-Guidance) | `EXT_CUSTOM_PROMPTS_ENABLED` | 4a |
| 4e | `ext-analytics` | Nutzungsanalysen (Grafana + CSV-Export) | `EXT_ANALYTICS_ENABLED` | 4a, ext-token (optional) |
| 4f | `ext-rbac` | Gruppenverwaltung + Kurator-Rollen | `EXT_RBAC_ENABLED` (+ `NEXT_PUBLIC_EXT_RBAC_ENABLED`) | 4a |
| 4g | `ext-access` | Gruppenbasierte Dokument-ACL | `EXT_DOC_ACCESS_ENABLED` | 4a, ext-rbac |
| 4h | `ext-i18n` | Deutsche UI-Lokalisierung | `NEXT_PUBLIC_EXT_I18N_ENABLED` | — (Frontend-only) |
| 4i | `ext-audit` | Audit-Log (Admin-Aktionen, 90d Retention) | `EXT_AUDIT_ENABLED` | 4a |

**Modulspezifikationen:** `docs/technisches-feinkonzept/ext-<modul>.md` (pro Modul eine Datei mit Detailansicht)

---

## 1. Empfehlung „Standard-Kunden-Setup"

Für einen neuen Banking-nahen Kunden empfiehlt sich **volle Aktivierung** aller 9 Module, weil:
- **Compliance-Anforderungen:** Audit-Log (4i), Access-Control (4g), RBAC (4f) sind Banking-typisch
- **Kostenkontrolle:** Token-Limits (4c) verhindern unkontrollierte LLM-Kosten
- **Whitelabel:** Branding (4b) + i18n (4h) sind Standard-Erwartung
- **Transparenz:** Analytics (4e) für Management-Reports

Für **nicht-regulierte Kunden** können Module einzeln deaktiviert werden. Feature-Flags sind rückgängig machbar ohne Code-Änderungen.

---

## 2. Aktivierungs-Reihenfolge

Einige Module haben Abhängigkeiten. Die sichere Reihenfolge:

1. **4a ext-framework** (`EXT_ENABLED=true`) — Master-Switch. Ohne das laufen alle anderen nicht.
2. **4h ext-i18n** (Frontend-only, Build-Zeit) — UI-Sprache vor Branding
3. **4b ext-branding** — damit das erste Login gebrandet ist
4. **4f ext-rbac** — Voraussetzung für ext-access
5. **4g ext-access** — Dokument-ACL aktiviert sich nach RBAC
6. **4c ext-token** — LLM-Limits setzen, bevor User aktiv werden
7. **4d ext-prompts** — Optional, je nach Bedarf
8. **4e ext-analytics** — Optional, nach Token-Tracking
9. **4i ext-audit** — kann jederzeit aktiviert werden, aber Audit greift erst ab Aktivierung (historische Daten nicht retroaktiv)

---

## 3. Konfigurations-Ebenen

Jedes Modul braucht Änderungen an **mehreren Stellen** — übersehen heißt „Modul scheint nicht zu funktionieren":

### 3.1 Helm Values (`values-common.yaml`)

```yaml
configMap:
  # Backend Feature Flags
  EXT_ENABLED: "true"
  EXT_BRANDING_ENABLED: "true"
  EXT_TOKEN_LIMITS_ENABLED: "true"
  EXT_CUSTOM_PROMPTS_ENABLED: "true"
  EXT_ANALYTICS_ENABLED: "true"
  EXT_RBAC_ENABLED: "true"
  EXT_DOC_ACCESS_ENABLED: "true"
  EXT_AUDIT_ENABLED: "true"
  EXT_I18N_ENABLED: "true"

  # Frontend Build-Time Flags (lesen sich Next.js-seitig)
  NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED: "true"
```

### 3.2 Web-Dockerfile Build-Args (für Next.js Build-Time-Flags)

Alle `NEXT_PUBLIC_*`-Flags müssen als Build-Args definiert sein, sonst landen sie nicht im Client-Bundle:

```dockerfile
# web/Dockerfile (beide Stages: builder + runner)
ARG NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=true
ARG NEXT_PUBLIC_EXT_I18N_ENABLED=true
ARG NEXT_PUBLIC_EXT_RBAC_ENABLED=true
ARG NEXT_PUBLIC_EXT_BRANDING_ENABLED=true

ENV NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=${NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED}
ENV NEXT_PUBLIC_EXT_I18N_ENABLED=${NEXT_PUBLIC_EXT_I18N_ENABLED}
ENV NEXT_PUBLIC_EXT_RBAC_ENABLED=${NEXT_PUBLIC_EXT_RBAC_ENABLED}
ENV NEXT_PUBLIC_EXT_BRANDING_ENABLED=${NEXT_PUBLIC_EXT_BRANDING_ENABLED}
```

### 3.3 GitHub Workflow (`stackit-deploy.yml`)

Build-Args durchreichen:

```yaml
- name: Build & Push Frontend
  uses: docker/build-push-action@...
  with:
    context: ./web
    push: true
    build-args: |
      NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=true
      NEXT_PUBLIC_EXT_I18N_ENABLED=true
      NEXT_PUBLIC_EXT_RBAC_ENABLED=true
      NEXT_PUBLIC_EXT_BRANDING_ENABLED=true
```

### 3.4 Alembic-Migrationen (automatisch)

Beim ersten `helm upgrade` läuft Alembic und legt die ext-Tabellen an:

- `ext_branding_config`
- `ext_token_usage`, `ext_token_user_limit`
- `ext_custom_prompts`
- `ext_audit_log`

RBAC + Access nutzen Onyx-Tabellen, brauchen keine eigenen Migrationen.

Chain (nach Sync #5): `503883791c39` → `ff7273065d0d` (branding) → `b3e4a7d91f08` (token) → `c7f2e8a3d105` (prompts) → `d8a1b2c3e4f5` (audit)

---

## 4. Modul-spezifische Aktivierung

### 4a. ext-framework (Basis)

Nichts weiter zu tun außer `EXT_ENABLED=true`. Health-Endpoint `/api/ext/health/deep` testet nach Aktivierung DB + Redis + OpenSearch.

**Validierung:**
```bash
curl https://<DEV_DOMAIN>/api/ext/health/deep
# Erwartung: {"status": "ok", "checks": {"db": true, "redis": true, "opensearch": true}}
```

### 4b. ext-branding

Siehe dediziertes Runbook: [whitelabel-setup.md](./whitelabel-setup.md)

### 4c. ext-token

1. Flag `EXT_TOKEN_LIMITS_ENABLED=true` setzen
2. Nach Deploy: Admin-UI `/admin/ext/token-usage` erreichbar
3. Pro User: Token-Limit setzen (Default: unlimited, empfohlen: z. B. 100.000 Tokens/Tag)
4. Prometheus-Counter werden automatisch geliefert (pro Modell: prompt/completion/requests)

**Validierung:**
```bash
# Admin-UI erreichbar
curl -I https://<DEV_DOMAIN>/admin/ext/token-usage
# Erwartung: 200 (mit Auth-Cookie) oder 302 (ohne)

# Prometheus-Targets:
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
# Browser http://localhost:9090 → Query: ext_token_prompt_total
```

### 4d. ext-prompts

1. Flag `EXT_CUSTOM_PROMPTS_ENABLED=true`
2. Admin-UI: `/admin/ext/system-prompts`
3. System-Prompt anlegen, aktivieren
4. Wirkt sofort — wird vor jedem LLM-Call prepended

**Typischer Use-Case:** Compliance-Guidance („Nie Code-Auszug aus internen Daten zeigen ohne Vollhintergrund").

### 4e. ext-analytics

1. Flag `EXT_ANALYTICS_ENABLED=true`
2. Grafana PG-Datasource muss eingerichtet sein (siehe [monitoring-setup.md §7.3](./monitoring-setup.md))
3. Dashboard „Analytics Overview" importieren (liegt in `deployment/k8s/monitoring-exporters/grafana-dashboards/analytics-overview.json`)
4. 4 API-Endpoints verfügbar:
   - `GET /api/ext/analytics/summary`
   - `GET /api/ext/analytics/users`
   - `GET /api/ext/analytics/agents`
   - `GET /api/ext/analytics/export/csv`

Details: [ext-analytics-verwaltung.md](./ext-analytics-verwaltung.md)

### 4f. ext-rbac

1. Flags `EXT_RBAC_ENABLED=true` + `NEXT_PUBLIC_EXT_RBAC_ENABLED=true`
2. Frontend muss mit `NEXT_PUBLIC_EXT_RBAC_ENABLED=true` gebaut sein (Build-Arg!)
3. Admin-UI: `/admin/ext-groups` erreichbar
4. Erste Gruppe anlegen, User zuweisen, ggf. als Kurator markieren
5. Personas + DocumentSets können dann Gruppen zugewiesen werden

**Upstream-Kollision beachten:** Seit Sync #5 legt Onyx automatisch „Admin" und „Basic" Default-Groups an. Diese können je nach Kundenwunsch behalten oder gelöscht werden.

### 4g. ext-access

1. Voraussetzung: `ext-rbac` aktiviert und mindestens eine Gruppe existiert
2. Flag `EXT_DOC_ACCESS_ENABLED=true`
3. Nach Aktivierung: Resync der OpenSearch-ACLs triggern:
   ```bash
   curl -X POST https://<DEV_DOMAIN>/api/ext/doc-access/resync \
     -H "Cookie: fastapiusersauth=<ADMIN_SESSION>"
   ```
4. Celery-Task `doc_access_sync` läuft alle 60 Sekunden und hält ACLs synchron

Details: [ext-access-aktivierung.md](./ext-access-aktivierung.md)

### 4h. ext-i18n (Deutsch)

1. `NEXT_PUBLIC_EXT_I18N_ENABLED=true` (Build-Arg + values)
2. Frontend neu bauen (Cache-Miss im Browser erzwingen mit Hard-Refresh)
3. UI ist jetzt deutsch

**Eigene Strings ergänzen:** `web/src/ext/i18n/translations.ts` erweitern.

Der TranslationProvider nutzt einen DOM-Observer, der auch dynamisch eingefügten Text übersetzt (z. B. aus Toasts). Keine zusätzliche Konfiguration nötig.

### 4i. ext-audit

1. Flag `EXT_AUDIT_ENABLED=true`
2. Admin-UI: `/admin/ext/audit` zeigt Event-Log
3. 15 Hooks in 5 Routern protokollieren automatisch (branding, rbac, token, prompts, doc_access)
4. DSGVO-IP-Anonymisierung nach 90 Tagen läuft als täglicher Celery-Task
5. CSV-Export aus Admin-UI für Compliance-Reports

**Was protokolliert wird:** UUID, Timestamp, actor_email, actor_role, action, resource_type, resource_id, details (JSON), IP (anonymisiert nach 90d), User-Agent.

**Nicht protokolliert:** Login/Logout (Onyx-FOSS-Lücke), 401/403-Auth-Failures, 429-Token-Limit-Blockaden, CSV-Exporte (Audit-Gap).

---

## 5. Validierung nach Voll-Aktivierung

```bash
# Backend Feature Flags verifizieren
kubectl --context <CLUSTER_DEV> exec -n <NAMESPACE_DEV> deployment/onyx-dev-api-server -- env | grep EXT_

# Erwartung:
# EXT_ENABLED=true
# EXT_BRANDING_ENABLED=true
# EXT_TOKEN_LIMITS_ENABLED=true
# EXT_CUSTOM_PROMPTS_ENABLED=true
# EXT_ANALYTICS_ENABLED=true
# EXT_RBAC_ENABLED=true
# EXT_DOC_ACCESS_ENABLED=true
# EXT_AUDIT_ENABLED=true
# EXT_I18N_ENABLED=true
```

Admin-UI-Sidebar zeigt alle ext-Admin-Links:
- Token Usage
- System Prompts
- Gruppen (`/admin/ext-groups`)
- Analytics (via Grafana, extern)
- Audit-Log
- Branding

---

## 6. Lessons Learned (aus VÖB-Projekt)

### 6.1 `NEXT_PUBLIC_*`-Flags müssen zur Build-Zeit da sein

**Problem:** Next.js inlinet `NEXT_PUBLIC_*`-Env-Vars zum Build-Zeitpunkt ins Client-Bundle. Wenn man sie nur in `values-common.yaml` setzt (Runtime-ENV), landen sie **nicht** im Frontend.

**Lösung:** Dreifach-Pflege:
1. `web/Dockerfile` ARG + ENV (beide Stages)
2. `.github/workflows/stackit-deploy.yml` Build-Args
3. `values-common.yaml` (für Konsistenz, weil sie zur Laufzeit nicht gelesen werden, aber andere Teile sich darauf stützen könnten)

Beim Hinzufügen eines neuen Flags: Checkliste aus `.claude/rules/` (Helm-Values-Pattern).

Referenz: Memory `feedback_helm-values-pattern.md`.

### 6.2 Core #15 Custom-Analytics-Gate (PROD-Incident 2026-04-20)

**Problem:** Sync-#5 hatte ursprünglich `useCustomAnalyticsScript()` hinter `EXT_BRANDING_ENABLED` gated. Endpoint existiert nur in `backend/ee/` (EE-only) → 404-Loop in Browser-Konsole, mehrere Hundert 429-Retries pro Minute.

**Lösung:** Core-#15-Patch (`useSettings.ts`) darf **nur** `useEnterpriseSettings()` gaten, **nicht** `useCustomAnalyticsScript()`.

**Pattern:** Bei jedem Upstream-Sync prüfen, ob der Core-#15-Patch noch die richtige Scope-Abgrenzung hat. Verweis im Patch-Header auf `memory/feedback_core-15-customanalytics-gate.md`.

Referenz: CHANGELOG 2026-04-20.

### 6.3 ext-rbac + Upstream-Sync-#5 Default-Groups-Kollision

**Problem:** Upstream PR #9795 führte ein `seed_default_groups`-Migration ein, die „Admin" und „Basic" automatisch anlegt. Wenn der Kunde diese Namen bereits anders besetzt hatte (z. B. „Admin" = spezifische Abteilung), würde Upstream das zu „Admin (Custom)" umbenennen.

**Lösung:** Vor jedem Sync prüfen, ob Kollisionen drohen. Bei VÖB waren keine Konflikte (Gruppen-Namen anders), aber bei neuen Kunden prüfen:
```bash
# Vor Sync
kubectl exec -n <NAMESPACE> deployment/<helm-release>-api-server -- \
  psql $POSTGRES_URL -c "SELECT name FROM user_group;"
```

Referenz: CHANGELOG Sync #5.

### 6.4 ext-audit: Nachträgliche Aktivierung

**Problem:** Audit-Log greift erst ab Aktivierung. Historische Admin-Aktionen **nicht retroaktiv** dokumentiert.

**Empfehlung:** `ext-audit` **vor** Go-Live aktivieren, nicht nachträglich. Audit-Lücken bei Reviews dokumentieren.

### 6.5 ext-access Fail-Closed bei Fehler

**Design-Entscheidung:** Bei Fehler im ACL-Aufbau liefert der Celery-Task eine **leere** Zugriffsliste → User sieht **weniger** (nicht mehr) als er dürfte.

**Rationale:** Bank-Compliance — versehentlich sichtbare Dokumente wären ein Breach. Versehentlich unsichtbare Dokumente sind „nur" eine UX-Einschränkung.

Referenz: ADR (falls vorhanden), sonst Modulspec `ext-access.md`.

---

## 7. Deaktivierung / Rollback

Modul deaktivieren:
1. `EXT_<MODUL>_ENABLED=false` in `values-common.yaml`
2. `helm upgrade` triggern

Das Modul läuft nicht mehr, Daten in ext-Tabellen bleiben erhalten (kein Datenverlust). Bei Wieder-Aktivierung ist der Zustand sofort wiederhergestellt.

**Ausnahme ext-i18n:** Deaktivierung erfordert Frontend-Rebuild mit `NEXT_PUBLIC_EXT_I18N_ENABLED=false`.

---

## 8. Typische Fehler

### „EXT_BRANDING_ENABLED=true, aber UI zeigt immer noch ‚Onyx'"

Frontend-Build hat den Flag nicht mitbekommen. Prüfe:
1. `web/Dockerfile`: ARG + ENV vorhanden?
2. `stackit-deploy.yml`: build-args vorhanden?
3. Image wirklich neu gebaut? (bei nur `values`-Änderung läuft kein Build)
4. Browser Hard-Refresh (Ctrl+Shift+R)

### Admin-UI-Link fehlt

Core-Datei-Patch `AdminSidebar.tsx` (#10) fügt die Admin-Links bei aktiven Flags hinzu. Wenn ein Link fehlt, prüfen ob der Patch intakt ist:
```bash
grep EXT_TOKEN_LIMITS_ENABLED web/src/sections/sidebar/AdminSidebar.tsx
```

### Celery-Task `doc_access_sync` läuft nicht

1. `EXT_DOC_ACCESS_ENABLED=true` gesetzt?
2. Beat-Scheduler (celery_beat) läuft?
3. `kubectl logs deployment/<release>-celery-worker-light` → `doc_access_sync`-Aufrufe sichtbar?

---

## 9. Checkliste

- [ ] `EXT_ENABLED=true` in `values-common.yaml`
- [ ] Alle 8 Modul-Flags gesetzt (false/true je nach Bedarf)
- [ ] `web/Dockerfile`: 4 ARG + 4 ENV für `NEXT_PUBLIC_*`
- [ ] `stackit-deploy.yml`: 4 build-args
- [ ] Frontend-Build erfolgreich durchgelaufen
- [ ] Alembic-Migrationen bis `d8a1b2c3e4f5` (audit) applied
- [ ] Admin-UI zeigt alle aktiven ext-Admin-Links
- [ ] `/api/ext/health/deep` liefert 200
- [ ] Token-Limit für Admin-User gesetzt (damit Admin-Quota nicht unbegrenzt ist)
- [ ] Erste Gruppe (ext-rbac) angelegt
- [ ] System-Prompt (ext-prompts) angelegt (optional)
- [ ] Audit-Log zeigt erste Events (Admin-Aktionen nachvollziehbar)
- [ ] Analytics-Dashboard in Grafana importiert

---

## 10. Nächster Schritt

→ [post-go-live.md](./post-go-live.md) — Erste Kunden-Aktionen nach Go-Live (Admin anlegen, erste Dokumente, erste Gruppen)
