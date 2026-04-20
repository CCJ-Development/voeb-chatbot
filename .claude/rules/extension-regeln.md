---
paths:
  - "backend/ext/**"
  - "web/src/ext/**"
---

# Extension-Code Regeln

## Backend (`backend/ext/`)

Aktueller Stand (Phase 4i, alle Module) — alle Verzeichnisse befuellt:

```
backend/ext/
  __init__.py                ← Package-Marker
  config.py                  ← Feature Flags (9 Module: EXT_ENABLED Master-Switch + 8 Modul-Flags + i18n Frontend-only)
  routers/                   ← FastAPI Router (health, branding, token, prompts, analytics, rbac, doc_access, audit)
  models/                    ← SQLAlchemy Models (branding, token, prompts, audit)
  schemas/                   ← Pydantic Schemas (branding, token, prompts, analytics, rbac, doc_access, audit)
  services/                  ← Business Logic (branding, token_tracker, prompt_manager, analytics, rbac, access, audit)
  tests/                     ← pytest Tests (config, health, branding, token, prompts, analytics, rbac, doc_access, audit)
  tasks/                     ← Celery Tasks (doc_access_sync, audit_ip_anonymize)
  _core_originals/           ← Backups der Core-Dateien (.original + .patch)
```

## Frontend (`web/src/ext/`)

Befuellt seit Phase 4b (ext-branding):

```
web/src/ext/
  components/                ← Eigene React-Komponenten
  pages/                     ← Eigene Seiten (/ext/admin/...)
  hooks/                     ← Eigene React Hooks
  lib/api.ts                 ← Eigener API-Client (/api/ext/...)
  styles/                    ← Eigene Styles (ext- Prefix fuer Klassen)
  __tests__/                 ← Frontend-Tests
```

## Import-Regeln
- ext → Onyx: ERLAUBT (read-only)
- Onyx → ext: NUR in 16 Core-Dateien (einzige Brücke)
- Sichere Imports: `onyx.db.models`, `onyx.db.engine`, `onyx.auth.users`, `onyx.configs.*`, `onyx.server.schemas`
- Vorsicht: `onyx.llm.*`, `onyx.chat.*`, `onyx.indexing.*` (Git-History prüfen)
- Verboten: `onyx.utils.internal`, `onyx.cli`, `onyx.background`

## Feature Flags
```python
# backend/ext/config.py
EXT_ENABLED = os.getenv("EXT_ENABLED", "true").lower() == "true"
EXT_BRANDING_ENABLED = EXT_ENABLED and os.getenv("EXT_BRANDING_ENABLED", "false").lower() == "true"
EXT_TOKEN_LIMITS_ENABLED = EXT_ENABLED and os.getenv("EXT_TOKEN_LIMITS_ENABLED", "false").lower() == "true"
EXT_CUSTOM_PROMPTS_ENABLED = EXT_ENABLED and os.getenv("EXT_CUSTOM_PROMPTS_ENABLED", "false").lower() == "true"
EXT_ANALYTICS_ENABLED = EXT_ENABLED and os.getenv("EXT_ANALYTICS_ENABLED", "false").lower() == "true"
EXT_RBAC_ENABLED = EXT_ENABLED and os.getenv("EXT_RBAC_ENABLED", "false").lower() == "true"
EXT_DOC_ACCESS_ENABLED = EXT_ENABLED and os.getenv("EXT_DOC_ACCESS_ENABLED", "false").lower() == "true"
EXT_AUDIT_ENABLED = EXT_ENABLED and os.getenv("EXT_AUDIT_ENABLED", "false").lower() == "true"
# i18n: NEXT_PUBLIC_EXT_I18N_ENABLED (Frontend-only, kein Backend-Flag)
```
Flag=false → Router nicht registriert, Hooks feuern nicht, keine DB-Queries. Onyx läuft 100% normal.

## Frontend-Regeln (Merge-Konflikt-Prävention)
- NIEMALS bestehende Onyx-Komponenten/CSS editieren
- Wrapper-Pattern: ExtHeader wraps Header, Fallback auf Original
- Eigene Routes unter /ext/ Prefix
- Tailwind + CSS Variables (--ext-*)
- Klassen-Prefix: ext-
