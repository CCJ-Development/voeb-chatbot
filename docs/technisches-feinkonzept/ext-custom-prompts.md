# Modulspezifikation: ext-prompts (Custom System Prompts)

**Dokumentstatus**: Implementiert
**Version**: 1.0
**Autor**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Datum**: 2026-03-09
**Status**: [ ] Entwurf | [ ] Review | [ ] Freigegeben | [x] Implementiert
**Prioritaet**: [x] Hoch | [ ] Kritisch | [ ] Normal | [ ] Niedrig

---

## 1. Uebersicht

| Feld | Wert |
|------|------|
| **Modulname** | Custom System Prompts |
| **Modul-ID** | `ext_prompts` |
| **Feature Flag** | `EXT_CUSTOM_PROMPTS_ENABLED` (existiert in `config.py`) |
| **Core-Aenderungen** | CORE #7 (`prompt_utils.py`), CORE #10 (`AdminSidebar.tsx`) |
| **Abhaengigkeiten** | Keine (ext-framework Basis genuegt) |

### Zweck

Ermoeglicht VoeB-Administratoren, **globale System-Prompt-Anweisungen** zentral zu verwalten, die bei JEDEM LLM-Aufruf dem System-Prompt vorangestellt werden. Typische Anwendungen: Compliance-Hinweise ("Keine Anlageberatung"), Tonalitaetsregeln ("Formelles Deutsch, Siezen"), DSGVO-Verweise, oder organisations-spezifischer Kontext ("Du bist ein Assistent des VoeB").

### Abgrenzung zu Onyx-Personas

Onyx hat bereits **per-Persona System Prompts** (Feld `persona.system_prompt`). Diese werden pro Agent/Persona individuell konfiguriert. ext-prompts ergaenzt dies um eine **globale Schicht**, die UEBER allen Personas liegt und IMMER angewendet wird — unabhaengig davon, welchen Agent der User gewaehlt hat.

```
┌──────────────────────────────────────────┐
│  ext-prompts: Globale VoeB-Anweisungen   │  ← PREPEND (unser Modul)
├──────────────────────────────────────────┤
│  Onyx Base System Prompt                 │  ← build_system_prompt()
│  (Datumskontext, User-Info, Tool-        │
│   Guidance, Citation-Guidance)           │
├──────────────────────────────────────────┤
│  Persona/Agent System Prompt             │  ← custom_agent_prompt (separates Message)
│  (Optional, pro Persona konfiguriert)    │
└──────────────────────────────────────────┘
```

### Im Umfang (v1.0)

- Globale System Prompts (gelten fuer alle Personas/Chats)
- CRUD-Admin-API (Erstellen, Lesen, Aktualisieren, Loeschen)
- Prioritaets-Reihenfolge (mehrere Prompts, sortiert angewendet)
- Kategorien zur Organisation (Compliance, Tonalitaet, Kontext, Anweisungen)
- Aktiv/Inaktiv-Toggle ohne Loeschen
- Preview-Endpoint (zusammengesetzter Prompt-Text)
- In-Memory-Cache mit konfigurierbarem TTL (kein DB-Call pro LLM-Aufruf)
- Admin-UI unter `/admin/ext-prompts`

### Nicht im Umfang (v1.0)

- Per-Persona Custom Prompts (Onyx hat das bereits nativ)
- Per-User Prompts (kommt ggf. mit ext-rbac in v2.0)
- Prompt-Versionierung / Rollback
- A/B-Testing von Prompts
- Token-Limit-Integration (ext-token zaehlt den Overhead automatisch mit)

---

## 2. Architektur

### Komponenten-Uebersicht

```
Admin-UI (/admin/ext-prompts)
    │
    ▼
FastAPI Router (ext.routers.prompts)
    │  GET/POST/PUT/DELETE /api/ext/prompts
    │  GET /api/ext/prompts/preview
    ▼
Service Layer (ext.services.prompt_manager)
    │  CRUD + Cache-Invalidierung
    │  get_cached_global_prompt() → In-Memory-Cache
    ▼
DB (ext_custom_prompts)
    │
    ▼
Core Hook (CORE #7: prompt_utils.py → build_system_prompt())
    │  try/except: get_cached_global_prompt()
    │  PREPEND vor Base System Prompt
    ▼
LLM-Aufruf (via llm_loop.py)
```

### Datenfluss (Chat-Request)

1. User sendet Nachricht im Chat
2. `process_message.py` orchestriert den Chat-Flow
3. `llm_loop.py` ruft `build_system_prompt()` auf (CORE #7)
4. **Hook in `build_system_prompt()`**: Laedt gecachten globalen Prompt-Text
5. Globaler Prompt wird dem Base System Prompt vorangestellt
6. Zusammengesetzter System-Prompt wird als System-Message an LLM gesendet
7. Persona-Prompt (falls vorhanden) wird als separates User-Message gesendet

### Datenfluss (Admin-CRUD)

1. Admin erstellt/aendert Prompt ueber UI → `PUT /api/ext/prompts/{id}`
2. Service-Layer aktualisiert DB
3. Service-Layer invalidiert In-Memory-Cache
4. Naechster LLM-Aufruf laedt frische Daten aus DB
5. Cache wird neu befuellt (TTL startet neu)

### Caching-Strategie

- **Cache-Typ**: Module-globaler `dict` mit Timestamp (kein Redis noetig)
- **TTL**: 60 Sekunden (konfigurierbar via `EXT_PROMPTS_CACHE_TTL_SECONDS`)
- **Invalidierung**: Explizit bei jeder Admin-CRUD-Operation
- **Fallback**: Bei Cache-Miss → DB-Query → Cache befuellen
- **Thread-Safety**: `threading.Lock` fuer Cache-Zugriff
- **Tenant-Kontext**: Cache-Refresh nutzt `get_session_with_current_tenant()` (aus `onyx.db.engine.sql_engine`). Im normalen LLM-Loop ist der Tenant immer gesetzt. Falls kein Tenant-Kontext vorhanden (Edge Case): try/except → leerer String, kein Crash.
- **Kein DB-Call in `build_system_prompt()`** wenn Cache warm (< 1ms Overhead)

---

## 3. Datenbankschema

### Tabelle: `ext_custom_prompts`

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Eindeutige ID |
| `name` | VARCHAR(100) | NOT NULL | Anzeigename fuer Admin-UI |
| `prompt_text` | TEXT | NOT NULL | Der eigentliche Prompt-Inhalt |
| `category` | VARCHAR(50) | NOT NULL, DEFAULT 'general' | Kategorie: `compliance`, `tone`, `context`, `instructions`, `general` |
| `priority` | INTEGER | NOT NULL, DEFAULT 100 | Sortierung: niedrigerer Wert = wird zuerst eingefuegt |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Aktiv/Inaktiv-Toggle |
| `created_at` | TIMESTAMP WITH TZ | NOT NULL, DEFAULT NOW() | Erstellungszeitpunkt |
| `updated_at` | TIMESTAMP WITH TZ | NOT NULL, DEFAULT NOW(), ON UPDATE NOW() | Letzte Aenderung |

### Indizes

```sql
-- Schnelle Abfrage aktiver Prompts, sortiert nach Prioritaet
CREATE INDEX idx_ext_custom_prompts_active_priority
  ON ext_custom_prompts(is_active, priority);
```

### Relationen

Keine Foreign Keys zu Onyx-Tabellen. Vollstaendig eigenstaendig.

### Migration

- Alembic-Migration in Onyx-Chain (wie ext-branding und ext-token)
- Revision-ID: generiert von Alembic
- `down_revision`: `b3e4a7d91f08` (ext-token, letztes Glied der Chain)
- Datei: `backend/alembic/versions/c7f2e8a3d105_ext_prompts_create_table.py`

---

## 4. API-Spezifikation

Alle Endpoints erfordern Admin-Auth (`current_admin_user`). Prefix: `/api/ext/prompts`

### Endpoint 1: `GET /api/ext/prompts`

**Beschreibung**: Liste aller Custom Prompts (aktive und inaktive)

**Response (200)**:
```json
[
  {
    "id": 1,
    "name": "Compliance-Grundregeln",
    "prompt_text": "Du darfst keine Anlageberatung geben...",
    "category": "compliance",
    "priority": 10,
    "is_active": true,
    "created_at": "2026-03-09T10:00:00Z",
    "updated_at": "2026-03-09T10:00:00Z"
  }
]
```

### Endpoint 2: `POST /api/ext/prompts`

**Beschreibung**: Neuen Custom Prompt erstellen

**Request Body** (`PromptCreate`):
```json
{
  "name": "Compliance-Grundregeln",
  "prompt_text": "Du darfst keine Anlageberatung geben. Verweise bei rechtlichen Fragen immer auf den Rechtsbereich.",
  "category": "compliance",
  "priority": 10,
  "is_active": true
}
```

**Validierung**:
- `name`: 1-100 Zeichen, nicht leer
- `prompt_text`: 1-10.000 Zeichen, nicht leer
- `category`: Einer von `compliance`, `tone`, `context`, `instructions`, `general`
- `priority`: 0-1000
- `is_active`: Boolean, Default `true`

**Response (201)**: Erstellter Prompt (Schema: `PromptResponse`)

### Endpoint 3: `PUT /api/ext/prompts/{prompt_id}`

**Beschreibung**: Bestehenden Prompt aktualisieren

**Path Parameter**: `prompt_id` (int)

**Request Body** (`PromptUpdate`):
```json
{
  "name": "Compliance-Grundregeln v2",
  "prompt_text": "Aktualisierter Text...",
  "category": "compliance",
  "priority": 10,
  "is_active": true
}
```

Alle Felder optional (Partial Update). Mindestens ein Feld muss gesetzt sein.

**Response (200)**: Aktualisierter Prompt (Schema: `PromptResponse`)

**Fehlercodes**:
- 404: Prompt mit `prompt_id` nicht gefunden

### Endpoint 4: `DELETE /api/ext/prompts/{prompt_id}`

**Beschreibung**: Prompt dauerhaft loeschen

**Response**: 204 No Content

**Fehlercodes**:
- 404: Prompt mit `prompt_id` nicht gefunden

### Endpoint 5: `GET /api/ext/prompts/preview`

**Beschreibung**: Zeigt den zusammengesetzten Text aller aktiven Prompts (in Prioritaets-Reihenfolge)

**Response (200)**:
```json
{
  "assembled_text": "## Compliance\nDu darfst keine Anlageberatung geben...\n\n## Tonalitaet\nAntworte immer in formellem Deutsch...",
  "active_count": 3,
  "total_count": 5
}
```

### Fehlerbehandlung

| HTTP-Status | Grund | Aktion |
|-------------|-------|--------|
| 200 | Erfolg | — |
| 201 | Erstellt | — |
| 204 | Geloescht | — |
| 400 | Validierungsfehler (leerer Name, zu langer Text, ungueltige Kategorie) | Fehlermeldung im Body |
| 401 | Nicht authentifiziert | Login erforderlich |
| 403 | Kein Admin | Nur Admins duerfen Prompts verwalten |
| 404 | Prompt nicht gefunden / Feature Flag deaktiviert (Router nicht registriert) | — |
| 500 | Interner Fehler | Logging, Onyx-Betrieb nicht beeintraechtigt |

---

## 5. Pydantic Schemas

### `ext/schemas/prompts.py`

```python
class PromptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    prompt_text: str = Field(min_length=1, max_length=10_000)
    category: str = Field(default="general", pattern="^(compliance|tone|context|instructions|general)$")
    priority: int = Field(default=100, ge=0, le=1000)
    is_active: bool = True

class PromptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    prompt_text: str | None = Field(default=None, min_length=1, max_length=10_000)
    category: str | None = Field(default=None, pattern="^(compliance|tone|context|instructions|general)$")
    priority: int | None = Field(default=None, ge=0, le=1000)
    is_active: bool | None = None

class PromptResponse(BaseModel):
    id: int
    name: str
    prompt_text: str
    category: str
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class PromptPreviewResponse(BaseModel):
    assembled_text: str
    active_count: int
    total_count: int
```

---

## 6. Betroffene Core-Dateien

### CORE #7: `backend/onyx/chat/prompt_utils.py`

**Was wird geaendert**: Hook in `build_system_prompt()`, eingefuegt VOR dem `if include_all_guidance:`-Block (ca. Zeile 229), um BEIDE Return-Pfade abzudecken.

**Hintergrund**: `build_system_prompt()` hat **zwei `return`-Statements**:
- Zeile 243: Early Return im `if include_all_guidance:`-Branch (genutzt von `calculate_reserved_tokens()`)
- Zeile 291: Finaler Return (genutzt vom normalen Chat-Flow in `llm_loop.py`)

Der Hook muss VOR dem ersten Branch sitzen, damit:
1. Der ext-prompt-Text bei BEIDEN Code-Pfaden eingefuegt wird
2. `calculate_reserved_tokens()` den ext-prompt-Overhead korrekt mitzaehlt (sonst Token-Estimation zu niedrig → Context-Window-Overflow-Risiko)

**Aenderung** (~10 Zeilen, eingefuegt nach `system_prompt += user_info_section` / vor `if should_append_citation_guidance:`):
```python
    system_prompt += user_info_section

    # ext-prompts: Prepend custom global prompts if configured
    try:
        from ext.config import EXT_CUSTOM_PROMPTS_ENABLED
        if EXT_CUSTOM_PROMPTS_ENABLED:
            from ext.services.prompt_manager import get_cached_global_prompt
            ext_prompt = get_cached_global_prompt()
            if ext_prompt:
                system_prompt = ext_prompt + "\n\n" + system_prompt
    except ImportError:
        pass
    except Exception:
        import logging
        logging.getLogger("ext").error("ext-prompts hook failed", exc_info=True)

    # Append citation guidance after company context ...
```

**Warum hier und nicht anderswo**:
- `build_system_prompt()` erzeugt den Base System Prompt — der richtige Ort fuer globale Anweisungen
- Platzierung VOR dem `include_all_guidance`-Branch deckt beide Return-Pfade ab
- Wird auch von `calculate_reserved_tokens()` durchlaufen → Token-Estimation korrekt
- Wird nur aufgerufen wenn `replace_base_system_prompt=False` (Standard) — respektiert Admin-Entscheidung
- Verwendet In-Memory-Cache → kein DB-Call, < 1ms Overhead
- Standard ext-Hook-Pattern (try/except, Feature Flag, ImportError-Safe)

**Verhalten bei `replace_base_system_prompt=True`**:
- `build_system_prompt()` wird NICHT aufgerufen (siehe `llm_loop.py:674-684`)
- Globale ext-prompts werden NICHT angewendet
- Dies ist beabsichtigt: Admin hat bewusst den gesamten System Prompt ersetzt
- Dokumentiert als bekannte Einschraenkung

### CORE #10: `web/src/sections/sidebar/AdminSidebar.tsx`

**Was wird geaendert**: Neuer Sidebar-Link "System Prompts" in der Settings-Section.

**Aenderung** (~3 Zeilen):
```typescript
// ext-prompts: System Prompts management when VÖB extension is active
...(settings?.enterpriseSettings && !hasSubscription
  ? [{ name: "System Prompts", icon: SvgFileText, link: "/admin/ext-prompts" }]
  : []),
```

Eingefuegt nach dem Token Usage Link (nach Zeile 165), vor dem Billing-Block.

**Import ergaenzen**: `SvgFileText` aus `@opal/icons` (gleicher Import-Pfad wie `SvgPaintBrush` und `SvgActivity` in AdminSidebar.tsx Zeile 22). Icon existiert in `web/lib/opal/src/icons/file-text.tsx`.

---

## 7. Feature Flag Verhalten

### Flag: `EXT_CUSTOM_PROMPTS_ENABLED`

**Default**: `false`

**Wenn aktiviert** (`EXT_ENABLED=true` + `EXT_CUSTOM_PROMPTS_ENABLED=true`):
- Router `/api/ext/prompts` wird registriert (in `ext/routers/__init__.py`)
- Admin-UI unter `/admin/ext-prompts` ist erreichbar
- Sidebar-Link wird angezeigt (via enterpriseSettings-Check)
- Hook in `build_system_prompt()` laedt und prepended aktive Prompts
- DB-Tabelle `ext_custom_prompts` wird via Alembic-Migration erstellt

**Wenn deaktiviert** (Default):
- Router wird nicht registriert → Endpoints liefern 404
- Hook in `build_system_prompt()` wird uebersprungen (Flag-Check)
- Kein DB-Zugriff, kein Overhead
- Sidebar-Link wird nicht angezeigt
- **Onyx-Verhalten: 100% unveraendert**

### Umgebungsvariablen

| Variable | Typ | Pflicht | Default | Beschreibung |
|----------|-----|---------|---------|-------------|
| `EXT_CUSTOM_PROMPTS_ENABLED` | bool | Nein | `false` | Feature-Flag (AND-gated mit `EXT_ENABLED`) |
| `EXT_PROMPTS_CACHE_TTL_SECONDS` | int | Nein | `60` | Cache-Lebensdauer in Sekunden |

---

## 8. Service-Layer

### `ext/services/prompt_manager.py`

**Funktionen**:

| Funktion | Beschreibung |
|----------|-------------|
| `get_all_prompts(db_session)` | Alle Prompts (aktiv + inaktiv), sortiert nach Prioritaet |
| `get_prompt_by_id(db_session, prompt_id)` | Einzelner Prompt oder None |
| `create_prompt(db_session, data)` | Prompt erstellen + Cache invalidieren |
| `update_prompt(db_session, prompt_id, data)` | Prompt aktualisieren + Cache invalidieren |
| `delete_prompt(db_session, prompt_id)` | Prompt loeschen + Cache invalidieren |
| `get_assembled_prompt_text(db_session)` | Alle aktiven Prompts zusammensetzen (fuer Preview) |
| `get_cached_global_prompt()` | **Cached**: Zusammengesetzter Text aller aktiven Prompts |
| `invalidate_cache()` | Cache explizit invalidieren |

**Prompt-Assembly-Logik**:
1. Alle aktiven Prompts laden, sortiert nach `priority` ASC
2. Pro Prompt: Text trimmen
3. Alle Texte mit `\n\n` verbinden
4. Ergebnis cachen

**Beispiel-Output**:
```
Du darfst keine Anlageberatung geben. Verweise bei rechtlichen Fragen immer auf den Rechtsbereich des VoeB.

Antworte immer in formellem Deutsch. Verwende die Hoeflichkeitsform (Siezen). Vermeide umgangssprachliche Ausdruecke.

Du bist ein KI-Assistent des Bundesverbands Oeffentlicher Banken Deutschlands (VoeB). Deine Aufgabe ist es, Mitarbeiter bei ihrer taeglichen Arbeit zu unterstuetzen.
```

---

## 9. Frontend

### Admin-Seite: `/admin/ext-prompts`

**Location**: `web/src/ext/pages/admin/prompts/page.tsx`

**Funktionalitaet**:
- Tabelle aller Prompts (Name, Kategorie, Prioritaet, Status, Aktionen)
- Toggle Aktiv/Inaktiv direkt in der Tabelle
- Modal/Formular fuer Erstellen/Bearbeiten:
  - Name (Textfeld, max 100 Zeichen)
  - Kategorie (Dropdown: Compliance, Tonalitaet, Kontext, Anweisungen, Allgemein)
  - Prioritaet (Nummernfeld, 0-1000)
  - Prompt-Text (Textarea, max 10.000 Zeichen)
  - Aktiv-Checkbox
- Loeschen mit Bestaetigung
- Preview-Button: Zeigt zusammengesetzten Text aller aktiven Prompts
- Hinweis-Box: Erklaerung was globale Prompts sind und wie sie wirken

**Pattern**: Analog zu `web/src/ext/pages/admin/branding/page.tsx` und `web/src/ext/pages/admin/token/page.tsx`.

**Routing**: `web/src/app/admin/ext-prompts/page.tsx` als Next.js Page (importiert ext-Komponente).

---

## 10. Tests

### Unit Tests (`backend/ext/tests/test_prompts.py`)

| Test | Beschreibung |
|------|-------------|
| `test_create_prompt_valid` | Prompt mit allen Feldern erstellen |
| `test_create_prompt_defaults` | Prompt mit nur Pflichtfeldern (category=general, priority=100) |
| `test_create_prompt_invalid_name_empty` | Leerer Name → ValidationError |
| `test_create_prompt_invalid_name_too_long` | Name > 100 Zeichen → ValidationError |
| `test_create_prompt_invalid_text_empty` | Leerer Text → ValidationError |
| `test_create_prompt_invalid_text_too_long` | Text > 10.000 Zeichen → ValidationError |
| `test_create_prompt_invalid_category` | Ungueltige Kategorie → ValidationError |
| `test_create_prompt_invalid_priority_negative` | Priority < 0 → ValidationError |
| `test_create_prompt_invalid_priority_too_high` | Priority > 1000 → ValidationError |
| `test_update_prompt_partial` | Nur Name aendern, Rest bleibt |
| `test_delete_prompt` | Prompt loeschen, danach 404 |
| `test_assemble_prompt_text_ordering` | Prompts nach Prioritaet sortiert |
| `test_assemble_prompt_text_only_active` | Inaktive Prompts werden ignoriert |
| `test_assemble_prompt_text_empty` | Keine aktiven Prompts → leerer String |
| `test_cache_returns_cached_value` | Zweiter Aufruf ohne DB-Query |
| `test_cache_invalidation` | Nach CRUD-Operation wird Cache invalidiert |
| `test_cache_ttl_expiry` | Nach TTL wird DB erneut abgefragt |
| `test_schema_validation` | Pydantic Schemas (Create, Update, Response) |

### Feature Flag Tests

| Test | Beschreibung |
|------|-------------|
| `test_flag_disabled_no_router` | Flag=false → Endpoints nicht registriert |
| `test_flag_disabled_no_hook` | Flag=false → build_system_prompt() unveraendert |
| `test_flag_enabled_hook_active` | Flag=true → Prompt wird prepended |
| `test_flag_enabled_no_active_prompts` | Flag=true, keine aktiven Prompts → kein Prepend |

### Edge Cases

| Test | Beschreibung |
|------|-------------|
| `test_ext_module_not_installed` | ImportError → Onyx laeuft normal |
| `test_db_error_in_cache_refresh` | DB-Fehler → alter Cache-Wert oder leerer String |
| `test_concurrent_cache_access` | Thread-Safety des Cache |
| `test_prompt_with_special_characters` | Unicode, Umlaute, Sonderzeichen |
| `test_very_long_assembled_prompt` | 10 Prompts a 10.000 Zeichen |
| `test_replace_base_system_prompt_true` | Hook wird nicht aufgerufen |

---

## 11. Datei-Uebersicht

### Neue Dateien

| Datei | Beschreibung |
|-------|-------------|
| `backend/ext/models/prompts.py` | SQLAlchemy Model: `ExtCustomPrompt` |
| `backend/ext/schemas/prompts.py` | Pydantic Schemas: Create, Update, Response, Preview |
| `backend/ext/services/prompt_manager.py` | CRUD + Caching + Assembly-Logik |
| `backend/ext/routers/prompts.py` | FastAPI Router: 5 Endpoints |
| `backend/ext/tests/test_prompts.py` | Unit Tests |
| `backend/alembic/versions/xxxx_ext_prompts.py` | Alembic Migration |
| `web/src/ext/pages/admin/prompts/page.tsx` | Admin-UI Komponente |
| `web/src/app/admin/ext-prompts/page.tsx` | Next.js Route |

### Geaenderte Dateien

| Datei | Aenderung | Zeilen |
|-------|-----------|--------|
| `backend/onyx/chat/prompt_utils.py` (CORE #7) | Hook: get_cached_global_prompt() + prepend | ~10 |
| `web/src/sections/sidebar/AdminSidebar.tsx` (CORE #10) | Sidebar-Link "System Prompts" | ~3 |
| `backend/ext/routers/__init__.py` | Router-Registrierung fuer ext-prompts | ~8 |
| `deployment/docker_compose/env.template` | `EXT_CUSTOM_PROMPTS_ENABLED` Doku (bereits vorhanden) | 0 |

### Core-Patches (kumulativ)

| Core-Datei | Bestehende Patches | Neuer Patch |
|------------|-------------------|-------------|
| `prompt_utils.py` | Keiner | ext-prompts Hook (~10 Zeilen) |
| `AdminSidebar.tsx` | ext-branding + ext-token | + ext-prompts Link (~3 Zeilen) |

---

## 12. Logging

Format: `[EXT-PROMPTS] {message}`

| Level | Event | Beispiel |
|-------|-------|---------|
| INFO | Router registriert | `Extension prompts router registered` |
| INFO | Prompt erstellt | `Prompt created: id=1, name='Compliance'` |
| INFO | Prompt aktualisiert | `Prompt updated: id=1` |
| INFO | Prompt geloescht | `Prompt deleted: id=1` |
| DEBUG | Cache-Hit | `Cache hit, TTL remaining: 45s` |
| DEBUG | Cache-Refresh | `Cache refreshed: 3 active prompts, 847 chars` |
| ERROR | Hook-Fehler | `ext-prompts hook failed` (mit exc_info) |

**DSGVO**: Keine personenbezogenen Daten in Logs. Nur Prompt-IDs und Namen.

---

## 13. Performance

| Anforderung | Zielwert |
|------------|---------|
| Hook-Overhead pro LLM-Aufruf (Cache warm) | < 1 ms |
| Admin-API (GET/POST/PUT/DELETE) | < 100 ms |
| Cache-Refresh (DB-Query) | < 50 ms |
| Max. Prompt-Speicher im Cache | ~100 KB (10 Prompts a 10.000 Zeichen) |

Kein Redis noetig. Module-globaler dict-Cache reicht fuer Single-Instance-Deployment.

---

## 14. Offene Punkte

- [x] **[OPEN-1]** ~~Icon fuer AdminSidebar~~ → **Geloest**: `SvgFileText` aus `@opal/icons` (existiert in `web/lib/opal/src/icons/file-text.tsx`).

- [x] **[OPEN-2]** ~~Sollen globale Prompts auch bei `replace_base_system_prompt=True` greifen?~~ → **Entscheidung: Nein.** Wer den System Prompt komplett ersetzt, hat bewusst die Kontrolle uebernommen. ext-prompts greifen nur im Standard-Modus. Bei Bedarf in v2.0 als Option.

- [x] **[OPEN-3]** ~~Max. Anzahl Prompts begrenzen?~~ → **Entscheidung: Soft-Limit.** Max. 20 aktive Prompts ODER 50.000 Zeichen Gesamtlaenge. Kein Hard-Block — Admin-UI zeigt Warnung wenn Limit ueberschritten wird (gelber Hinweis-Banner). API akzeptiert weiterhin, loggt aber Warning.

---

## 15. Approvals

| Rolle | Name | Datum | Status |
|------|------|-------|--------|
| Technical Lead | Nikolaj Ivanov | TBD | __ |

---

## Revisions-Historie

| Version | Datum | Autor | Aenderungen |
|---------|-------|-------|-----------|
| 0.1 | 2026-03-09 | Nikolaj Ivanov | Initialer Entwurf |
| 0.2 | 2026-03-09 | Nikolaj Ivanov | Code-Verifikation: Hook-Platzierung korrigiert (2 Return-Statements), Icon-Import-Pfad korrigiert (@opal/icons), Token-Estimation-Problem adressiert, Tenant-Kontext Edge Case dokumentiert |
| 1.0 | 2026-03-09 | Nikolaj Ivanov | Implementiert. Migration `c7f2e8a3d105`. 29 Unit Tests bestanden. Backend-API funktional, Frontend Admin-UI erstellt. |
