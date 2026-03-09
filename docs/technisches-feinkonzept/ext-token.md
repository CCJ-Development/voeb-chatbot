# Modulspezifikation: ext-token (LLM Usage Tracking + Token Limits)

**Dokumentstatus**: Freigegeben
**Version**: 0.3
**Autor**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Datum**: 2026-03-09
**Status**: [ ] Entwurf | [ ] Review | [x] Freigegeben
**Prioritaet**: [x] Hoch | [ ] Kritisch | [ ] Normal | [ ] Niedrig

---

## Moduluebersicht

| Feld | Wert |
|------|------|
| **Modulname** | LLM Usage Tracking + Token Limits |
| **Modul-ID** | `ext_token` |
| **Version** | 0.2.0 |
| **Phase** | 4c |
| **Feature Flag** | `EXT_TOKEN_LIMITS_ENABLED` (existiert in `backend/ext/config.py:13-16`) |
| **Abhaengigkeiten** | Phase 4a Extension Framework ✅ |

---

## Zweck und Umfang

### Zweck

Der VoeB-Kunde braucht Transparenz und Kontrolle ueber den LLM-Token-Verbrauch. Das Modul loggt jeden LLM-Aufruf granular (User, Modell, Prompt-/Completion-Tokens, Zeitpunkt), bietet ein Admin-Dashboard zur Auswertung und ermoeglicht Per-User Token-Limits. Dies ist essentiell fuer Kostenkontrolle und Compliance im Bankensektor.

### Im Umfang enthalten

- Backend: Hook in `multi_llm.py` (CORE #2) fuer granulares Token-Logging nach jedem LLM-Call
- Backend: REST-API fuer Usage-Abfragen (Aggregationen nach User, Modell, Zeitraum)
- Backend: REST-API fuer Per-User Token-Limits (CRUD)
- Backend: Per-User Limit-Enforcement (Pruefung vor LLM-Call, 429 bei Ueberschreitung)
- Datenbank: `ext_token_usage` Tabelle + Alembic-Migration
- Datenbank: `ext_token_user_limit` Tabelle fuer Per-User Limits + Alembic-Migration
- Frontend: Admin-Seite `/admin/ext-token` mit Usage-Dashboard
- Feature-Flag-Gating: Alles hinter `EXT_TOKEN_LIMITS_ENABLED`

### Nicht im Umfang

- Per-Gruppen Token-Limits (kommt mit ext-rbac, Phase 4f)
- Kostenberechnung in Euro/Dollar (Onyx FOSS hat bereits `calculate_llm_cost_cents()` — wir tracken nur Tokens)
- Echtzeit-Warnungen im Chat-Interface (spaetere Erweiterung)
- Export als CSV/PDF (spaetere Erweiterung)
- Token-Schaetzung VOR dem LLM-Call (zu ungenau, wir loggen die tatsaechlichen Tokens aus der LLM-Response)

### Abhaengige Module / Prerequisites

- [x] Phase 4a: Extension Framework Basis (erledigt)
- [x] Onyx FOSS laufende Installation
- [ ] Keine weiteren Abhaengigkeiten

---

## Kritische Architekturentscheidung: Aufbau auf FOSS-Infrastruktur

### Erkenntnis aus Tiefenanalyse

Onyx FOSS hat bereits umfangreiche Token-Infrastruktur. Wir bauen gezielt darauf auf, ohne sie zu duplizieren:

**Was FOSS bereits liefert (nutzen wir, aendern wir NICHT):**

| FOSS-Feature | Datei | Was es tut |
|-------------|-------|-----------|
| `Usage` Klasse | `llm/model_response.py:41-46` | `prompt_tokens`, `completion_tokens`, `total_tokens` aus LLM-Response |
| `_track_llm_cost()` | `llm/multi_llm.py:315-355` | Cost-Tracking (pro Tenant, pro Woche) |
| `TokenRateLimit` Model | `db/models.py:3952-3965` | DB-Tabelle fuer Rate Limits (GLOBAL/USER Scope) |
| `ChatMessage.token_count` | `db/models.py:2495+` | Token-Count pro Chat-Nachricht |
| Global Rate Limit Enforcement | `server/query_and_chat/token_limit.py` | 429-Error bei globalem Limit |
| Admin-Seite `/admin/token-rate-limits` | `web/src/app/admin/token-rate-limits/` | CRUD fuer Global Token Rate Limits |
| `LLMUserIdentity` | `llm/interfaces.py:17-19` | `user_id` + `session_id` — bereits an invoke/stream durchgereicht |
| `LiteLLM` Token-Info | `llm/multi_llm.py:663,742` | Automatische Token-Counts in jeder Response (Streaming + Non-Streaming) |

**Was FOSS NICHT kann (bauen wir in ext-token):**

| Feature | Warum fehlt es |
|---------|---------------|
| Granulares Usage-Log pro User + Modell | FOSS tracked nur aggregiert pro Tenant (TenantUsage) |
| Per-User Token-Limits + Enforcement | Nur in EE (backend/ee/ ist leer) |
| Usage-Dashboard mit Aufschluesselung | Keine UI im FOSS |
| API-Endpoints fuer Usage-Daten | Keine oeffentliche Usage-API im FOSS |

**Hybrid-Ansatz (bestehende Seite + neue Seite):**

| Bereich | Wo | Begruendung |
|---------|-----|-------------|
| Global Token Rate Limits setzen | Bestehende FOSS-Seite `/admin/token-rate-limits` | Funktioniert, kein Code noetig |
| Usage-Dashboard + Per-User Limits | Neue Seite `/admin/ext-token` in `web/src/ext/` | "Extend don't modify", zero Upstream-Konflikte |

---

## Architektur

### Komponenten-Uebersicht

```
┌─────────────────────────────────────────────────────────────┐
│                   Onyx Chat Interface                        │
│              (User sendet Chat-Nachricht)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  FOSS: check_token_rate_limits()                            │
│  (FastAPI Dependency — prueft Global Limits)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  multi_llm.py invoke() / stream()                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EXT HOOK (vor LLM-Call):                            │    │
│  │  ext_check_user_token_limit(user_id, model)          │    │
│  │  → 429 wenn Per-User Limit ueberschritten            │    │
│  └────────────────────┬────────────────────────────────┘    │
│                       │                                      │
│                       ↓                                      │
│  ┌───────────────────────────────────────────────┐          │
│  │  LiteLLM → Provider API → Response mit Usage   │          │
│  └────────────────────┬──────────────────────────┘          │
│                       │                                      │
│                       ↓                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FOSS: _track_llm_cost(usage)                        │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EXT HOOK (nach LLM-Call):                           │    │
│  │  ext_log_token_usage(user_id, model, usage)          │    │
│  │  → INSERT in ext_token_usage                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ext_token_usage (NEU — Logging)                      │   │
│  │  user_id | model_name | prompt_tokens |               │   │
│  │  completion_tokens | total_tokens | created_at        │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ext_token_user_limit (NEU — Per-User Limits)         │   │
│  │  user_id | token_budget | period_hours | enabled      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Admin-Dashboard (web/src/ext/)                              │
│  /admin/ext-token                                            │
│  ┌─────────┬──────────────┬────────────────┬──────────┐     │
│  │ Ueber-  │ Per-User     │ Per-Modell     │ User     │     │
│  │ sicht   │ Breakdown    │ Breakdown      │ Limits   │     │
│  └─────────┴──────────────┴────────────────┴──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Datenfluss

**Logging (nach jedem LLM-Call):**
1. LLM-Call completed → `invoke()` oder `stream()` in `multi_llm.py`
2. FOSS: `_track_llm_cost(usage)` — speichert Cost in `TenantUsage`
3. EXT HOOK: `ext_log_token_usage(user_id, model, usage)` — speichert in `ext_token_usage`
4. Hook ist fire-and-forget, Exception wird geloggt aber bricht Onyx nie

**Enforcement (vor jedem LLM-Call):**
1. Chat-Request kommt an
2. FOSS: `check_token_rate_limits()` — prueft Global Limits (Dependency auf Chat-Endpoint)
3. In `multi_llm.py` VOR `_completion()`: EXT HOOK prueft Per-User Limit
4. Wenn User-Limit ueberschritten: `HTTPException(429)` mit aussagekraeftiger Meldung
5. Wenn unter Limit: LLM-Call normal durchfuehren

**Dashboard-Abfrage:**
1. Admin oeffnet `/admin/ext-token`
2. Frontend fetcht `GET /api/ext/token/usage/summary`
3. Backend aggregiert aus `ext_token_usage` (GROUP BY user/model/time)
4. Dashboard zeigt Grafiken + Tabellen

---

## Datenbankschema

### Tabelle: `ext_token_usage`

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-increment ID |
| `user_id` | UUID | FK → user(id), INDEX, NULLABLE | User der den LLM-Call ausgeloest hat. NULL bei System-Calls (Indexing, Background) |
| `model_name` | VARCHAR(255) | NOT NULL, INDEX | Modell-Identifier (z.B. `openai/gpt-oss-120b`) |
| `prompt_tokens` | INTEGER | NOT NULL, DEFAULT 0 | Input-Tokens des LLM-Calls |
| `completion_tokens` | INTEGER | NOT NULL, DEFAULT 0 | Output-Tokens des LLM-Calls |
| `total_tokens` | INTEGER | NOT NULL, DEFAULT 0 | Summe (prompt + completion) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW(), INDEX | Zeitpunkt des LLM-Calls |

**Hinweis**: Kein `group_id` — wird spaeter per ALTER TABLE + Migration ergaenzt wenn ext-rbac implementiert wird.

### Tabelle: `ext_token_user_limit`

Per-User Token-Limits. **Eigene Tabelle, NICHT die FOSS `token_rate_limit` Tabelle** (siehe "Korrektur v0.2" unten).

| Spalte | Typ | Constraints | Beschreibung |
|--------|-----|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-increment ID |
| `user_id` | UUID | FK → user(id) ON DELETE CASCADE, NOT NULL, UNIQUE | Der User fuer den das Limit gilt |
| `token_budget` | INTEGER | NOT NULL, CHECK > 0 | Budget in Tausenden (konsistent mit FOSS `TOKEN_BUDGET_UNIT = 1_000`) |
| `period_hours` | INTEGER | NOT NULL, CHECK > 0 | Zeitfenster in Stunden (z.B. 168 = 1 Woche) |
| `enabled` | BOOLEAN | NOT NULL, DEFAULT TRUE | Limit aktiv/inaktiv |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Erstellt am |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Letzte Aenderung |

**UNIQUE Constraint auf `user_id`**: Jeder User hat maximal EIN aktives Limit. Mehrere Limits pro User sind nicht vorgesehen (Vereinfachung fuer v1.0).

#### Korrektur v0.2: Warum NICHT die FOSS `token_rate_limit` Tabelle?

Die v0.1 Spec behauptete, wir koennten die FOSS-Tabelle `token_rate_limit` mit `scope=USER` fuer Per-User Limits nutzen. **Das ist technisch falsch:**

1. Die FOSS `token_rate_limit` Tabelle hat **KEINE `user_id` Spalte** — sie kennt nur `scope` (GLOBAL/USER/USER_GROUP), `token_budget` und `period_hours`
2. `insert_user_token_rate_limit()` erstellt ein Limit vom **Typ** "USER", bindet es aber **NICHT an einen spezifischen User**
3. Es gibt keine `TokenRateLimit__User` Join-Tabelle (nur `TokenRateLimit__UserGroup` fuer Gruppen)
4. Die FOSS `_check_token_rate_limits()` Funktion prueft NUR `scope=GLOBAL` — User-Limits werden von FOSS komplett ignoriert

**Konsequenz:** Wir brauchen eine eigene `ext_token_user_limit` Tabelle mit expliziter `user_id` FK. Eigene CRUD-Operationen in `ext/services/token_tracker.py`.

### Indizes

```sql
-- ext_token_usage Indizes
CREATE INDEX idx_ext_token_usage_user_id ON ext_token_usage(user_id);
CREATE INDEX idx_ext_token_usage_model ON ext_token_usage(model_name);
CREATE INDEX idx_ext_token_usage_created_at ON ext_token_usage(created_at);

-- Composite: Per-User-Verbrauch in Zeitfenster (Rate Limit Enforcement)
CREATE INDEX idx_ext_token_usage_user_time ON ext_token_usage(user_id, created_at);

-- ext_token_user_limit Indizes
-- user_id hat UNIQUE Constraint → impliziter Index
```

### Relationen

```
ext_token_usage (many) ──FK──> user (one)         [NULLABLE: System-Calls haben keinen User]
ext_token_user_limit (one) ──FK──> user (one)     [NOT NULL, UNIQUE: 1 Limit pro User]
```

**FOSS-Tabellen:** `token_rate_limit` und `ChatMessage` werden nur GELESEN (fuer Kompatibilitaet), nicht beschrieben.

### Migration

- Alembic Migration in Onyx's `backend/alembic/versions/` (Pattern von ext-branding uebernommen: `ff7273065d0d_ext_branding_...`)
- Revision-ID: wird bei Implementierung generiert
- Erstellt: `ext_token_usage` + `ext_token_user_limit` Tabellen + Indizes
- Down-Migration: `DROP TABLE ext_token_user_limit; DROP TABLE ext_token_usage;`

---

## API-Spezifikation

### Endpoints

Alle Endpoints unter Prefix `/api/ext/token/` — erfordern Admin-Auth.

#### Endpoint 1: `GET /api/ext/token/usage/summary`

**Beschreibung**: Aggregierte Usage-Statistiken fuer das Dashboard.

**Authentifizierung**: `current_admin_user` (Onyx Admin-Auth)

**Query Parameter**:

| Parameter | Typ | Erforderlich | Beschreibung |
|-----------|-----|-------------|-------------|
| `period_hours` | int | Nein (default: 168 = 1 Woche) | Zeitfenster fuer Aggregation |
| `user_id` | UUID | Nein | Filter auf bestimmten User |
| `model_name` | string | Nein | Filter auf bestimmtes Modell |

**Response (200)**:

```json
{
  "period_hours": 168,
  "total_prompt_tokens": 1250000,
  "total_completion_tokens": 340000,
  "total_tokens": 1590000,
  "total_requests": 847,
  "by_user": [
    {
      "user_id": "550e8400-...",
      "user_email": "max.mustermann@voeb.de",
      "total_tokens": 450000,
      "total_requests": 230
    }
  ],
  "by_model": [
    {
      "model_name": "openai/gpt-oss-120b",
      "total_tokens": 980000,
      "total_requests": 520
    }
  ]
}
```

#### Endpoint 2: `GET /api/ext/token/usage/timeseries`

**Beschreibung**: Zeitreihen-Daten fuer Grafiken (aggregiert pro Stunde/Tag).

**Authentifizierung**: `current_admin_user`

**Query Parameter**:

| Parameter | Typ | Erforderlich | Beschreibung |
|-----------|-----|-------------|-------------|
| `period_hours` | int | Nein (default: 168) | Zeitfenster |
| `granularity` | string | Nein (default: `hour`) | `hour` oder `day` |
| `user_id` | UUID | Nein | Filter auf User |
| `model_name` | string | Nein | Filter auf Modell |

**Response (200)**:

```json
{
  "granularity": "hour",
  "data": [
    {
      "timestamp": "2026-03-09T10:00:00Z",
      "total_tokens": 15000,
      "prompt_tokens": 11000,
      "completion_tokens": 4000,
      "request_count": 12
    }
  ]
}
```

#### Endpoint 3: `GET /api/ext/token/limits/users`

**Beschreibung**: Alle konfigurierten Per-User Token-Limits abrufen.

**Authentifizierung**: `current_admin_user`

**Response (200)**:

```json
[
  {
    "id": 1,
    "user_id": "550e8400-...",
    "user_email": "max.mustermann@voeb.de",
    "token_budget": 500,
    "period_hours": 168,
    "enabled": true,
    "current_usage": 230000
  }
]
```

**Hinweis**: `token_budget` ist in Tausenden (konsistent mit FOSS `TOKEN_BUDGET_UNIT = 1_000`). `current_usage` wird live aus `ext_token_usage` berechnet.

#### Endpoint 4: `POST /api/ext/token/limits/users`

**Beschreibung**: Per-User Token-Limit erstellen.

**Authentifizierung**: `current_admin_user`

**Request Body**:

```json
{
  "user_id": "550e8400-...",
  "token_budget": 500,
  "period_hours": 168,
  "enabled": true
}
```

**Response (201)**:

```json
{
  "id": 1,
  "user_id": "550e8400-...",
  "token_budget": 500,
  "period_hours": 168,
  "enabled": true
}
```

#### Endpoint 5: `PUT /api/ext/token/limits/users/{limit_id}`

**Beschreibung**: Per-User Token-Limit aktualisieren.

**Authentifizierung**: `current_admin_user`

**Request Body**: Gleich wie POST.

**Response (200)**: Aktualisiertes Limit.

#### Endpoint 6: `DELETE /api/ext/token/limits/users/{limit_id}`

**Beschreibung**: Per-User Token-Limit loeschen.

**Authentifizierung**: `current_admin_user`

**Response (204)**: Kein Body.

### Error Handling

| Fehler-Code | HTTP-Status | Beschreibung |
|-------------|------------|-------------|
| Token-Limit ueberschritten | 429 | "Token-Limit erreicht. Naechstes Fenster beginnt in X h Y min." (mit berechnetem Reset-Zeitpunkt) |
| Ungueltiger User | 404 | "User not found" |
| Ungueltige Parameter | 400 | Pydantic-Validierung (period_hours > 0, token_budget > 0) |
| Nicht authentifiziert | 401 | Onyx Standard-Auth |
| Kein Admin | 403 | `current_admin_user` Dependency |
| DB/Server-Fehler | 500 | Generische Fehlermeldung (keine internen Details) |

---

## Core-Aenderungen

### CORE #2: `backend/onyx/llm/multi_llm.py`

**Erlaubt laut `.claude/rules/core-dateien.md`:**
> ERLAUBT: Nach LLM-Response Hook einfuegen: `ext_token_counter.log_usage(...)` hinter Flag + Try/Except
> VERBOTEN: LLM-Call-Flow, Parameter, Return-Values veraendern

**Hook 1 — Logging (nach LLM-Call, Zeile ~664 und ~743):**

Insertion nach `self._track_llm_cost(model_response.usage)`:

```python
# === VÖB ext-token: Usage Logging ===
try:
    from ext.config import EXT_TOKEN_LIMITS_ENABLED
    if EXT_TOKEN_LIMITS_ENABLED:
        from ext.services.token_tracker import log_token_usage
        log_token_usage(
            user_id=user_identity.user_id if user_identity else None,
            model_name=self._model_version,
            usage=model_response.usage,
        )
except ImportError:
    pass  # ext/ nicht vorhanden
except Exception:
    logger.warning("ext-token logging hook failed", exc_info=True)
```

**Hook 2 — Enforcement (vor LLM-Call, am Anfang von `_completion()`, Zeile ~370):**

Insertion am Anfang von `_completion()`, nach den Parameter-Definitionen:

```python
# === VÖB ext-token: Per-User Limit Check ===
try:
    from ext.config import EXT_TOKEN_LIMITS_ENABLED
    if EXT_TOKEN_LIMITS_ENABLED and user_identity and user_identity.user_id:
        from ext.services.token_tracker import check_user_token_limit
        check_user_token_limit(user_identity.user_id)
except ImportError:
    pass  # ext/ nicht vorhanden
except Exception as e:
    if hasattr(e, "status_code") and e.status_code == 429:
        raise  # 429 mit Reset-Zeitpunkt muss durchkommen
    logger.warning("ext-token limit check failed", exc_info=True)
```

**Aenderungsumfang**: ~20 Zeilen (2 Hooks), kein Eingriff in bestehenden Flow.

**Backup + Patch:**
```bash
cp backend/onyx/llm/multi_llm.py backend/ext/_core_originals/multi_llm.py.original
# Nach Aenderung:
diff -u backend/ext/_core_originals/multi_llm.py.original backend/onyx/llm/multi_llm.py \
  > backend/ext/_core_originals/multi_llm.py.patch
```

---

## Backend-Dateien

### Neue Dateien in `backend/ext/`

| Datei | Zweck |
|-------|-------|
| `ext/models/token_usage.py` | SQLAlchemy Models `ExtTokenUsage` + `ExtTokenUserLimit` |
| `ext/schemas/token.py` | Pydantic Request/Response Schemas |
| `ext/services/token_tracker.py` | `log_token_usage()` + `check_user_token_limit()` + CRUD fuer User-Limits + Aggregationen |
| `ext/routers/token.py` | FastAPI Router (6 Endpoints) |
| `ext/tests/test_token_tracker.py` | Unit Tests fuer Service-Layer |

### Service-Layer: `ext/services/token_tracker.py`

Kernfunktionen:

```python
def log_token_usage(
    user_id: str | None,
    model_name: str,
    usage: Usage,
) -> None:
    """Fire-and-forget: Speichert Token-Usage in ext_token_usage.
    Darf Onyx NIEMALS brechen — alle Exceptions werden gefangen + geloggt."""

def check_user_token_limit(user_id: str) -> None:
    """Prueft ob User sein Token-Limit ueberschritten hat.
    Wirft HTTPException(429) wenn ueberschritten.
    Liest Limit aus ext_token_user_limit, Usage aus ext_token_usage."""

def get_usage_summary(
    period_hours: int,
    user_id: str | None = None,
    model_name: str | None = None,
) -> dict:
    """Aggregiert Usage aus ext_token_usage fuer Dashboard."""

def get_usage_timeseries(
    period_hours: int,
    granularity: str = "hour",
    user_id: str | None = None,
    model_name: str | None = None,
) -> list[dict]:
    """Zeitreihen-Aggregation fuer Dashboard-Grafiken."""
```

### Per-User Limit Enforcement — Technischer Ansatz

**Problem:** FOSS `check_token_rate_limits()` nutzt `fetch_versioned_implementation()` was EE-Override erwartet. Unser `backend/ee/` ist leer, also faellt es auf die FOSS-Version zurueck (nur Global). Die FOSS `token_rate_limit` Tabelle hat keine `user_id` Spalte und kann Per-User Limits nicht abbilden.

**Loesung:** Eigene Tabelle + eigener Enforcement-Pfad:
1. Per-User Limits werden in **eigener Tabelle `ext_token_user_limit`** gespeichert (mit `user_id` FK, `token_budget`, `period_hours`, `enabled`)
2. CRUD-Operationen werden custom geschrieben in `ext/services/token_tracker.py`
3. Enforcement passiert in `multi_llm.py` (CORE #2) — VOR dem LLM-Call in `_completion()` (Zeile ~371)
4. Usage-Daten kommen aus `ext_token_usage` (unsere Tabelle), nicht aus `ChatMessage.token_count`
5. Dadurch werden ALLE LLM-Calls erfasst (Chat, Search, Deep Research, Agents), nicht nur Chat-Messages
6. Embedding-Calls werden NICHT erfasst (gehen nicht durch `_completion()`)

**Enforcement-Logik in `check_user_token_limit()`:**
```python
def check_user_token_limit(user_id: str) -> None:
    # 1. Limit fuer User aus ext_token_user_limit laden
    # 2. Falls kein Limit konfiguriert oder disabled → return (kein Limit)
    # 3. Usage im Zeitfenster summieren: SELECT SUM(total_tokens) FROM ext_token_usage
    #    WHERE user_id = ? AND created_at >= NOW() - period_hours
    # 4. Vergleich: usage >= token_budget * TOKEN_BUDGET_UNIT →
    #    Reset-Zeitpunkt berechnen (aeltester relevanter Eintrag + period_hours)
    #    HTTPException(429, detail="Token-Limit erreicht. Naechstes Fenster beginnt in Xh Ym.")
```

**Token-Count Quelle:** Wir nutzen `response.usage.total_tokens` aus der LLM-Response (vom Provider berechnet). Das ist genauer als `ChatMessage.token_count` (der vom lokalen Tokenizer berechnet wird und abweichen kann).

**Warum `_completion()` der richtige Hook-Punkt ist:**
- Sowohl `invoke()` als auch `stream()` rufen `_completion()` auf → EIN Hook fuer beide Pfade
- `user_identity` ist als Parameter verfuegbar (Zeile 368)
- Hook laeuft VOR `litellm.completion()` (Zeile 533) → kann blockieren bevor Kosten entstehen
- HTTPException(429) propagiert korrekt: `invoke()` und `stream()` haben kein try/except das sie verschluckt
- Background-Tasks ohne `user_identity` ueberspringen den Hook automatisch

**Streaming-Hinweis:** Der Logging-Hook (nach LLM-Call) wird bei Streaming pro Chunk aufgerufen (Zeile 743). Usage-Info kommt typischerweise nur im letzten Chunk. Zur Sicherheit pruefen wir `completion_tokens > 0` vor dem INSERT.

---

## Frontend-Komponenten

### Seite: `/admin/ext-token`

**Route:** `web/src/app/admin/ext-token/page.tsx` (Next.js App Router, konsistent mit ext-branding Pattern `/admin/ext-branding`)

**Hauptkomponente:** `web/src/ext/components/token/TokenManagementPage.tsx`

**Tabs:**

| Tab | Inhalt | Datenquelle |
|-----|--------|-------------|
| Uebersicht | Gesamt-Tokens, Top-User, Top-Modelle | `GET /api/ext/token/usage/summary` |
| Zeitverlauf | Liniendiagramm (Tokens pro Stunde/Tag) | `GET /api/ext/token/usage/timeseries` |
| Per-User Breakdown | Tabelle: User, Tokens, Requests, % vom Limit | `GET /api/ext/token/usage/summary` |
| User Limits | CRUD fuer Per-User Token Budgets | `GET/POST/PUT/DELETE /api/ext/token/limits/users` |

**Technologie:**
- React + TypeScript (Standard Onyx-Stack)
- `useSWR` fuer Data-Fetching (CLAUDE.md Regel)
- Onyx `refresh-components` fuer UI-Elemente (Button, Table, Tabs)
- Icons aus `@opal/icons` (gleiche Quelle wie AdminSidebar.tsx, z.B. `SvgPaintBrush` fuer ext-branding)
- Tailwind mit Custom Colors (`text-01`, `background-neutral-01`, etc.)
- Kein `dark:` Modifier (CLAUDE.md Regel)

### Sidebar-Link

**CORE #10: `AdminSidebar.tsx`** — Neuer Link unter Settings-Section (analog zu ext-branding):

```typescript
// "Token Usage" Link unter Settings, nur wenn EXT_TOKEN_LIMITS_ENABLED
```

Patch-Update: Der bestehende `AdminSidebar.tsx.patch` (von ext-branding) wird kumulativ erweitert.

---

## Konfiguration

### Environment Variables

| Variable | Wert-Typ | Pflichtfeld | Standard | Beschreibung |
|----------|----------|-----------|---------|-------------|
| `EXT_ENABLED` | boolean | Ja | `false` | Master-Switch (bereits vorhanden) |
| `EXT_TOKEN_LIMITS_ENABLED` | boolean | Ja | `false` | Token-Modul aktivieren (bereits in config.py) |

**Keine weiteren Env-Variablen noetig.** Token-Budgets und Zeitfenster werden ueber die Admin-UI konfiguriert, nicht ueber Environment Variables.

### Feature Flags

```python
# backend/ext/config.py (bereits vorhanden, Zeilen 13-16)
EXT_TOKEN_LIMITS_ENABLED: bool = (
    EXT_ENABLED
    and os.getenv("EXT_TOKEN_LIMITS_ENABLED", "false").lower() == "true"
)
```

### Helm Values

```yaml
# deployment/helm/values/values-dev.yaml (ergaenzen)
configMap:
  env:
    EXT_TOKEN_LIMITS_ENABLED: "true"  # Aktivieren auf DEV

# deployment/helm/values/values-test.yaml (ergaenzen)
configMap:
  env:
    EXT_TOKEN_LIMITS_ENABLED: "true"  # Aktivieren auf TEST
```

---

## Fehlerbehandlung und Logging

### Fehlerbehandlungs-Strategie

1. **Logging-Hook (nach LLM-Call):** Fire-and-forget. Exception wird geloggt, bricht Onyx NICHT.
2. **Enforcement-Hook (vor LLM-Call):** HTTPException(429) wird durchgereicht. Alle anderen Exceptions werden geloggt + ignoriert.
3. **API-Endpoints:** Standard Pydantic-Validierung + SQLAlchemy ORM (kein raw SQL).
4. **Grundregel:** ext-token darf Onyx NIEMALS brechen. Wenn ext-token crasht, funktioniert Onyx weiter.

### Logging-Strategie

| Level | Beispiel | Wann |
|-------|----------|------|
| `DEBUG` | "Token usage logged: user=X, model=Y, tokens=Z" | Jeder erfolgreiche Log |
| `INFO` | "ext-token router registered" | Startup |
| `WARN` | "ext-token logging hook failed: ..." | Hook-Exception (non-fatal) |
| `ERROR` | "ext-token limit check failed: ..." | Enforcement-Exception (non-fatal) |

**DSGVO:** Keine personenbezogenen Daten in Logs. User-ID (UUID) ist pseudonymisiert. Keine E-Mail-Adressen in Logs.

**Logger:** `logging.getLogger("ext.token")`

---

## Performance-Anforderungen

| Anforderung | Zielwert | Massnahme |
|------------|---------|-----------|
| Logging-Hook Latenz | < 10 ms | Einfaches INSERT, kein JOIN |
| Enforcement-Hook Latenz | < 20 ms | SUM-Query mit Index auf (user_id, created_at) |
| Dashboard-API Latenz | < 500 ms | Aggregations-Queries mit Indizes |
| DB-Tabellengroesse | ~100k Rows/Monat bei 150 Usern | Retention-Policy spaeter (nicht in v1.0) |

### Optimierungen

- **Composite Index** `(user_id, created_at)` fuer Rate-Limit-Pruefung
- **Kein Redis-Cache** in v1.0 (unnoetige Komplexitaet bei 150 Usern)
- **Kein Batching** in v1.0 (einzelne INSERTs sind bei der Last ausreichend)

---

## Test-Strategie

### Unit Tests (`backend/ext/tests/test_token_tracker.py`)

```python
class TestTokenTracker:
    def test_log_token_usage_stores_correctly(self): ...
    def test_log_token_usage_handles_null_user(self): ...
    def test_check_user_limit_passes_when_under_budget(self): ...
    def test_check_user_limit_raises_429_when_over_budget(self): ...
    def test_check_user_limit_passes_when_no_limit_configured(self): ...
    def test_get_usage_summary_aggregates_correctly(self): ...
    def test_get_usage_summary_filters_by_user(self): ...
    def test_get_usage_summary_filters_by_model(self): ...
    def test_get_usage_timeseries_groups_by_hour(self): ...
    def test_get_usage_timeseries_groups_by_day(self): ...
```

### Integration Tests (`backend/tests/integration/ext/test_token_api.py`)

```python
class TestTokenAPI:
    def test_usage_summary_requires_admin(self): ...
    def test_usage_summary_returns_correct_data(self): ...
    def test_create_user_limit(self): ...
    def test_update_user_limit(self): ...
    def test_delete_user_limit(self): ...
    def test_user_limit_enforcement_returns_429(self): ...
    def test_disabled_flag_skips_all_hooks(self): ...
```

### Feature Flag Test

```python
def test_ext_token_disabled_by_default(self):
    """GET /api/ext/health — modules.token_limits should be false when flag off."""
```

---

## Sicherheits-Checkliste

- [ ] Alle Inputs via Pydantic Schemas validiert
- [ ] Keine SQL-Strings aus User-Input (NUR SQLAlchemy ORM)
- [ ] String-Maxlaenge (model_name: 255), numerische Min/Max (period_hours > 0, token_budget > 0)
- [ ] Alle Endpoints erfordern `current_admin_user`
- [ ] Keine personenbezogenen Daten in Logs (nur UUID)
- [ ] Keine Tokens/Passwoerter in Logs
- [ ] Alle Exceptions gefangen in Hooks (kein unhandled an Client)
- [ ] Keine internen Details in Fehlermeldungen (429-Message ist generisch)
- [ ] HTTP-Statuscodes korrekt (400/401/403/429/500)
- [ ] ext-Hooks in Core-Dateien: Try/Except, Onyx nie brechen

---

## Offene Punkte

- [ ] **[OPEN-1]** Sidebar-Link: Eigenes Icon fuer "Token Usage" auswaehlen (aus `@opal/icons`)
  - **Verantwortlicher**: CCJ
  - **Kontext**: ext-branding nutzt `SvgPaintBrush` aus `@opal/icons` — Token braucht eigenes Icon aus derselben Quelle

- [x] **[OPEN-2]** ~~Dashboard-Grafiken: Welche Chart-Library?~~ → `recharts` v2.13.1 ist bereits in `web/package.json` als Dependency vorhanden
  - **Entscheidung**: `recharts` verwenden (Line/Bar Charts fuer Zeitreihen, Pie Charts fuer Modell-Verteilung)

- [ ] **[OPEN-3]** Retention-Policy: Wie lange werden Usage-Logs aufbewahrt?
  - **Verantwortlicher**: VoeB (Compliance/DSGVO)
  - **Kontext**: ~100k Rows/Monat bei 150 Usern. Ohne Cleanup waechst die Tabelle stetig.

---

## Implementierungs-Abweichungen (v0.3)

Dokumentiert nach Implementierung + Docker-Test am 2026-03-09.

| ID | Spec v0.2 | Implementierung | Begruendung |
|----|-----------|-----------------|-------------|
| D1 | `log_token_usage(user_id, model_name, usage: Usage)` | `log_token_usage(user_id, model_name, prompt_tokens, completion_tokens, total_tokens)` | Individuelle int-Parameter statt Usage-Objekt — vermeidet Import-Dependency auf `onyx.llm.model_response.Usage` in ext-Code |
| D2 | Frontend in `web/src/ext/components/token/TokenManagementPage.tsx` | Frontend in `web/src/ext/pages/admin/token/page.tsx` | `pages/` statt `components/` — konsistent mit ext-branding Pattern, klarere Trennung Page vs. Component |
| D3 | `user_identity.user_id` ist UUID-String → direkter `UUID()` Cast | `_resolve_user_uuid()` resolved Email ODER UUID → User-Tabellen-Lookup | Onyx uebergibt Email (nicht UUID) als `user_identity.user_id` — Cast scheiterte, Bugfix erforderte Resolver-Funktion |
| D4 | User Limits: UUID-Eingabefeld | User Limits: Email-Dropdown (fetcht `/api/manage/users`) | UX-Verbesserung — Admin kennt keine UUIDs, Email-Auswahl ist praxistauglich |
| D5 | Frontend nutzt `useSWR` (CLAUDE.md Regel) | Frontend nutzt `fetch` + `useState` | Bewusste v1-Entscheidung — Cleanup in v1.1 geplant |
| D6 | `recharts` fuer Zeitverlauf-Grafiken | Horizontale Balken mit CSS (`div` + `style.width`) | Reduziert Komplexitaet fuer v1, `recharts`-Integration in v1.1 |

---

## Approvals

| Rolle | Name | Datum | Status |
|------|------|-------|--------|
| Technical Lead | Nikolaj Ivanov | TBD | Ausstehend |

---

## Revisions-Historie

| Version | Datum | Autor | Aenderungen |
|---------|-------|-------|-----------|
| 0.1 | 2026-03-09 | CCJ | Initialer Entwurf basierend auf Tiefenanalyse |
| 0.2 | 2026-03-09 | CCJ | Validierung: 3 Fehler korrigiert — eigene `ext_token_user_limit` Tabelle statt FOSS `token_rate_limit` (keine user_id Spalte in FOSS), Route `/admin/ext-token` (konsistent mit ext-branding), Icons aus `@opal/icons`, `recharts` als Chart-Library bestaetigt, Streaming-Deduplizierung dokumentiert, Token-Count-Quelle praezisiert |
| 0.3 | 2026-03-09 | CCJ | Implementierung abgeschlossen, Abweichungen dokumentiert (D1-D3), Status auf Freigegeben |
