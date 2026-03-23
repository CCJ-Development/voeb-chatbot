---
paths:
  - "backend/onyx/**"
  - "web/src/app/**"
  - "web/src/components/**"
  - "web/src/lib/**"
---

# Core-Dateien: Was darf geändert werden

**NUR DIESE 12 DATEIEN dürfen verändert werden. Keine Ausnahmen.**
**#1-#10:** Aktiv gepatcht (8 von 10 haben Patches, #3 und #5 noch offen).
**#11-#12:** Reserviert fuer Phase 4g (ext-access). Noch NICHT gepatcht.

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
- ERLAUBT: Additiver Permission-Check NACH bestehenden Checks
- VERBOTEN: Bestehende Checks verändern/entfernen
- MERGE: Additiv, einfach einfügen

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
- ERLAUBT: OnyxIcon durch Custom Logo ersetzen (mit Fallback), "New to Onyx?" durch application_name ersetzen
- VERBOTEN: Auth-Flow-Logik, Formular-Struktur verändern
- MERGE: Icon/Text-Ersetzung, kein Strukturkonflikt
- HINWEIS: Freigabe durch Niko (2026-03-08) für ext-branding Whitelabel

## 10. `web/src/sections/sidebar/AdminSidebar.tsx` — Admin Sidebar
- ERLAUBT: "Upgrade Plan"/Billing ausblenden wenn ext-branding aktiv, "Branding"-Link + "Token Usage"-Link + "System Prompts"-Link + "Gruppen"-Link einfuegen, ausgegraute EE-Items (Groups, SCIM, Theme, Usage, Query History) komplett ausblenden wenn EE nicht aktiv
- VERBOTEN: Sidebar-Struktur, andere Sections, Navigation-Logik veraendern
- MERGE: Settings-Section anpassen (Zeilen ~155-170), Import ergaenzen (SvgPaintBrush, SvgActivity, SvgFileText, SvgUsers), EE-Guards in Sections 5/6/7, Permissions-Section (Gruppen-Link bei EXT_RBAC)
- HINWEIS: Freigabe durch Niko (2026-03-08) fuer ext-branding Whitelabel. Erweitert fuer ext-token (SvgActivity), ext-prompts (SvgFileText), EE-Cleanup (2026-03-19). ext-rbac (2026-03-23): "Gruppen"-Link auf `/admin/ext-groups` bei `EXT_RBAC_ENABLED`.

## 11. `backend/onyx/db/persona.py` — Persona/Agent Gruppen-Zuordnung [RESERVIERT Phase 4g]
- ERLAUBT: In `update_persona_access()` den `NotImplementedError`-Block durch ext-Hook ersetzen (hinter `EXT_DOC_ACCESS_ENABLED` Flag + try/except). Bestehende User-Sharing-Logik NICHT veraendern.
- VERBOTEN: Persona-CRUD, Sharing-Logik, User-Zuordnung veraendern
- MERGE: Hook nach `if group_ids:` Guard einfuegen (~Zeile 244). Mittel-hohes Merge-Risiko (14 Commits/3 Monate, Sharing-Features aktiv upstream)
- STATUS: Noch NICHT gepatcht. Wird in Phase 4g (ext-access) aktiviert.
- HINWEIS: `versioned_update_persona_access` nutzt `fetch_versioned_implementation` — EE-Override funktioniert NICHT (is_ee_version=false). Daher direkter Hook in FOSS-Funktion noetig.

## 12. `backend/onyx/db/document_set.py` — DocumentSet Gruppen-Zuordnung [RESERVIERT Phase 4g]
- ERLAUBT: In `make_doc_set_private()` den `NotImplementedError`-Block durch ext-Hook ersetzen (hinter `EXT_DOC_ACCESS_ENABLED` Flag + try/except). Bestehende Public/Private-Logik NICHT veraendern.
- VERBOTEN: DocumentSet-CRUD, Filterung, Sync-Logik veraendern
- MERGE: Hook vor `raise NotImplementedError` einfuegen (~Zeile 179). Niedriges Merge-Risiko (5 Commits/3 Monate, Funktion seit 2026-01-29 unveraendert)
- STATUS: Noch NICHT gepatcht. Wird in Phase 4g (ext-access) aktiviert.
- HINWEIS: Analog zu #11, gleicher Hook-Pattern.

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
