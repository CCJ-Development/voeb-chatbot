# Extension-Entwicklungsplan — VoeB Chatbot

**Stand**: Maerz 2026
**Erstellt von**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Bezug**: [EE/FOSS-Abgrenzung](ee-foss-abgrenzung.md) | [Extension Framework](../technisches-feinkonzept/ext-framework.md) | [Projektstatus](../../.claude/rules/voeb-projekt-status.md)

---

## Uebersicht

Alle Enterprise-Features werden custom in `backend/ext/` + `web/src/ext/` entwickelt, da wir Onyx FOSS (MIT) ohne Enterprise-Lizenz nutzen. Siehe [EE/FOSS-Abgrenzung](ee-foss-abgrenzung.md) fuer Details.

### Moduluebersicht

```
Phase 4a: ✅ Extension Framework Basis (erledigt)
          │
          ├── Phase 4b: ✅ ext-branding (implementiert + DEV/TEST deployed 2026-03-08)
          │     Whitelabel: Logo, App-Name, Login-Text, Greeting, Disclaimer, Popup, Consent
          │     Offen: Favicon, Farben/Theme (Kundenabstimmung)
          │
          ├── Phase 4c: ✅ ext-token (implementiert + DEV/TEST deployed 2026-03-09)
          │     LLM-Nutzung tracken, Limits pro User/Gruppe
          │
          ├── Phase 4d: ✅ ext-prompts (DEV + TEST deployed + abgenommen 2026-03-09)
          │     Custom System Prompts (globale Anweisungen fuer jeden LLM-Aufruf)
          │
          ├── Phase 4e: ⏭️ ext-analytics — ÜBERSPRUNGEN
          │     Funktionalität bereits in ext-token enthalten
          │
          ├── Phase 4f: ✅ ext-rbac (implementiert 2026-03-23)
          │     Gruppenverwaltung, 7 Endpoints, Core #10/#11/#12 gepatcht
          │
          ├── Phase 4g: ✅ ext-access (implementiert 2026-03-25)
          │     Document Access Control pro Gruppe, Core #3 gepatcht, eigener Celery-Task
          │
          ├── Phase 4h: ✅ ext-i18n (DEV + PROD deployed 2026-03-22)
          │     Deutsche Lokalisierung (~250 Strings), TranslationProvider + t()-Calls
          │
          └── Phase 4i: ✅ ext-audit (implementiert 2026-03-25)
                Audit-Logging, 15 Hooks, DB-Tabelle ext_audit_log, CSV-Export
```

---

## Abhaengigkeitsgraph

```
                    ┌─────────────────┐
                    │ Phase 4a:       │
                    │ ext-framework   │
                    │ ✅ ERLEDIGT     │
                    └────────┬────────┘
                             │
         ┌───────────┬───────┴───────┬────────────┐
         ▼           ▼               ▼            ▼
   ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐
   │ext-branding│ │ext-token │ │ext-prompts│ │ext-analytics│
   │ Phase 4b  │ │ Phase 4c │ │ Phase 4d  │ │ Phase 4e  │
   │ ✅ ERLED. │ │ ✅ ERLED.│ │ ✅ ERLED. │ │⏭️ÜBERSP. │
   └───────────┘ └─────┬────┘ └───────────┘ └─────┬─────┘
                        │                           │
                        │      ┌──────────┐         │
                        └─────►│ext-rbac  │◄────────┘
                               │ Phase 4f │
                               │ ✅ ERLED.│
                               │(2026-3-23)│
                               └─────┬────┘
                                     │
                               ┌─────▼─────┐
                               │ext-access  │
                               │ Phase 4g   │
                               │ ✅ ERLED.  │
                               │(2026-3-25) │
                               └────────────┘
```

---

## Blocker-Analyse

| Modul | Blocker | Wartet auf | Workaround |
|-------|---------|-----------|------------|
| ext-branding | **Keiner** | — | — |
| ext-token | **Keiner** | — | — |
| ext-prompts | **Keiner** | — | — |
| ext-analytics | **UEBERSPRUNGEN** | — | Funktionalitaet in ext-token enthalten |
| ext-rbac | **Keiner** | — | ✅ Implementiert (2026-03-23) |
| ext-access | **Keiner** | — | ✅ Implementiert (2026-03-25) |

---

## Empfohlene Reihenfolge

### Prioritaet 1: ext-branding (Phase 4b)

**Warum zuerst**: Sofort sichtbarer Mehrwert fuer VoeB. Kunde will komplettes Whitelabel — kein Onyx-Branding mehr sichtbar.

| Aspekt | Detail |
|--------|--------|
| **Scope** | App-Name, Logo, Favicon, Sidebar-Branding, Login-Seite, Browser-Tab |
| **Core-Aenderungen** | CORE #4 (layout.tsx): Favicon + Title | CORE #5 (header): Logo-Injection | CORE #6 (constants.ts): ext_-Konstanten |
| **Backend** | `backend/ext/routers/branding.py` — GET/PUT Branding Config |
| | `backend/ext/models/branding.py` — `ext_branding_config` Tabelle |
| | `backend/ext/services/branding.py` — Business Logic, Logo-Storage |
| **Frontend** | `web/src/ext/components/BrandingProvider.tsx` — Settings-Injection |
| **DB** | 1 Tabelle: `ext_branding_config` |
| **Feature Flag** | `EXT_BRANDING_ENABLED` (existiert bereits in config.py) |
| **Aufwand** | Mittel — Backend-Store + 3 Core-Patches + Frontend-Integration |
| **Abhaengigkeit** | Keine |

**Technischer Ansatz**: Die FOSS-Frontend-Komponenten (`Logo.tsx`, `SidebarWrapper.tsx`, `layout.tsx`) lesen bereits aus `EnterpriseSettings`. Wir bauen einen Backend-Store der dieselben Felder ueber den FOSS-Endpoint `/enterprise-settings` befuellt (nutzt FOSS-Frontend-Pfad, keine ext/-Route noetig), und injizieren die Werte in den bestehenden `SettingsProvider`. So nutzen wir die vorhandene Rendering-Logik ohne sie zu duplizieren.

> **Implementierungsabweichung:** Nutzt den FOSS-EnterpriseSettings-Endpoint statt eigenem ext/-Pfad (siehe ext-branding.md Abschnitt Architekturentscheidung).

**Alternative**: Komplett eigene Komponenten in `web/src/ext/`. Vorteil: Null Abhaengigkeit von Onyx-Frontend. Nachteil: Doppelte Arbeit, Onyx-Logo-Reste koennten durchscheinen.

### Prioritaet 2: ext-token (Phase 4c)

**Warum als zweites**: Wichtig fuer Kostenkontrolle und Nutzungstransparenz. Banken brauchen Nachvollziehbarkeit.

| Aspekt | Detail |
|--------|--------|
| **Scope** | LLM-Aufrufe loggen (Tokens, Modell, User, Timestamp), Usage-API, spaeter: Limits |
| **Core-Aenderungen** | CORE #2 (multi_llm.py): Hook nach LLM-Response fuer Token-Logging |
| **Backend** | `backend/ext/routers/token.py` — GET Usage Stats |
| | `backend/ext/models/token.py` — `ext_token_usage` Tabelle |
| | `backend/ext/services/token_counter.py` — Zaehler + Aggregation |
| **Frontend** | `web/src/ext/pages/admin/token-usage.tsx` — Admin-Dashboard (spaeter) |
| **DB** | 1 Tabelle: `ext_token_usage` (user_id, model, prompt_tokens, completion_tokens, timestamp) |
| **Feature Flag** | `EXT_TOKEN_LIMITS_ENABLED` (existiert bereits in config.py) |
| **Aufwand** | Mittel — 1 Core-Patch + DB-Tabelle + Aggregations-Logik |
| **Abhaengigkeit** | Keine (User-Zuordnung funktioniert auch mit Basic Auth in DEV) |

### Prioritaet 3: ext-prompts (Phase 4d)

**Warum als drittes**: Ermoeglicht VoeB-spezifische Anweisungen an die LLMs (Tonalitaet, Compliance-Hinweise, Abteilungs-Kontext).

| Aspekt | Detail |
|--------|--------|
| **Scope** | System Prompt Injection (prepend, nicht replace), Admin-UI zum Verwalten |
| **Core-Aenderungen** | CORE #7 (prompt_utils.py): Hook fuer Custom Prompt Injection |
| **Backend** | `backend/ext/routers/prompts.py` — CRUD Prompt Templates |
| | `backend/ext/models/prompts.py` — `ext_prompt_templates` Tabelle |
| | `backend/ext/services/prompt_injection.py` — Injection-Logik |
| **Frontend** | `web/src/ext/pages/admin/prompt-templates.tsx` — Admin-UI |
| **DB** | 1 Tabelle: `ext_prompt_templates` (name, content, scope, is_active) |
| **Feature Flag** | `EXT_CUSTOM_PROMPTS_ENABLED` (existiert bereits in config.py) |
| **Aufwand** | Mittel — 1 Core-Patch + CRUD + Injection-Logik |
| **Abhaengigkeit** | Keine |

### ~~Prioritaet 4: ext-analytics (Phase 4e)~~ — ÜBERSPRUNGEN

**Entscheidung (2026-03-09):** ext-token liefert bereits Usage Dashboard (Overview, Timeline, Per-User, Per-Model, User Limits). Ein eigenes Analytics-Modul haette keinen Mehrwert. Falls spaeter CSV-Export gewuenscht, wird er direkt in ext-token ergaenzt.

### Prioritaet 5: ext-rbac (Phase 4f) — IMPLEMENTIERT

**Implementiert**: 2026-03-23 (7 Endpoints, 29 Tests, Core #10/#11/#12 gepatcht)

| Aspekt | Detail |
|--------|--------|
| **Scope** | 4 Rollen (System-Admin, Gruppen-Admin, Power-User, Standard-User), Gruppen = Abteilungen |
| **Core-Aenderungen** | CORE #3 (access.py): Additiver Permission-Check nach bestehenden Checks |
| **Backend** | `backend/ext/models/rbac.py` — `ext_user_groups`, `ext_user_roles`, `ext_group_permissions` |
| | `backend/ext/services/rbac.py` — Rollen-Mapping, Gruppen-Sync |
| | `backend/ext/services/entra_sync.py` — Entra ID Gruppen-Sync |
| **Frontend** | `web/src/ext/pages/admin/groups.tsx` — Gruppen-Verwaltung |
| **DB** | 3+ Tabellen |
| **Feature Flag** | `EXT_RBAC_ENABLED` (existiert bereits in config.py) |
| **Aufwand** | Hoch — Entra ID Integration + Rollen-System + Gruppen-Sync |
| **Abhaengigkeit** | Phase 3 (Entra ID Auth) muss abgeschlossen sein |
| **Vorarbeit** | Rollenmodell-Entwurf existiert (docs/referenz/rbac-rollenmodell.md), 10 Fragen an VoeB offen |

### Prioritaet 6: ext-access (Phase 4g) — IMPLEMENTIERT

**Implementiert**: 2026-03-25 (Core #3 gepatcht, eigener Celery-Task, 11 Tests)

| Aspekt | Detail |
|--------|--------|
| **Scope** | Document Access Control: Welche Gruppe sieht welche Dokumente/Agenten/Modelle |
| **Core-Aenderungen** | CORE #3 (access.py): Gruppen-basierte Dokumentfilterung |
| **Abhaengigkeit** | ext-rbac (Gruppen muessen existieren) |

### Zukuenftig: ext-retention (GEPLANT)

**Herkunft:** Kickoff-Beschluss KICKOFF-012 (Chat-Retention 6 Monate).

| Aspekt | Detail |
|--------|--------|
| **Scope** | Automatische Loeschung von Chat-Verlaeufen nach 6 Monaten |
| **Abhaengigkeit** | Loeschkonzept (DSGVO-konform, DIN EN ISO/IEC 27555:2025-09) |
| **Implementierung** | Cronjob oder DB-Funktion (periodisches DELETE auf `chat_message` + `chat_session` mit Altersfilter) |
| **Feature Flag** | `EXT_RETENTION_ENABLED` (noch nicht in config.py) |
| **Status** | GEPLANT — Implementierung nach Loeschkonzept-Erstellung |

---

## Entwicklungs-Workflow pro Modul

Jedes Modul durchlaeuft denselben Prozess:

```
1. /modulspec erstellen
   └── docs/technisches-feinkonzept/ext-{modul}.md

2. Freigabe durch Niko
   └── Dokumentstatus: Freigegeben

3. /ext-framework aufrufen (6-Schritte-Pflicht)
   └── Analyse → Plan → Spec → Review → Implement → Test

4. Feature-Branch erstellen
   └── git checkout -b feature/ext-{modul}

5. Implementierung
   ├── Backend: ext/models/ → ext/services/ → ext/routers/
   ├── Core-Patches: _core_originals/ sichern → Hook einfuegen
   ├── Frontend: web/src/ext/
   └── Tests: ext/tests/

6. Selbst-Review (Sicherheits-Checkliste)
   └── .claude/rules/sicherheit.md

7. Praesentation an Niko
   └── Dateien, Tests, Core-Aenderungen, offene Punkte

8. Freigabe → Commit → Push → Merge auf main → Deploy
```

---

## DB-Migrations-Strategie

Alle ext_-Tabellen nutzen **Onyx Alembic** (kein eigener Alembic-Branch):

```bash
# Migration erstellen
alembic revision -m "ext_branding: Create ext_branding_config table"

# Migration ausfuehren
alembic upgrade head
```

**Konventionen**:
- Tabellen-Prefix: `ext_` (z.B. `ext_branding_config`, `ext_token_usage`)
- Migrations-Prefix im Kommentar: `ext_{modul}:`
- Keine ALTER TABLE auf bestehende Onyx-Tabellen
- Foreign Keys auf Onyx-Tabellen (z.B. `user_.id`) sind erlaubt (READ-ONLY Referenz)

---

## Core-Datei-Aenderungen: Gesamtuebersicht

| Core | Datei | ext-branding | ext-token | ext-prompts | ext-rbac | ext-access | ext-i18n |
|------|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| #1 | `main.py` | — | — | — | — | — | — |
| #2 | `multi_llm.py` | — | ✅ | — | — | — | — |
| #3 | `access.py` | — | — | — | ✅ | ✅ | — |
| #4 | `layout.tsx` | ✅ | — | — | — | — | ✅ |
| #5 | `header/` | ✅ | — | — | — | — | — |
| #6 | `constants.ts` | ✅ | — | — | — | — | — |
| #7 | `prompt_utils.py` | — | — | ✅ | — | — | — |
| #8 | `LoginText.tsx` | ✅ | — | — | — | — | — |
| #9 | `AuthFlowContainer.tsx` | ✅ | — | — | — | — | — |
| #10 | `AdminSidebar.tsx` | ✅ | ✅ | ✅ | ✅ | — | — |
| #11 | `persona.py` | — | — | — | ✅ | — | — |
| #12 | `document_set.py` | — | — | — | ✅ | — | — |
| #13 | `CustomModal.tsx` | — | — | — | — | — | — |
| #14 | `search_nlp_models.py` | — | — | — | — | — | — |

> CORE #1 (`main.py`) ist bereits gepatcht (Extension Framework Hook, Phase 4a).
> Alle Patches folgen dem try/except-Pattern aus `.claude/rules/core-dateien.md`.
> **13 von 14 Core-Dateien sind gepatcht** (Stand 2026-03-25). Ungepatcht: header/ (#5, offen).

---

## Feature-Flag-Uebersicht

Alle Flags existieren bereits in `backend/ext/config.py`:

| Flag | Modul | Default | Hinweis |
|------|-------|---------|---------|
| `EXT_ENABLED` | Master-Switch | `false` | |
| `EXT_BRANDING_ENABLED` | ext-branding | `false` | |
| `EXT_TOKEN_LIMITS_ENABLED` | ext-token | `false` | |
| `EXT_CUSTOM_PROMPTS_ENABLED` | ext-prompts | `false` | |
| `EXT_ANALYTICS_ENABLED` | ext-analytics | `false` | UEBERSPRUNGEN (2026-03-09) — Funktionalitaet bereits in ext-token enthalten. Flag existiert noch in config.py (Default false), wird in Zukunft entfernt. |
| `EXT_RBAC_ENABLED` | ext-rbac | `false` | |
| `EXT_DOC_ACCESS_ENABLED` | ext-access | `false` | |
| `EXT_I18N_ENABLED` | ext-i18n | `false` | + `NEXT_PUBLIC_EXT_I18N_ENABLED` (Frontend Build-Arg) |
| `EXT_AUDIT_ENABLED` | ext-audit | `false` | |

Aktivierung in `deployment/docker_compose/.env` oder `deployment/helm/values/values-{env}.yaml`.

---

## Referenzen

- [EE/FOSS-Abgrenzung](ee-foss-abgrenzung.md) — Lizenz-Details
- [Extension Framework Spec](../technisches-feinkonzept/ext-framework.md) — Basis-Architektur
- [RBAC Rollenmodell](rbac-rollenmodell.md) — Rollen-Entwurf (Phase 4f)
- [Core-Dateien Regeln](../../.claude/rules/core-dateien.md) — Erlaubte Aenderungen
- [Sicherheits-Checkliste](../../.claude/rules/sicherheit.md) — Pruefung pro Modul
- [Commit-Workflow](../../.claude/rules/commit-workflow.md) — Branch + PR Prozess
