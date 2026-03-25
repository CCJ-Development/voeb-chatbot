# Modulspezifikation: ext-access (Document Access Control)

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
| **Modulname** | Document Access Control |
| **Modul-ID** | `ext_access` |
| **Version** | 0.1.0 |
| **Phase** | 4g |
| **Feature Flag** | `EXT_DOC_ACCESS_ENABLED` (existiert bereits in `backend/ext/config.py:33-36`) |
| **Abhaengigkeiten** | Phase 4a Extension Framework ✅, Phase 4f ext-rbac ✅ (liefert Gruppen-CRUD + M2M-Tabellen) |

---

## Zweck und Umfang

### Zweck

VÖB hat ~100 Mitarbeitende in 16 Abteilungen. ext-rbac ermoeglicht Gruppen (= Abteilungen), aber
Dokumente sind aktuell fuer alle sichtbar. ext-access schliesst diese Luecke:

- Dokumente nur fuer bestimmte Gruppen sichtbar machen
- Suchergebnisse nach Gruppenzugehoerigkeit filtern
- Connector-Daten (z.B. SharePoint einer Abteilung) nur der zugewiesenen Gruppe zeigen

### Wie es funktioniert (Ende-zu-Ende)

```
ADMIN: Weist ConnectorCredentialPair einer Gruppe zu (via ext-rbac UI)
                          ↓
ext-rbac: Setzt UserGroup.is_up_to_date = False
                          ↓
ext-access Celery-Task (alle 60s): Findet Gruppen mit is_up_to_date == False
                          ↓
Query: UserGroup → UserGroup__ConnectorCredentialPair → DocumentByConnectorCredentialPair → document_ids
                          ↓
Fuer jedes Dokument: ACL in OpenSearch aktualisieren (user_groups befuellen)
                          ↓
UserGroup.is_up_to_date = True
                          ↓
USER: Stellt Suchanfrage
                          ↓
Core #3 Hook: get_acl_for_user() liefert {"user_email:alice@voeb.de", "group:Kreditabteilung", "PUBLIC"}
                          ↓
OpenSearch: Filtert Dokumente — zeigt nur Treffer wo ACL matched
```

### Im Umfang enthalten

- Backend: Core #3 Patch (access.py) — 3 Hooks fuer Gruppen-ACLs
- Backend: Celery-Task fuer ACL-Sync bei Gruppenaeaenderungen
- Backend: Admin-Endpoint `/ext/doc-access/resync` fuer einmaligen Full-Sync
- Backend: Admin-Endpoint `/ext/doc-access/status` fuer Sync-Status

### Nicht im Umfang

- Frontend-UI fuer Dokument-Berechtigungen (Zuordnung laeuft ueber ext-rbac Gruppen-UI)
- Externe Permission-Sync (z.B. SharePoint-Berechtigungen importieren)
- Document-Level ACL (Einzeldokument einem User zuweisen) — nur Gruppen-basiert
- Patching von `redis_usergroup.py` oder `tasks.py` — eigener Sync-Mechanismus (Ansatz C)

### Architekturentscheidung: Ansatz C (eigener Celery-Task)

**Problem:** Onyx's UserGroup-Sync-Pipeline hat 6 EE-Guards in `redis_usergroup.py` und `tasks.py`
die FOSS komplett blockieren. 4 fehlende EE-Funktionen muessten nachgebaut werden.

**Entscheidung:** Statt 2 neue Core-Dateien zu patchen (#15, #16), bauen wir einen eigenen
einfachen Celery-Task in `backend/ext/`. Dieser umgeht die gesamte Onyx-Sync-Pipeline.

**Begruendung:**
- Minimum Core-Changes (14 Core-Dateien bleiben, nur #3 wird gepatcht)
- Onyx's Redis-Fence-Koordination ist fuer Scale — bei 150 Usern unnoetig
- Eigener Task ist ~50 Zeilen, nicht 500
- Niedrigstes Merge-Risiko bei Upstream-Syncs

Dokumentiert als ADR wenn gewuenscht.

---

## API-Endpoints

### POST /ext/doc-access/resync

Full Re-Sync aller Gruppen-ACLs. Noetig bei:
- Erstmalige Aktivierung von ext-access (bestehende Dokumente haben keine group: ACLs)
- Nach manuellem Daten-Fix

| Feld | Wert |
|------|------|
| Pfad | `/api/ext/doc-access/resync` |
| Methode | POST |
| Auth | Required (ADMIN only) |
| Request Body | Keiner |
| Response | `{ "status": "started", "groups_queued": 5, "estimated_documents": 601 }` |
| Fehlercodes | 401 Nicht authentifiziert, 403 Kein Admin, 404 Feature deaktiviert |

### GET /ext/doc-access/status

Aktueller Sync-Status.

| Feld | Wert |
|------|------|
| Pfad | `/api/ext/doc-access/status` |
| Methode | GET |
| Auth | Required (ADMIN only) |
| Request Body | Keiner |
| Response | `{ "enabled": true, "groups_total": 5, "groups_synced": 4, "groups_pending": 1, "last_sync": "2026-03-25T12:00:00Z" }` |
| Fehlercodes | 401 Nicht authentifiziert, 403 Kein Admin, 404 Feature deaktiviert |

---

## Datenbankschema

### Keine neuen Tabellen

Alle benoetigten Tabellen existieren bereits in Onyx FOSS:

| Tabelle | Zweck | Genutzt von |
|---------|-------|-------------|
| `user_group` | Gruppen-Definition (Name, etc.) | ext-rbac (CRUD) |
| `user__user_group` | User ↔ Gruppe (M2M) | ext-rbac (Mitglieder) |
| `user_group__connector_credential_pair` | Gruppe ↔ Connector (M2M) | ext-rbac (CC-Pair Zuordnung) |
| `document_by_connector_credential_pair` | Dokument ↔ Connector (M2M) | Onyx Core (Indexierung) |

**Abfrage-Kette fuer Gruppen-ACLs eines Dokuments:**
```sql
SELECT ug.name
FROM user_group ug
JOIN user_group__connector_credential_pair ugcc ON ug.id = ugcc.user_group_id
JOIN document_by_connector_credential_pair dcc ON ugcc.cc_pair_id = dcc.cc_pair_id
WHERE dcc.id = :document_id
```

**Abfrage-Kette fuer Gruppen eines Users:**
```sql
SELECT ug.name
FROM user_group ug
JOIN user__user_group uug ON ug.id = uug.user_group_id
WHERE uug.user_id = :user_id
```

### Alembic-Migration

Keine Migration noetig — alle Tabellen existieren. Kein Schema-Change.

---

## Implementierungsdetails

### Neue Dateien

| # | Datei | Zweck | Geschaetzte Zeilen |
|---|-------|-------|-------------------|
| 1 | `backend/ext/services/doc_access.py` | Kernlogik: ACL-Berechnung, Sync-Job, Re-Sync | ~120 |
| 2 | `backend/ext/routers/doc_access.py` | 2 Admin-Endpoints (resync, status) | ~60 |
| 3 | `backend/ext/schemas/doc_access.py` | Pydantic Schemas (Response) | ~25 |

### backend/ext/services/doc_access.py — Kernlogik

**Funktion 1: `get_group_acls_for_user(user, db_session) -> set[str]`**

Wird von Core #3 Hook in `_get_acl_for_user()` aufgerufen. Liefert `{"group:Kreditabteilung", "group:IT"}` fuer den User.

```python
def get_group_acls_for_user(user: User, db_session: Session) -> set[str]:
    """Alle Gruppen-ACL-Strings fuer einen User."""
    groups = (
        db_session.query(UserGroup.name)
        .join(User__UserGroup, UserGroup.id == User__UserGroup.user_group_id)
        .filter(User__UserGroup.user_id == user.id)
        .all()
    )
    return {prefix_user_group(name) for (name,) in groups}
```

**Funktion 2: `get_user_groups_for_cc_pair(cc_pair_id, db_session) -> list[str]`**

Wird von Core #3 Hook in `_get_access_for_document(s)()` aufgerufen. Liefert Gruppennamen fuer ein ConnectorCredentialPair.

```python
def get_user_groups_for_cc_pair(cc_pair_id: int, db_session: Session) -> list[str]:
    """Alle Gruppen die einem CC-Pair zugewiesen sind."""
    groups = (
        db_session.query(UserGroup.name)
        .join(UserGroup__ConnectorCredentialPair,
              UserGroup.id == UserGroup__ConnectorCredentialPair.user_group_id)
        .filter(UserGroup__ConnectorCredentialPair.cc_pair_id == cc_pair_id)
        .all()
    )
    return [name for (name,) in groups]
```

**Funktion 3: `sync_usergroup_acls(db_session) -> dict`**

Celery-Task-Logik. Findet Gruppen mit `is_up_to_date == False`, aktualisiert deren Dokument-ACLs in OpenSearch.

```python
def sync_usergroup_acls(db_session: Session) -> dict:
    """Sync-Job: Aktualisiert OpenSearch ACLs fuer geaenderte Gruppen."""
    pending_groups = (
        db_session.query(UserGroup)
        .filter(UserGroup.is_up_to_date == False)
        .all()
    )
    if not pending_groups:
        return {"synced": 0, "documents": 0}

    total_docs = 0
    for group in pending_groups:
        # Alle Dokument-IDs dieser Gruppe finden
        doc_ids = get_document_ids_for_group(group.id, db_session)
        # ACLs fuer jedes Dokument neu berechnen + OpenSearch updaten
        for doc_id in doc_ids:
            access = get_access_for_document(doc_id, db_session)  # nutzt Core #3 Hook
            update_opensearch_acl(doc_id, access)  # OpenSearch direkt updaten
            total_docs += 1
        # Gruppe als synced markieren
        group.is_up_to_date = True

    db_session.commit()
    return {"synced": len(pending_groups), "documents": total_docs}
```

**Funktion 4: `trigger_full_resync(db_session) -> dict`**

Admin-Endpoint-Logik. Markiert ALLE Gruppen als `is_up_to_date = False`.

```python
def trigger_full_resync(db_session: Session) -> dict:
    """Markiert alle Gruppen fuer Re-Sync."""
    count = (
        db_session.query(UserGroup)
        .update({UserGroup.is_up_to_date: False})
    )
    db_session.commit()
    return {"groups_queued": count}
```

### Celery-Task Registration

In `backend/ext/tasks/doc_access_sync.py`:

```python
from celery import shared_task

@shared_task(name="ext_doc_access_sync")
def ext_doc_access_sync_task() -> None:
    """Periodischer Sync: Gruppen-ACLs → OpenSearch."""
    from ext.config import EXT_DOC_ACCESS_ENABLED
    if not EXT_DOC_ACCESS_ENABLED:
        return

    from ext.services.doc_access import sync_usergroup_acls
    # ... DB Session holen, sync ausfuehren
```

**Schedule:** Alle 60 Sekunden via Celery Beat (oder manuell via Admin-Endpoint).

---

## Fehlerbehandlung

| Fehlerfall | HTTP | Verhalten |
|-----------|------|-----------|
| Feature Flag deaktiviert | 404 | Router nicht registriert (Standard ext-Pattern) |
| Nicht authentifiziert | 401 | Onyx Auth-Middleware |
| Kein Admin | 403 | `Depends(current_admin_user)` |
| OpenSearch nicht erreichbar | 500 | Logged, Retry beim naechsten Sync-Zyklus. Gruppe bleibt `is_up_to_date=False`. |
| Keine Gruppen vorhanden | 200 | `{ "synced": 0, "documents": 0 }` — kein Fehler |
| Dokument nicht im Index | Skip | Uebersprungen, kein Fehler (Dokument wird beim naechsten Indexing-Lauf korrekt angelegt) |
| DB-Fehler bei Sync | 500 | Transaction Rollback, `is_up_to_date` bleibt `False`, Retry naechster Zyklus |

### Core #3 Hook Fehlerbehandlung

```python
try:
    from ext.config import EXT_DOC_ACCESS_ENABLED
    if EXT_DOC_ACCESS_ENABLED:
        from ext.services.doc_access import get_group_acls_for_user
        acl_set.update(get_group_acls_for_user(user, db_session))
except ImportError:
    pass  # ext/ nicht vorhanden
except Exception:
    import logging
    logging.getLogger("ext").error("doc_access hook failed", exc_info=True)
    # NIEMALS Onyx-Funktionalitaet brechen — ACL ohne Gruppen ist restriktiver (sicher)
```

---

## Feature Flag Verhalten

### `EXT_DOC_ACCESS_ENABLED = true`

- Core #3 Hooks aktiv: Dokumente bekommen `group:` ACLs, User bekommen `group:` ACLs
- Celery-Task synced Gruppen-Aenderungen alle 60s
- Admin-Endpoints `/ext/doc-access/resync` und `/ext/doc-access/status` verfuegbar
- **Erstmalig:** Full Re-Sync noetig (bestehende Dokumente haben keine group: ACLs)

### `EXT_DOC_ACCESS_ENABLED = false` (Default)

- Core #3 Hooks inaktiv (try/except ImportError → pass)
- Celery-Task macht nichts (early return)
- Admin-Endpoints nicht registriert (404)
- Onyx verhält sich exakt wie ohne ext-access (kein Seiteneffekt)

---

## Betroffene Core-Dateien

### Core #3: `backend/onyx/access/access.py` (3 Stellen)

**Stelle 1: `_get_access_for_document()` (Zeile 28-34)**

Aenderung: `user_groups=[]` durch Gruppen-Lookup ersetzen.

```python
# VORHER (Zeile 28-34):
doc_access = DocumentAccess.build(
    user_emails=info[1] if info and info[1] else [],
    user_groups=[],
    ...
)

# NACHHER:
_user_groups = []
try:
    from ext.config import EXT_DOC_ACCESS_ENABLED
    if EXT_DOC_ACCESS_ENABLED and info and info[0]:
        from ext.services.doc_access import get_user_groups_for_document
        _user_groups = get_user_groups_for_document(document_id, db_session)
except ImportError:
    pass
except Exception:
    import logging
    logging.getLogger("ext").error("ext-access hook failed", exc_info=True)

doc_access = DocumentAccess.build(
    user_emails=info[1] if info and info[1] else [],
    user_groups=_user_groups,
    ...
)
```

**Stelle 2: `_get_access_for_documents()` (Zeile 69-76)**

Analog zu Stelle 1, aber fuer Batch-Verarbeitung. `user_groups=[]` durch Lookup ersetzen.

**Stelle 3: `_get_acl_for_user()` (Zeile 109-111)**

Aenderung: Gruppen-ACLs zum ACL-Set hinzufuegen.

```python
# VORHER (Zeile 109-111):
if user.is_anonymous:
    return {PUBLIC_DOC_PAT}
return {prefix_user_email(user.email), PUBLIC_DOC_PAT}

# NACHHER:
if user.is_anonymous:
    return {PUBLIC_DOC_PAT}
acl = {prefix_user_email(user.email), PUBLIC_DOC_PAT}
try:
    from ext.config import EXT_DOC_ACCESS_ENABLED
    if EXT_DOC_ACCESS_ENABLED:
        from ext.services.doc_access import get_group_acls_for_user
        acl.update(get_group_acls_for_user(user, db_session))
except ImportError:
    pass
except Exception:
    import logging
    logging.getLogger("ext").error("ext-access acl hook failed", exc_info=True)
return acl
```

**Warum Core #3 noetig ist:** Die Funktionen `_get_access_for_document(s)` und `_get_acl_for_user`
sind private FOSS-Funktionen die via `fetch_versioned_implementation` geladen werden. Es gibt
keinen anderen Extension-Point. Ohne diesen Patch bleiben `user_groups` immer leer und User
bekommen nie `group:` ACLs — Dokument-Zugriffskontrolle via Gruppen ist unmoeglich.

---

## Tests

### Unit Tests (`backend/ext/tests/test_doc_access.py`)

| # | Test | Beschreibung |
|---|------|-------------|
| 1 | `test_get_group_acls_for_user` | User in 2 Gruppen → 2 ACL-Strings |
| 2 | `test_get_group_acls_no_groups` | User in 0 Gruppen → leeres Set |
| 3 | `test_get_user_groups_for_document` | Dokument via CC-Pair in Gruppe → Gruppenname |
| 4 | `test_get_user_groups_no_assignment` | Dokument ohne Gruppen-Zuordnung → leere Liste |
| 5 | `test_sync_usergroup_acls_pending` | Gruppe mit `is_up_to_date=False` → Sync + True setzen |
| 6 | `test_sync_usergroup_acls_nothing_pending` | Alle Gruppen synced → 0 Aenderungen |
| 7 | `test_trigger_full_resync` | Alle Gruppen auf `is_up_to_date=False` markiert |
| 8 | `test_feature_flag_disabled` | `EXT_DOC_ACCESS_ENABLED=false` → Sync macht nichts |

### Integration Tests

| # | Test | Beschreibung |
|---|------|-------------|
| 1 | `test_resync_endpoint` | POST `/ext/doc-access/resync` → 200 + Gruppen markiert |
| 2 | `test_status_endpoint` | GET `/ext/doc-access/status` → korrekter Status |
| 3 | `test_resync_requires_admin` | BASIC User → 403 |
| 4 | `test_endpoints_404_when_disabled` | Flag=false → 404 |

### Feature Flag Tests

| # | Test | Beschreibung |
|---|------|-------------|
| 1 | `test_acl_with_flag_enabled` | User in Gruppe → Suche zeigt nur Gruppen-Dokumente |
| 2 | `test_acl_with_flag_disabled` | Gleicher User → Suche zeigt alles (FOSS-Verhalten) |
| 3 | `test_document_acl_with_flag_enabled` | Dokument bekommt `group:` ACL |
| 4 | `test_document_acl_with_flag_disabled` | Dokument bekommt `user_groups=[]` (FOSS) |

### Edge Cases

| # | Test | Beschreibung |
|---|------|-------------|
| 1 | `test_user_in_multiple_groups` | User in 3 Gruppen → alle 3 als ACL |
| 2 | `test_document_in_multiple_groups` | CC-Pair in 2 Gruppen → beide als ACL |
| 3 | `test_public_document_always_visible` | `is_public=True` → sichtbar auch ohne Gruppe |
| 4 | `test_admin_sees_everything` | Admin-User → alle Dokumente sichtbar |
| 5 | `test_anonymous_only_public` | Anonymer User → nur PUBLIC |
| 6 | `test_cc_pair_not_assigned_to_group` | Connector ohne Gruppe → nur `user_email:` ACL |
| 7 | `test_opensearch_unavailable_during_sync` | OpenSearch down → Gruppe bleibt pending, kein Crash |

---

## Aktivierungs-Checkliste

1. Feature Flag setzen: `EXT_DOC_ACCESS_ENABLED=true`
2. Server neustarten (wegen `fetch_versioned_implementation` LRU-Cache)
3. Gruppen muessen CC-Pairs zugewiesen sein (via ext-rbac Admin-UI)
4. Full Re-Sync ausloesen: `POST /ext/doc-access/resync`
5. Status pruefen: `GET /ext/doc-access/status` → alle Gruppen synced
6. Testen: User in Gruppe X sieht nur Dokumente von CC-Pairs die Gruppe X zugewiesen sind

---

## Risiken und Mitigationen

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| Bestehende Dokumente ohne group: ACLs | Mittel | Re-Sync Endpoint + Aktivierungs-Checkliste |
| Core #3 Merge-Risiko (Upstream) | Mittel | Identisches Hook-Pattern wie Core #11/#12 (bewaehrt) |
| Performance: DB-Query pro Suchanfrage | Niedrig | `get_group_acls_for_user` ist 1 einfacher JOIN, <1ms. Cache moeglich falls noetig. |
| Persona-Sichtbarkeit ≠ Dokument-ACL | Niedrig | Erwartetes Verhalten dokumentieren (Persona-Zugriff und Dokumentzugriff sind unabhaengig) |
| OpenSearch-Ausfall waehrend Sync | Niedrig | Gruppe bleibt `is_up_to_date=False`, Retry naechster Zyklus |

---

## Abhaengigkeiten

| Abhaengigkeit | Status | Blockierend? |
|--------------|--------|-------------|
| ext-rbac (Gruppen-CRUD) | ✅ Implementiert | Ja — Gruppen muessen existieren |
| Core #11 (persona.py Gruppen-Hook) | ✅ Gepatcht | Nein — unabhaengig |
| Core #12 (document_set.py Gruppen-Hook) | ✅ Gepatcht | Nein — unabhaengig |
| OpenSearch PROD | ✅ Live | Ja — ACLs werden dort gespeichert |
| Entra ID OIDC | ✅ Live | Ja — User muessen eingeloggt sein |

---

## Aufwandsschaetzung

| Arbeitspaket | Aufwand |
|-------------|---------|
| Core #3 Patch (3 Hooks) | 2h |
| ext/services/doc_access.py (Kernlogik) | 3h |
| ext/routers/doc_access.py (Endpoints) | 1h |
| Celery-Task + Registration | 1h |
| Tests (Unit + Integration) | 3h |
| Dokumentation (Patch, Runbook) | 1h |
| **Gesamt** | **~11h** |
