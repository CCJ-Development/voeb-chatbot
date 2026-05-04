---
paths:
  - "backend/onyx/**"
  - "web/src/app/**"
  - "web/src/components/**"
  - "web/src/lib/**"
  - "web/src/sections/**"
  - "web/src/refresh-components/**"
  - "web/src/providers/**"
---

# Core-Dateien: Was darf geändert werden

**NUR DIESE 17 DATEIEN dürfen verändert werden. Keine Ausnahmen.**

**Status (Stand 2026-05-02):** 16 von 17 gepatcht, nur **#5 `web/src/components/header/`** noch offen.

**Historie:**
- 2026-05-02 (Sync #7): Core #9 `AuthFlowContainer.tsx` **angepasst** — Opal-Migration: `OnyxIcon` aus `../icons/icons` (Legacy-Pfad) durch `SvgOnyxLogo` aus `@opal/logos` ersetzt. Custom-Logo-Conditional unveraendert, Fallback-Branch nutzt `SvgOnyxLogo`. Upstream PRs #10474 + #10483.
- 2026-05-02 (Sync #7): Core #17 `AccountPopover.tsx` **erweitert** — Schema-Migration `LineItem` → `LineItemButton` (Upstream PR #10646). Patch von 3 auf 4 `EXT_BRANDING_ENABLED`-Gate-Stellen erweitert: Notifications, Help & FAQ, Bubble (alle bestehend) + neuer "Onyx <version>"-Eintrag mit Link auf `docs.onyx.app/changelog` (Whitelabel-konsistent ausgeblendet bei aktivem Flag). Bubble-Conditional von `hasNotifications` auf `!!undismissedCount` (Upstream hat `hasNotifications` weg-refactored).
- 2026-04-20: Core #17 `AccountPopover.tsx` **neu** — `EXT_BRANDING_ENABLED`-Gate blendet im User-Dropdown (Klick auf eigenen Namen unten links) die Menu-Eintraege "Notifications" und "Help & FAQ" sowie den roten Notifications-Bubble-Indikator am Sidebar-Trigger aus. Whitelabel-Anforderung: VOeB nutzt Onyx' internes Release-Notes-/Announcement-System nicht, und "Help & FAQ" linkte auf `docs.onyx.app` (Onyx-Branding auf VOeB-Oberflaeche).
- 2026-04-20: Core #15 `useSettings.ts` **reduziert** — `useCustomAnalyticsScript`-Gate wieder entfernt (nur `useEnterpriseSettings` bleibt erweitert). Ursache: Endpoint `/api/enterprise-settings/custom-analytics-script` lebt nur in `backend/ee/` → 404 in FOSS → SWR-Retry-Loop spammt Browser-Konsole.
- 2026-04-20: Core #16 `DynamicMetadata.tsx` **neu** — `usePathname` dep fuer `document.title`-Resync nach Soft-Navigation. Upstream-Bug: `useEffect`-Dep-Array ohne `pathname` laesst Titel auf "Onyx" stehen wenn Next.js App Router bei Nav den statischen `metadata.title` neu injiziert.
- 2026-04-14 (Sync #5): Core #13 `CustomModal.tsx` **entfernt** — Upstream-Bug (onyx-dot-app/onyx#9592) gefixt via PRs #10009 ff.
- 2026-04-14 (Sync #5): Core #15 `useSettings.ts` **neu** — Upstream SSR→CSR Migration (#9529) gated `useEnterpriseSettings` hinter EE-Lizenz-Flag, Gate fuer ext-branding ohne EE-Lizenz.

**Uebersicht:**
| # | Datei | Status | Letzte Patch-Aenderung |
|---|-------|--------|-----------------------|
| 1 | `backend/onyx/main.py` | Gepatcht | Phase 4a |
| 2 | `backend/onyx/llm/multi_llm.py` | Gepatcht | ext-token |
| 3 | `backend/onyx/access/access.py` | Gepatcht | 2026-03-25 (ext-access) |
| 4 | `web/src/app/layout.tsx` | Gepatcht | 2026-03-22 (ext-i18n) |
| 5 | `web/src/components/header/` | **OFFEN** | — |
| 6 | `web/src/lib/constants.ts` | Gepatcht | ext-branding |
| 7 | `backend/onyx/chat/prompt_utils.py` | Gepatcht | ext-prompts |
| 8 | `web/src/app/auth/login/LoginText.tsx` | Gepatcht | 2026-03-08 (ext-branding) |
| 9 | `web/src/components/auth/AuthFlowContainer.tsx` | Gepatcht | 2026-05-02 (Sync #7 Opal-Migration) |
| 10 | `web/src/sections/sidebar/AdminSidebar.tsx` | Gepatcht | 2026-03-23 (ext-rbac) |
| 11 | `backend/onyx/db/persona.py` | Gepatcht | 2026-03-23 (ext-rbac) |
| 12 | `backend/onyx/db/document_set.py` | Gepatcht | 2026-03-23 (ext-rbac) |
| 13 | `backend/onyx/natural_language_processing/search_nlp_models.py` | Gepatcht | 2026-03-24 (OpenSearch lowercase) |
| 14 | `web/src/refresh-components/popovers/ActionsPopover/index.tsx` | Gepatcht | 2026-03-26 |
| 15 | `web/src/hooks/useSettings.ts` | Gepatcht | 2026-04-20 (Analytics-404-Fix) |
| 16 | `web/src/providers/DynamicMetadata.tsx` | Gepatcht | 2026-04-20 (ext-branding) |
| 17 | `web/src/sections/sidebar/AccountPopover.tsx` | Gepatcht | 2026-05-02 (Sync #7 LineItemButton-Migration + 4. Gate) |

## 1. `backend/onyx/main.py` — Router registrieren
- ERLAUBT: `from ext.config import EXT_ENABLED` + `register_ext_routers(app)` hinter Feature Flag + try/except ImportError
- VERBOTEN: Bestehende Router/Middleware/Startup-Events verändern
- MERGE: 7 Zeilen wieder einfügen (nach letztem Router, vor Auth-Block)
- HINWEIS: Funktion `get_application()` ab Zeile 419, Router-Registrierung Zeilen 447-509

## 2. `backend/onyx/llm/multi_llm.py` — Token Hook
- ERLAUBT: Nach LLM-Response Hook einfügen: `ext_token_counter.log_usage(...)` hinter Flag + Try/Except
- VERBOTEN: LLM-Call-Flow, Parameter, Return-Values verändern
- MERGE: Hook-Insertion-Point finden, Zeilen einfügen

## 3. `backend/onyx/access/access.py` — Access Control
- ERLAUBT: Additiver Permission-Check NACH bestehenden Checks, ext-Hooks fuer UserGroup-ACLs hinter Feature Flag
- VERBOTEN: Bestehende Checks veraendern/entfernen
- MERGE: Additiv, einfach einfuegen. Mittleres Merge-Risiko (access.py wird gelegentlich upstream geaendert)
- STATUS: ✅ Gepatcht (ext-access, 2026-03-25). 3 Hooks: `_get_access_for_document` + `_get_access_for_documents` (user_groups befuellen) + `_get_acl_for_user` (group: ACLs hinzufuegen). Alle hinter `EXT_DOC_ACCESS_ENABLED` + try/except.

## 4. `web/src/app/layout.tsx` — Navigation + i18n
- ERLAUBT: Nav-Items für ext/-Seiten, Conditional Rendering, Import ext/-Komponenten, TranslationProvider Wrapper, `lang="de"`
- VERBOTEN: Bestehende Nav/Layout umbauen
- MERGE: Nav-Items einfügen, TranslationProvider-Import + Wrapper beibehalten
- HINWEIS: ext-i18n (2026-03-22): 1 Import (`TranslationProvider`), `lang="de"` statt `lang="en"`, `<TranslationProvider>` um den Content-div gewickelt

## 5. `web/src/components/header/` — Branding
- ERLAUBT: Logo/Titel durch Config-Werte ersetzen mit Fallback auf Original
- VERBOTEN: Header-Layout/Struktur verändern
- MERGE: Config-Injection anpassen

## 6. `web/src/lib/constants.ts` — CSS Variables
- ERLAUBT: Neue CSS Properties mit --ext- Prefix, neue Konstanten mit ext_-Prefix
- VERBOTEN: Bestehende Variablen umbenennen/ändern
- MERGE: Additiv, kein Konflikt

## 7. `backend/onyx/chat/prompt_utils.py` — System Prompts
- ERLAUBT: Hook für Custom Prompt Injection (prepend, nicht override) hinter Flag
- VERBOTEN: Bestehenden Prompt-Flow verändern
- MERGE: Injection-Point einfügen

## 8. `web/src/app/auth/login/LoginText.tsx` — Login Tagline
- ERLAUBT: Tagline ("Your open source AI platform for work") durch EnterpriseSettings-Wert ersetzen oder entfernen, mit Fallback
- VERBOTEN: Login-Layout/Struktur verändern
- MERGE: Textersetzung, kein Strukturkonflikt
- HINWEIS: Freigabe durch Niko (2026-03-08) für ext-branding Whitelabel

## 9. `web/src/components/auth/AuthFlowContainer.tsx` — Login Icon + Text
- ERLAUBT: `SvgOnyxLogo` aus `@opal/logos` durch Custom Logo ersetzen (mit Fallback auf `SvgOnyxLogo`), "New to Onyx?" durch `application_name` ersetzen, ext-i18n `t()`-Calls fuer alle user-sichtbaren Strings, `useContext(SettingsContext)` fuer `enterpriseSettings`-Lookup
- VERBOTEN: Auth-Flow-Logik, Formular-Struktur verändern
- MERGE: 2 Stellen: Imports (`Image`, `SvgOnyxLogo` von `@opal/logos`, `useContext`, `SettingsContext`, `t`) + Icon-Ersetzung im JSX (`use_custom_logo` Conditional → `Image` ODER `SvgOnyxLogo`-Fallback). Niedriges Merge-Risiko aber Frontend-Component-Refactor moeglich (Sync #7 hatte `OnyxIcon`→`SvgOnyxLogo`-Migration).
- STATUS: ✅ Gepatcht. Letzter Patch-Update: 2026-05-02 (Sync #7) — Opal-Migration `OnyxIcon` aus `../icons/icons` (Legacy) → `SvgOnyxLogo` aus `@opal/logos`.
- HINWEIS: Freigabe durch Niko (2026-03-08) für ext-branding Whitelabel. Bei zukuenftigen Opal-Migrationen (Sync #8+) muss der Fallback-Branch ggf. erneut umgebogen werden — `web/CLAUDE.md` ist die SoT fuer aktuelle Komponentenpfade.

## 10. `web/src/sections/sidebar/AdminSidebar.tsx` — Admin Sidebar
- ERLAUBT: "Upgrade Plan"/Billing ausblenden wenn ext-branding aktiv, "Branding"-Link + "Token Usage"-Link + "System Prompts"-Link + "Gruppen"-Link einfuegen, ausgegraute EE-Items (Groups, SCIM, Theme, Usage, Query History) komplett ausblenden wenn EE nicht aktiv
- VERBOTEN: Sidebar-Struktur, andere Sections, Navigation-Logik veraendern
- MERGE: Settings-Section anpassen (Zeilen ~155-170), Import ergaenzen (SvgPaintBrush, SvgActivity, SvgFileText, SvgUsers), EE-Guards in Sections 5/6/7, Permissions-Section (Gruppen-Link bei EXT_RBAC)
- HINWEIS: Freigabe durch Niko (2026-03-08) fuer ext-branding Whitelabel. Erweitert fuer ext-token (SvgActivity), ext-prompts (SvgFileText), EE-Cleanup (2026-03-19). ext-rbac (2026-03-23): "Gruppen"-Link auf `/admin/ext-groups` bei `EXT_RBAC_ENABLED`.

## 11. `backend/onyx/db/persona.py` — Persona/Agent Gruppen-Zuordnung [AKTIV]
- ERLAUBT: In `update_persona_access()` den `NotImplementedError`-Block durch ext-Hook ersetzen (hinter `EXT_RBAC_ENABLED` Flag + try/except). Bestehende User-Sharing-Logik NICHT veraendern.
- VERBOTEN: Persona-CRUD, Sharing-Logik, User-Zuordnung veraendern
- MERGE: Hook nach `if group_ids:` Guard einfuegen (~Zeile 244). Mittel-hohes Merge-Risiko (14 Commits/3 Monate, Sharing-Features aktiv upstream)
- STATUS: ✅ Gepatcht (ext-rbac, 2026-03-23). Hook inseriert Persona__UserGroup Eintraege wenn EXT_RBAC_ENABLED.
- HINWEIS: `versioned_update_persona_access` nutzt `fetch_versioned_implementation` — EE-Override funktioniert NICHT (is_ee_version=false). Daher direkter Hook in FOSS-Funktion noetig.

## 12. `backend/onyx/db/document_set.py` — DocumentSet Gruppen-Zuordnung [AKTIV]
- ERLAUBT: In `make_doc_set_private()` den `NotImplementedError`-Block durch ext-Hook ersetzen (hinter `EXT_RBAC_ENABLED` Flag + try/except). Bestehende Public/Private-Logik NICHT veraendern.
- VERBOTEN: DocumentSet-CRUD, Filterung, Sync-Logik veraendern
- MERGE: Hook vor `raise NotImplementedError` einfuegen (~Zeile 179). Niedriges Merge-Risiko (5 Commits/3 Monate, Funktion seit 2026-01-29 unveraendert)
- STATUS: ✅ Gepatcht (ext-rbac, 2026-03-23). Hook inseriert DocumentSet__UserGroup Eintraege wenn EXT_RBAC_ENABLED.
- HINWEIS: Analog zu #11, gleicher Hook-Pattern.

## 13. `backend/onyx/natural_language_processing/search_nlp_models.py` — Index-Name lowercase [TEMPORAER]
- ERLAUBT: `.lower()` an `clean_model_name()` Return-Value anhaengen
- VERBOTEN: Alles andere in dieser Datei veraendern
- MERGE: 1 Stelle, 1 Zeile. Niedriges Merge-Risiko (Funktion seit Monaten unveraendert)
- STATUS: ✅ Gepatcht (2026-03-24). OpenSearch verlangt lowercase Index-Namen, `clean_model_name()` macht kein `.lower()`.
- HINWEIS: **TEMPORAER** — Upstream-Bug. Bei Upstream-Sync pruefen ob gefixt. Betrifft jeden OpenSearch-User mit Modellnamen die Grossbuchstaben enthalten.

## 14. `web/src/refresh-components/popovers/ActionsPopover/index.tsx` — Actions-Popover fuer Basic User ausblenden
- ERLAUBT: Early-Return `if (!isAdmin && !isCurator) return null;` nach allen Hooks, vor `displayTools`
- VERBOTEN: Tool-Logik, Popover-Struktur, MCP-Handling veraendern
- MERGE: 1 Stelle, 1 Zeile (nach letztem `useCallback`, vor `displayTools` Filter). Niedriges Merge-Risiko (Insertion-Stelle ist stabil)
- STATUS: ✅ Gepatcht (2026-03-26). Basic User sehen den "Manage Actions" Button im Chat nicht.
- HINWEIS: `useUser()` mit `isAdmin`/`isCurator` ist bereits in der Komponente vorhanden (Zeile 306). Kein neuer Import noetig.

## 15. `web/src/hooks/useSettings.ts` — useEnterpriseSettings ohne EE-Lizenz-Flag aktivieren
- ERLAUBT: `NEXT_PUBLIC_EXT_BRANDING_ENABLED` als zusaetzlichen Gate in `shouldFetch` **NUR fuer `useEnterpriseSettings()`**. Konstante am Datei-Anfang definieren. `useCustomAnalyticsScript()` bleibt auf Upstream-Original (nur EE-Flags).
- VERBOTEN: SWR-Config, API-Keys, DEFAULT_SETTINGS, Return-Shape veraendern. Insbesondere KEINEN `EXT_BRANDING_ENABLED`-Gate in `useCustomAnalyticsScript()` einfuegen — der Endpoint existiert in FOSS nicht.
- MERGE: 2 Stellen: Import+Const (~8 Zeilen nach EE_ENABLED import), `shouldFetch =` (1x in `useEnterpriseSettings`, nach `EE_ENABLED || eeEnabledRuntime` ein `|| EXT_BRANDING_ENABLED` anfuegen). Niedriges Merge-Risiko (Upstream hat diese Zeile in PR #9529 stabilisiert, weitere Aenderungen unwahrscheinlich).
- STATUS: ✅ Gepatcht (2026-04-14, Sync #5). Auf einen Gate reduziert 2026-04-20 (siehe HINWEIS unten).
- HINWEIS: **Entkoppelt von EE-Lizenz.** Wir setzen weder `ENABLE_PAID_ENTERPRISE_EDITION_FEATURES` noch `LICENSE_ENFORCEMENT_ENABLED` noch `NEXT_PUBLIC_ENABLE_PAID_EE_FEATURES`. Der neue Flag `NEXT_PUBLIC_EXT_BRANDING_ENABLED` ist semantisch klar "VÖB-Branding-Hook aktivieren" und aktiviert keine EE-Features. Build-Arg muss in `web/Dockerfile` (beide Stages) und `.github/workflows/stackit-deploy.yml` gesetzt sein.
- HINWEIS 2 (2026-04-20): Der urspruengliche Sync-#5-Patch gated AUCH `useCustomAnalyticsScript()` hinter `EXT_BRANDING_ENABLED`. Folge: SWR rief `/api/enterprise-settings/custom-analytics-script` in PROD auf, der Endpoint lebt aber nur in `backend/ee/` (EE-only) → 404 → SWR-Default `shouldRetryOnError: true` + Exponential-Backoff = Endlos-Loop in der Browser-Konsole (Hunderte `setTimeout`-Retries pro Minute). Fix: Gate auf Upstream-Original zurueck. VOeB nutzt kein Custom Analytics Script; bei Bedarf koennte spaeter ein `ext-analytics`-Endpoint den Pfad bedienen.

## 16. `web/src/providers/DynamicMetadata.tsx` — document.title Re-Sync nach Soft-Navigation
- ERLAUBT: `usePathname()` + `useSearchParams()` aus `next/navigation` importieren + `pathname` + `searchParams` zur Dep-Liste des title-`useEffect` hinzufuegen. 3-Zeilen-Kommentar zur Begruendung ueber den Hook-Aufrufen.
- VERBOTEN: Title-Logik veraendern, Favicon-Logik veraendern, Return-JSX veraendern, `use_custom_logo`-Zweig anfassen.
- MERGE: 1 Stelle, ~9 Zeilen (1 Import + 2 Hook-Calls + 1 Dep-Array-Erweiterung + 3 Kommentarzeilen). Niedriges Merge-Risiko (Datei ist klein und aendert sich upstream selten).
- STATUS: ✅ Gepatcht (2026-04-20). Ohne `pathname` in den Deps laeuft der `useEffect` bei Route-Wechsel nicht neu (SWR-Referenz von `enterpriseSettings` stabil). Ohne `searchParams` fehlen Query-Only-Transitions: Chat-Wechsel ruft `/chat?chatId=xxx` auf, wird aber per Next.js-Redirect (`next.config.js`) auf `/app?chatId=xxx` umgeleitet → pathname bleibt `/app`, nur `searchParams` aendert sich. Beide Deps zusammen decken jede URL-Aenderung ab. Next.js App Router injiziert bei jeder Navigation den statischen `metadata.title = "Onyx"` aus `app/layout.tsx` in den `<head>`; der Effect ueberschreibt das synchron zurueck.

## 17. `web/src/sections/sidebar/AccountPopover.tsx` — User-Menu Whitelabel-Aufraeumung
- ERLAUBT: `NEXT_PUBLIC_EXT_BRANDING_ENABLED`-Konstante am Dateianfang (nach den Imports) definieren + **4 Stellen** mit `!EXT_BRANDING_ENABLED &&` (bzw. `!!undismissedCount && !EXT_BRANDING_ENABLED` fuer Bubble) gaten: (a) `LineItemButton` "Notifications" im `PopoverMenu`-Array, (b) `LineItemButton` "Help & FAQ" im `PopoverMenu`-Array, (c) Notifications-Bubble in `rightChildren` der `SidebarTab`, (d) `<div key="version">`-Eintrag mit `Content`-Komponente am Ende des Arrays (Onyx-Version-Link auf docs.onyx.app/changelog).
- VERBOTEN: Menu-Reihenfolge, Menu-Item "Settings" (`SvgSliders`), `<div key="user-email">`-Eintrag, Trenner (`null`-Eintrag), Login/Logout-Logik, `SidebarTab`-Props (ausser `rightChildren`-Conditional), Popover-Struktur, SWR-Fetches veraendern. SWR-Calls bleiben erhalten (kein Funktionsunterschied bei deaktiviertem Flag, Upstream-Behaviour wird respektiert).
- MERGE: 4 Stellen: Konstante (~14 Zeilen inkl. Kommentar) nach UserAvatar-Import + 2x Array-Element-Gate im PopoverMenu (Notifications + Help-FAQ als `LineItemButton`) + 1x neues Array-Element-Gate (`version`-Eintrag, neu seit Sync #7 / PR #10646) + 1x Bubble-Conditional in SidebarTab rightChildren. **Mittel-hohes Merge-Risiko:** Upstream hat das gesamte Menu in Sync #7 von `LineItem` auf `LineItemButton` umgestellt — bei zukuenftigen Opal-Migrationen (z. B. weiterer Schema-Wechsel, neue Menu-Eintraege) muss der Patch komplett neu angewendet werden.
- STATUS: ✅ Gepatcht. Letzter Patch-Update: 2026-05-02 (Sync #7) — `LineItem` → `LineItemButton`-Schema-Migration, 4. Gate-Stelle (`version`-Eintrag) hinzugefuegt, Bubble-Conditional von `hasNotifications` auf `!!undismissedCount` (Upstream-Refactor). Bei `NEXT_PUBLIC_EXT_BRANDING_ENABLED=true` zeigt das User-Menu nur noch "User-Email" + Trenner + "Settings" + Trenner + "Log Out".
- HINWEIS: Build-time Gate, gesetzt in `web/Dockerfile` (beide Stages) und `.github/workflows/stackit-deploy.yml` — gleicher Flag wie Core #15 (`useSettings.ts`). Kein neuer Build-Arg noetig. `onShowBuildIntro`-Prop bleibt erhalten (wird via `NotificationsPopover` weitergeleitet, aber Popover wird bei aktivem Flag nie geoeffnet — defensiv). Die ext-i18n-Eintraege "Notifications" und "Help & FAQ" im Translation-Dictionary werden NICHT entfernt — sie sind tot-code bei aktivem Flag, aber ein Rueckzug auf Upstream (Flag off) wuerde sie wieder brauchen.

## Absicherung
Vor JEDER Core-Datei-Änderung:
```bash
mkdir -p backend/ext/_core_originals/
cp <original> backend/ext/_core_originals/<name>.original
# Nach Änderung:
diff -u backend/ext/_core_originals/<name>.original <geändert> > backend/ext/_core_originals/<name>.patch
```

## Patch-Verwaltung
- **Ein .original + ein .patch PRO Core-Datei** (nicht pro Modul)
- Wenn mehrere Module dieselbe Core-Datei patchen, waechst der Patch kumulativ
- `.original` = immer die unveraenderte Upstream-Version
- `.patch` = Diff zwischen Upstream und unserem Stand (alle Hooks zusammen)
- Beispiel: ext-rbac UND ext-access patchen beide `access.py` → ein `.patch` mit beiden Hooks
- Bei Upstream-Merge: `.original` aktualisieren, `.patch` regenerieren (siehe fork-management.md Schritt 5)

## Hook-Pattern für Core-Dateien
```python
try:
    from ext.config import EXT_FEATURE_ENABLED
    if EXT_FEATURE_ENABLED:
        from ext.services.feature import do_something
        do_something(...)
except ImportError:
    pass  # ext/ nicht vorhanden → Onyx läuft normal
except Exception:
    import logging
    logging.getLogger("ext").error("Extension hook failed", exc_info=True)
    # NIEMALS Onyx-Funktionalität brechen
```
