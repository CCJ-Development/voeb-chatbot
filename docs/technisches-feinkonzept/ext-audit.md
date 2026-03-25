# Modulspezifikation: ext-audit (Audit-Logging)

**Dokumentstatus**: Entwurf
**Version**: 0.1
**Autor**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Datum**: 2026-03-25
**Status**: [x] Entwurf | [ ] Review | [ ] Freigegeben
**Prioritaet**: [x] Hoch | [ ] Kritisch | [ ] Normal | [ ] Niedrig

---

## Moduluebersicht

| Feld | Wert |
|------|------|
| **Modulname** | Audit-Logging |
| **Modul-ID** | `ext_audit` |
| **Version** | 0.1.0 |
| **Feature Flag** | `EXT_AUDIT_ENABLED` (neu, in `backend/ext/config.py` hinzufuegen) |
| **Abhaengigkeiten** | Phase 4a Extension Framework ✅ |

---

## Zweck und Umfang

### Zweck

Enterprise-Banking-Kontext erfordert Nachvollziehbarkeit: Wer hat wann was geaendert?
DSGVO Art. 5 (Rechenschaftspflicht), BSI OPS.1.1.5 (Protokollierung).

ext-audit protokolliert alle Admin-Aktionen in einer PostgreSQL-Tabelle:
- Gruppen erstellen/aendern/loeschen (ext-rbac)
- Branding-Einstellungen aendern (ext-branding)
- System Prompts erstellen/aendern/loeschen (ext-prompts)
- Token-Limits setzen/aendern (ext-token)
- Document Access Resync ausloesen (ext-access)
- Login-Events (Success/Failure, wenn moeglich)

### Im Umfang enthalten

- Backend: `ext_audit_log` DB-Tabelle + Alembic-Migration
- Backend: `log_audit_event()` Utility-Funktion (aufgerufen von bestehenden ext-Routern)
- Backend: Admin-Endpoint GET `/ext/audit/events` (Audit-Log Browser mit Filtern)
- Backend: Admin-Endpoint GET `/ext/audit/export` (CSV-Export fuer Compliance)
- DSGVO: IP-Anonymisierung nach 90 Tagen (Celery-Task `ext_audit_ip_anonymize`, 24h-Intervall, self-scheduling)

### Nicht im Umfang

- Frontend-UI fuer Audit-Log (Phase 2 — aktuell reicht API + CSV-Export)
- Onyx-Core Admin-Aktionen (wir koennen keine Hooks in Core-Dateien fuer Audit setzen — das waere eine neue Core-Datei)
- Echtzeit-Alerting auf Audit-Events (Monitoring-Alerts decken Security ab)

### Architekturentscheidung: PostgreSQL statt Loki

| Kriterium | PostgreSQL | Loki |
|-----------|-----------|------|
| DSGVO Loeschrecht (Art. 17) | `DELETE WHERE actor_email = ?` | Append-only, gezielte Loeschung extrem aufwaendig |
| Strukturierte Abfragen | SQL mit Filtern | LogQL (weniger praezise) |
| Infrastruktur | Existiert bereits | Frisch deployed (Sprint Loki) |
| Admin-UI moeglich | Ja (DB-backed API) | Nur Grafana Explore |

**Entscheidung: PostgreSQL.** Loki dient als Backup (ext-audit loggt auch auf stdout → Loki faengt es auf).

---

## API-Endpoints

### GET /ext/audit/events

Audit-Log Browser mit Filtern und Pagination.

| Feld | Wert |
|------|------|
| Pfad | `/api/ext/audit/events` |
| Methode | GET |
| Auth | Required (ADMIN only) |
| Query-Parameter | `actor_email` (optional), `action` (optional), `resource_type` (optional), `from_date` (optional, ISO 8601), `to_date` (optional, ISO 8601), `page` (default 1), `page_size` (default 50, max 200) |
| Response | `{ "events": [...], "total": 123, "page": 1, "page_size": 50 }` |
| Fehlercodes | 401 Nicht authentifiziert, 403 Kein Admin, 404 Feature deaktiviert |

Event-Objekt:
```json
{
  "id": "uuid",
  "timestamp": "2026-03-25T12:00:00Z",
  "actor_email": "n.ivanov@scale42.de",
  "actor_role": "ADMIN",
  "action": "CREATE",
  "resource_type": "GROUP",
  "resource_id": "5",
  "resource_name": "Kreditabteilung",
  "details": {"members_added": 3},
  "ip_address": "188.34.92.162"
}
```

### GET /ext/audit/export

CSV-Export fuer Compliance-Reports.

| Feld | Wert |
|------|------|
| Pfad | `/api/ext/audit/export` |
| Methode | GET |
| Auth | Required (ADMIN only) |
| Query-Parameter | `from_date` (required), `to_date` (required) |
| Response | `text/csv` Download |
| Fehlercodes | 400 Datumsbereich >90 Tage, 401, 403, 404 |

---

## Datenbankschema

### Tabelle: `ext_audit_log`

| Spalte | Typ | Constraints | Default | Beschreibung |
|--------|-----|------------|---------|-------------|
| `id` | UUID | PK | `gen_random_uuid()` | Eindeutige ID |
| `timestamp` | TIMESTAMPTZ | NOT NULL, INDEX | `now()` | Zeitpunkt der Aktion |
| `actor_email` | VARCHAR(255) | NULLABLE | — | Wer (Email, NULL fuer System-Events) |
| `actor_role` | VARCHAR(50) | NULLABLE | — | ADMIN, CURATOR, BASIC, SYSTEM |
| `action` | VARCHAR(50) | NOT NULL | — | CREATE, UPDATE, DELETE, LOGIN, LOGIN_FAILED, RESYNC |
| `resource_type` | VARCHAR(50) | NOT NULL | — | GROUP, BRANDING, PROMPT, TOKEN_LIMIT, DOC_ACCESS, AUTH |
| `resource_id` | VARCHAR(255) | NULLABLE | — | ID der betroffenen Ressource |
| `resource_name` | VARCHAR(255) | NULLABLE | — | Name fuer Lesbarkeit |
| `details` | JSONB | NULLABLE | — | Zusaetzliche Infos (diff, alte/neue Werte) |
| `ip_address` | INET | NULLABLE | — | Client-IP (DSGVO: nach 90d anonymisieren) |
| `user_agent` | TEXT | NULLABLE | — | Browser/Client Info |

### Indizes

```sql
CREATE INDEX idx_ext_audit_log_timestamp ON ext_audit_log (timestamp DESC);
CREATE INDEX idx_ext_audit_log_actor ON ext_audit_log (actor_email);
CREATE INDEX idx_ext_audit_log_resource ON ext_audit_log (resource_type, resource_id);
CREATE INDEX idx_ext_audit_log_action ON ext_audit_log (action);
```

### Alembic-Migration

- Revision: `d8a1b2c3e4f5_ext_audit_create_table.py`
- Down-Revision: `c7f2e8a3d105` (ext-prompts, aktueller Head)
- Nur `CREATE TABLE` + Indizes, kein Data-Migration

### DSGVO: IP-Anonymisierung

Implementiert als `@shared_task(name="ext_audit_ip_anonymize")` in `backend/ext/tasks/audit_ip_anonymize.py`.
Self-scheduling (same pattern wie `ext_doc_access_sync`): Nach jedem Lauf schedult sich der Task
selbst mit `apply_async(countdown=86400)` fuer den naechsten Lauf in 24 Stunden.

```sql
UPDATE ext_audit_log
SET ip_address = NULL, user_agent = NULL
WHERE timestamp < now() - INTERVAL '90 days'
AND ip_address IS NOT NULL;
```

---

## Implementierungsdetails

### Neue Dateien

| # | Datei | Zweck | Zeilen |
|---|-------|-------|--------|
| 1 | `backend/ext/models/audit.py` | SQLAlchemy Model | ~30 |
| 2 | `backend/ext/services/audit.py` | `log_audit_event()` + Query-Logik + CSV-Export + IP-Anonymisierung | ~150 |
| 3 | `backend/ext/routers/audit.py` | 2 Admin-Endpoints + `get_audit_context` Dependency | ~90 |
| 4 | `backend/ext/schemas/audit.py` | Pydantic Schemas | ~40 |
| 5 | `backend/ext/tests/test_audit.py` | Unit Tests | ~130 |
| 6 | Alembic-Migration | DB-Tabelle | ~40 |

### Client-IP Extraktion: FastAPI Dependency

**Problem:** Bestehende ext-Router verwenden `request` als Parametername fuer Pydantic-Schemas
(z.B. `request: UserGroupCreate` in rbac.py). Ein zusaetzlicher `request: Request` Parameter
wuerde Namenskonflikte verursachen.

**Loesung:** FastAPI Dependency `get_audit_context` die das Starlette `Request`-Objekt liest:

```python
from fastapi import Depends, Request

def get_audit_context(request: Request) -> dict:
    """Extrahiert Client-IP und User-Agent aus dem HTTP-Request.

    Beruecksichtigt X-Forwarded-For Header (NGINX Proxy).
    Kein Namenskonflikt mit Pydantic 'request'-Parametern weil
    FastAPI Dependencies ueber den Typ aufgeloest werden.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else None
    if not ip and request.client:
        ip = request.client.host
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent"),
    }
```

### log_audit_event() — Zentrale Utility

```python
def log_audit_event(
    db_session: Session,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    resource_name: str | None = None,
    details: dict | None = None,
    audit_ctx: dict | None = None,  # Von get_audit_context Dependency
) -> None:
    """Schreibt ein Audit-Event in die DB + stdout (fuer Loki).

    WICHTIG: Faengt alle Exceptions — bricht NIEMALS den Request ab.
    """
```

Wird in bestehende ext-Router eingefuegt (KEIN Core-Patch noetig):

```python
# Beispiel: ext/routers/rbac.py, nach create_user_group()
from ext.services.audit import log_audit_event
from ext.routers.audit import get_audit_context

@admin_router.post("", status_code=201)
def api_create_user_group(
    request: UserGroupCreate,         # Pydantic Schema (unveraendert)
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),  # NEU: IP + User-Agent
) -> dict:
    result = create_user_group(db_session, ...)
    log_audit_event(
        db_session=db_session,
        actor=user,
        action="CREATE",
        resource_type="GROUP",
        resource_id=str(result["id"]),
        resource_name=request.name,
        audit_ctx=audit_ctx,
    )
    return result
```

### Betroffene ext-Router (Aenderungen)

Jeder Endpoint bekommt 2 Zeilen:
1. `audit_ctx: dict = Depends(get_audit_context)` als neuer Parameter
2. `log_audit_event(...)` Aufruf nach der eigentlichen Aktion

| Router | Endpoints betroffen | Aenderungen pro Endpoint |
|--------|-------------------|-------------------------|
| `ext/routers/rbac.py` | 5 (create, update, delete, add-users, set-curator) | +2 Zeilen |
| `ext/routers/branding.py` | 3 (put settings, put logo, delete logo) | +2 Zeilen |
| `ext/routers/prompts.py` | 3 (create, update, delete) | +2 Zeilen |
| `ext/routers/token.py` | 3 (create limit, update limit, delete limit) | +2 Zeilen |
| `ext/routers/doc_access.py` | 1 (resync) | +2 Zeilen |
| **Gesamt** | **15 Endpoints** | **+30 Zeilen** |

### Audit-Events pro ext-Modul

| Modul | Endpoint | Action | Resource Type |
|-------|----------|--------|--------------|
| ext-rbac | POST /user-group | CREATE | GROUP |
| ext-rbac | PATCH /user-group/{id} | UPDATE | GROUP |
| ext-rbac | DELETE /user-group/{id} | DELETE | GROUP |
| ext-rbac | POST /user-group/{id}/add-users | UPDATE | GROUP_MEMBERS |
| ext-branding | PUT /admin/enterprise-settings | UPDATE | BRANDING |
| ext-branding | PUT /admin/enterprise-settings/logo | UPDATE | LOGO |
| ext-branding | DELETE /admin/enterprise-settings/logo | DELETE | LOGO |
| ext-prompts | POST /ext/prompts | CREATE | PROMPT |
| ext-prompts | PUT /ext/prompts/{id} | UPDATE | PROMPT |
| ext-prompts | DELETE /ext/prompts/{id} | DELETE | PROMPT |
| ext-token | POST /ext/token/limits/users | CREATE | TOKEN_LIMIT |
| ext-token | PATCH /ext/token/limits/users/{id} | UPDATE | TOKEN_LIMIT |
| ext-token | DELETE /ext/token/limits/users/{id} | DELETE | TOKEN_LIMIT |
| ext-access | POST /ext/doc-access/resync | RESYNC | DOC_ACCESS |

---

## Fehlerbehandlung

| Fehlerfall | HTTP | Verhalten |
|-----------|------|-----------|
| Feature Flag deaktiviert | 404 | Router nicht registriert |
| Nicht authentifiziert | 401 | Onyx Auth-Middleware |
| Kein Admin | 403 | `Depends(current_admin_user)` |
| Datumsbereich >90 Tage (Export) | 400 | "Maximaler Export-Zeitraum: 90 Tage" |
| Ungueltige Filter-Parameter | 400 | Pydantic Validation |
| DB-Fehler beim Schreiben | — | `log_audit_event()` faengt Exception, loggt auf stderr, bricht NICHT den Request ab |
| Leeres Audit-Log | 200 | `{ "events": [], "total": 0 }` |

**Kritische Design-Entscheidung:** `log_audit_event()` darf NIEMALS den eigentlichen Request abbrechen. Wenn das Audit-Schreiben fehlschlaegt, wird der Fehler geloggt und der Request geht normal weiter. Audit ist best-effort, nicht transaktional mit der Haupt-Aktion.

---

## Feature Flag Verhalten

### `EXT_AUDIT_ENABLED = true`

- Audit-Endpoints verfuegbar (`/ext/audit/events`, `/ext/audit/export`)
- `log_audit_event()` schreibt in DB + stdout
- IP-Anonymisierung laeuft als periodischer Task
- Bestehende ext-Router rufen `log_audit_event()` auf (nur wenn Flag aktiv)

### `EXT_AUDIT_ENABLED = false` (Default)

- Audit-Endpoints nicht registriert (404)
- `log_audit_event()` macht nichts (early return)
- Keine DB-Writes in `ext_audit_log`
- DB-Tabelle existiert (Migration laeuft immer), bleibt leer

---

## Betroffene Core-Dateien

**Keine.** ext-audit veraendert keine Core-Dateien.

Audit-Hooks werden in bestehende ext-Router eingefuegt (backend/ext/routers/), die wir selbst kontrollieren.
Dies ist ein reines ext-Modul ohne Core-Patching.

---

## Tests

### Unit Tests (`backend/ext/tests/test_audit.py`)

| # | Test | Beschreibung |
|---|------|-------------|
| 1 | `test_log_audit_event_creates_entry` | Event wird in DB geschrieben |
| 2 | `test_log_audit_event_with_all_fields` | Alle Felder korrekt gespeichert |
| 3 | `test_log_audit_event_without_actor` | System-Events (actor=None) |
| 4 | `test_log_audit_event_never_raises` | Exception in DB → kein Crash |
| 5 | `test_log_audit_event_disabled` | Flag=false → kein DB-Write |
| 6 | `test_query_events_with_filters` | Filter nach actor, action, resource_type, Datum |
| 7 | `test_query_events_pagination` | Page/PageSize korrekt |
| 8 | `test_export_csv_format` | CSV-Output korrekt formatiert |
| 9 | `test_export_max_range` | >90 Tage → 400 |
| 10 | `test_ip_anonymization` | IPs aelter 90d → NULL gesetzt |

### Feature Flag Tests

| # | Test | Beschreibung |
|---|------|-------------|
| 1 | `test_endpoints_404_when_disabled` | Flag=false → 404 |
| 2 | `test_log_noop_when_disabled` | Flag=false → kein DB-Write |

### Edge Cases

| # | Test | Beschreibung |
|---|------|-------------|
| 1 | `test_details_json_large` | Grosses JSONB-Feld (10KB) |
| 2 | `test_concurrent_writes` | Mehrere Events gleichzeitig |
| 3 | `test_empty_audit_log` | Keine Events → leere Response |

---

## Aufwandsschaetzung

| Arbeitspaket | Aufwand |
|-------------|---------|
| DB-Model + Alembic-Migration | 1h |
| Service (log_audit_event, query, export, anonymize) | 2h |
| Router (2 Endpoints) | 1h |
| Hooks in bestehende ext-Router | 1.5h |
| Tests | 2h |
| **Gesamt** | **~7.5h** |
