# Modulspezifikation: ext-rbac (Gruppenverwaltung)

**Dokumentstatus**: Entwurf
**Version**: 0.7
**Autor**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Datum**: 2026-03-23
**Status**: [x] Entwurf | [ ] Review | [ ] Freigegeben
**Prioritaet**: [x] Hoch | [ ] Kritisch | [ ] Normal | [ ] Niedrig

---

## Moduluebersicht

| Feld | Wert |
|------|------|
| **Modulname** | Gruppenverwaltung (RBAC) |
| **Modul-ID** | `ext_rbac` |
| **Version** | 0.1.0 |
| **Phase** | 4f |
| **Feature Flag** | `EXT_RBAC_ENABLED` (existiert in `backend/ext/config.py:17-19`) |
| **Abhaengigkeiten** | Phase 4a Extension Framework ✅, Phase 4b ext-branding ✅ (liefert `enterpriseSettings` fuer `useGroups` Hook) |

---

## Zweck und Umfang

### Zweck

VÖB hat ~100 Mitarbeitende in 16 Abteilungen. Ohne Gruppenverwaltung sehen alle User alle Connectoren, Agenten und LLM-Modelle. ext-rbac ermoeglicht:
- Abteilungen als Gruppen abbilden
- Abteilungsleiter als Curators mit eingeschraenkten Admin-Rechten
- LLM-Modelle, Connectoren und Agenten pro Gruppe zuweisen
- Dokument-Zugriffskontrolle vorbereiten (ext-access, Phase 4g)

### Im Umfang enthalten

- Backend: CRUD API fuer Gruppen auf **bestehenden** FOSS DB-Tabellen (`user_group`, `user__user_group`, etc.)
- Backend: User-zu-Gruppe Zuordnung mit `is_curator` Flag
- Backend: LLM-Provider, Connector, Agent/Persona zu Gruppe Zuordnung
- Backend: Curator-Berechtigung pro Gruppe validiert (CVE-2025-51479 Vermeidung)
- Frontend: Admin UI fuer Gruppenverwaltung (Create, Edit, Delete, Member-Management)
- Frontend: AdminSidebar-Link fuer Groups (Core #10 Patch-Update)
- Feature-Flag-Gating: Alles hinter `EXT_RBAC_ENABLED`

### Nicht im Umfang

- Entra ID Gruppen-Sync (OIDC `groups` Claim oder Microsoft Graph API) — spaetere Erweiterung
- SCIM Provisioning — nicht noetig bei ~100 Usern
- Document-Level Access Control — kommt in ext-access (Phase 4g)
- Automatisches Deprovisioning — spaetere Phase
- Per-Gruppen Token-Limits — ext-token Erweiterung, separates Ticket

### Validierte Annahmen (2026-03-23)

| Annahme | Validiert | Evidenz |
|---------|-----------|---------|
| API-Route `/manage/admin/user-group` frei | ✅ | Kein FOSS-Handler registriert, kein EE-Stub |
| `useGroups` Hook fetcht Gruppen | ✅ | ext-branding liefert `enterpriseSettings` → `!== null` → Hook aktiv |
| Vespa-Sync irrelevant | ✅ | OpenSearch nutzt Query-Time ACL Filtering — kein Index-Sync noetig |
| 12+ Frontend-Gates freigeschaltet | ✅ | `usePaidEnterpriseFeaturesEnabled()` prueft `enterpriseSettings` |
| `can_user_access_llm_provider()` funktioniert | ✅ | FOSS-Logik, prueft DB zur Laufzeit |
| **proxy.ts EE-Rewrite** | ❌ **Blocker** | `/admin/groups` wird auf `/ee/admin/groups` umgeschrieben (ext-branding setzt `SERVER_SIDE_ONLY__PAID_ENTERPRISE_FEATURES_ENABLED=true`). Loesung: Eigene Route `/admin/ext-groups` statt `/admin/groups` |
| CURATOR-Rolle blockiert in FOSS | ❌ | `validate_user_role_update()` blockiert `role=CURATOR`. ext-rbac `set-curator` muss auch `user.role` setzen |
| "Admin"/"Basic" Built-in Groups | ❌ | Keine DB-Rows — reine Frontend-Konstanten. GET gibt leere Liste zurueck |

### Abhaengige Module / Prerequisites

- [x] Phase 4a: Extension Framework Basis
- [x] Phase 4b: ext-branding (liefert `enterpriseSettings` — noetig damit `useGroups` Hook funktioniert)
- [x] Phase 3: Entra ID OIDC Login (DEV funktioniert)
- [ ] Keine weiteren Abhaengigkeiten

---

## Kritische Architekturentscheidung: Bestehende FOSS-Tabellen nutzen

### Erkenntnis aus Tiefenanalyse

Onyx FOSS hat das **komplette DB-Schema** fuer Gruppen. Was fehlt, ist ausschliesslich die CRUD-Geschaeftslogik (liegt in `backend/ee/onyx/db/user_group.py` — bei uns leer).

**Was FOSS bereits liefert (nutzen wir, aendern wir NICHT):**

| FOSS-Feature | Datei | Was es tut |
|-------------|-------|-----------|
| `UserGroup` Model | `db/models.py:4067-4120` | id, name, is_up_to_date, is_up_for_deletion, relationships |
| `User__UserGroup` M2M | `db/models.py:3971-3981` | user_group_id, user_id, **is_curator** |
| `UserGroup__ConnectorCredentialPair` | `db/models.py:3984-4007` | Connector-Zuordnung mit is_current |
| `Persona__UserGroup` | `db/models.py:4009-4015` | Agent/Persona-Zuordnung |
| `LLMProvider__UserGroup` | `db/models.py:4034-4042` | LLM-Provider-Zuordnung |
| `DocumentSet__UserGroup` | `db/models.py:4045-4053` | DocumentSet-Zuordnung |
| `Credential__UserGroup` | `db/models.py:4056-4064` | Credential-Zuordnung |
| `TokenRateLimit__UserGroup` | `db/models.py:4143-4151` | Token-Limit-Zuordnung |
| `can_user_access_llm_provider()` | `db/llm.py:101-147` | LLM-Zugriffspruefung pro Gruppe |
| `fetch_user_group_ids()` | `db/llm.py:79-98` | User-Gruppen-IDs abfragen |
| `batch_get_user_groups()` | `db/users.py:421-443` | Bulk-Abfrage User→Gruppen |
| `current_curator_or_admin_user` | `auth/users.py:1630-1639` | Auth-Dependency fuer Curator-Endpoints |
| GroupsPage (Liste) | `web/src/refresh-pages/admin/GroupsPage/` | READ-ONLY Gruppenliste |
| `useGroups` Hook | `web/src/hooks/useGroups.ts` | SWR-basierter Gruppen-Fetch |
| `UserGroup` TypeScript Interface | `web/src/lib/types.ts:472-482` | Frontend-Typdefinition |

**Was FOSS NICHT kann (bauen wir in ext-rbac):**

| Feature | Warum fehlt es |
|---------|---------------|
| Gruppen-CRUD API | Nur in EE (`backend/ee/onyx/db/user_group.py` — bei uns leer) |
| User-zu-Gruppe Zuordnung | Nur in EE |
| Connector/LLM/Agent-zu-Gruppe Zuordnung | Nur in EE |
| Gruppen-Detail/Edit UI | Nur in EE (`web/src/app/ee/admin/groups/[groupId]/`) |
| Create Group Modal | Nur in EE |

### Warum KEINE neuen DB-Tabellen

Alle 8 M2M-Tabellen existieren bereits in FOSS mit den richtigen Spalten und Foreign Keys. Eine neue Migration wuerde:
- Redundante Tabellen schaffen (Sync-Problem)
- Bestehende FOSS-Logik (`can_user_access_llm_provider`) nicht triggern
- Upstream-Merges verkomplizieren

Stattdessen: Eigene SQLAlchemy-Queries auf bestehende Tabellen in `backend/ext/services/`.

---

## Architektur

### Komponenten-Uebersicht

```
┌─────────────────────────────────────────────────────────────┐
│                Admin UI (/admin/groups)                       │
│  ┌─────────────┬──────────────┬──────────────────────────┐  │
│  │ Gruppenliste │ Gruppe       │ Gruppe erstellen         │  │
│  │ (FOSS Page) │ Detail/Edit  │ (ext Modal)              │  │
│  │             │ (ext Page)   │                          │  │
│  └──────┬──────┴──────┬───────┴────────────┬─────────────┘  │
│         │             │                    │                  │
└─────────┼─────────────┼────────────────────┼────────────────┘
          │             │                    │
          ↓             ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│  ext-rbac Backend API (backend/ext/routers/rbac.py)          │
│                                                              │
│  GET    /api/manage/admin/user-group          → Liste        │
│  POST   /api/manage/admin/user-group          → Erstellen    │
│  PATCH  /api/manage/admin/user-group/{id}     → Aktualisieren│
│  DELETE /api/manage/admin/user-group/{id}     → Loeschen     │
│  POST   /api/manage/admin/user-group/{id}/add-users          │
│  POST   /api/manage/admin/user-group/{id}/set-curator        │
│                                                              │
│  Auth: current_admin_user (Create/Delete)                    │
│        current_curator_or_admin_user (Read/Update/AddUsers)  │
│        + Per-Gruppe Curator-Validierung (CVE-2025-51479)     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  PostgreSQL (bestehende FOSS-Tabellen)                       │
│                                                              │
│  user_group ←→ user__user_group (is_curator)                 │
│       ↕              ↕                                       │
│  persona__user_group                                         │
│  llm_provider__user_group                                    │
│  user_group__connector_credential_pair                       │
│  document_set__user_group                                    │
│  credential__user_group                                      │
│  token_rate_limit__user_group                                │
└─────────────────────────────────────────────────────────────┘
```

### Datenfluss

**Gruppen-CRUD:**
1. Admin erstellt Gruppe → `POST /api/manage/admin/user-group`
2. ext-rbac INSERT in `user_group` Tabelle
3. Admin weist User zu → `POST .../add-users`
4. ext-rbac INSERT in `user__user_group`
5. Admin weist LLM-Provider zu → `PATCH .../user-group/{id}` mit `cc_pair_ids`
6. ext-rbac INSERT in `user_group__connector_credential_pair`

**Automatischer Effekt (kein ext-rbac Code noetig):**
- `can_user_access_llm_provider()` prueft `llm_provider__user_group` → Modell-Zugriff eingeschraenkt
- Bestehende GroupsPage zeigt Gruppen an (fetcht `/api/manage/admin/user-group`)
- `useGroups` Hook liefert Gruppen (da ext-branding `enterpriseSettings` bereitstellt)

---

## API-Spezifikation

### API-Pfad-Entscheidung

**Pfad: `/manage/admin/user-group`** (wird zu `/api/manage/admin/user-group` nach Prefix-Prepend)

**Begruendung:** Die bestehende GroupsPage (`web/src/refresh-pages/admin/GroupsPage/svc.ts`) fetcht von genau diesem Pfad. Die TypeScript-Interfaces (`UserGroup` in `types.ts`) erwarten genau dieses Response-Format. Eigener `/ext/rbac/`-Pfad wuerde ein komplett neues Frontend erfordern.

### Endpoints

#### Endpoint 1: `GET /api/manage/admin/user-group`

**Beschreibung**: Alle Gruppen auflisten (inkl. Members, Curators, zugewiesene Ressourcen).

**Authentifizierung**: `current_curator_or_admin_user`
- ADMIN sieht alle Gruppen
- CURATOR/GLOBAL_CURATOR sieht nur Gruppen in denen er Curator ist

**Query Parameter**: Keine

**Response (200)**:

```json
[
  {
    "id": 1,
    "name": "Geschaeftsleitung",
    "users": [
      {"id": "uuid", "email": "henkel@voeb-service.de", "role": "BASIC"}
    ],
    "curator_ids": ["uuid-of-curator"],
    "cc_pairs": [
      {"id": 1, "name": "SharePoint Geschaeftsleitung", "connector": {...}}
    ],
    "document_sets": [],
    "personas": [
      {"id": 1, "name": "VÖB Assistent"}
    ],
    "is_up_to_date": true,
    "is_up_for_deletion": false
  }
]
```

**Kompatibilitaet**: Exakt das `UserGroup` Interface aus `web/src/lib/types.ts:472-482`.

#### Endpoint 2: `POST /api/manage/admin/user-group`

**Beschreibung**: Neue Gruppe erstellen.

**Authentifizierung**: `current_admin_user` (nur Admins duerfen Gruppen erstellen)

**Request Body**:

```json
{
  "name": "Geschaeftsleitung",
  "user_ids": ["uuid-1", "uuid-2"],
  "cc_pair_ids": [1, 3]
}
```

| Feld | Typ | Pflicht | Validierung |
|------|-----|---------|-------------|
| `name` | string | Ja | 1-255 Zeichen, unique |
| `user_ids` | list[UUID] | Nein (default: []) | Existierende User-IDs |
| `cc_pair_ids` | list[int] | Nein (default: []) | Existierende CC-Pair-IDs |

**Response (201)**: `UserGroup` Objekt (wie GET-Response, einzeln)

#### Endpoint 3: `PATCH /api/manage/admin/user-group/{user_group_id}`

**Beschreibung**: Gruppe aktualisieren (Members und Connector-Zuordnungen).

**Authentifizierung**: `current_curator_or_admin_user`
- ADMIN: Kann jede Gruppe aendern
- CURATOR: Nur Gruppen in denen `is_curator=True` (**CVE-2025-51479 Fix**)

**Path Parameter**: `user_group_id` (int)

**Request Body**:

```json
{
  "user_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "cc_pair_ids": [1, 3, 5]
}
```

| Feld | Typ | Pflicht | Validierung |
|------|-----|---------|-------------|
| `user_ids` | list[UUID] | Ja | Existierende User-IDs (ersetzt komplette User-Liste) |
| `cc_pair_ids` | list[int] | Ja | Existierende CC-Pair-IDs (ersetzt komplette CC-Pair-Liste) |

**Wichtig**: Ersetzt die komplette Zuordnung (PUT-Semantik auf die Unterliste). Fehlende IDs werden entfernt, neue hinzugefuegt.

**Response (200)**: Aktualisiertes `UserGroup` Objekt

#### Endpoint 4: `DELETE /api/manage/admin/user-group/{user_group_id}`

**Beschreibung**: Gruppe zum Loeschen markieren (`is_up_for_deletion=True`).

**Authentifizierung**: `current_admin_user` (nur Admins duerfen Gruppen loeschen)

**Path Parameter**: `user_group_id` (int)

**Deletion-Strategie (validiert 2026-03-23):**

Die FOSS-Celery-Jobs raeumen `is_up_for_deletion=True` Gruppen **NICHT** auf (EE-only). Daher implementieren wir **hartes DELETE** mit Cascade:

1. Alle M2M-Eintraege loeschen (`user__user_group`, `user_group__connector_credential_pair`, `persona__user_group`, `llm_provider__user_group`, `document_set__user_group`, `credential__user_group`, `token_rate_limit__user_group`)
2. `user_group` Row loeschen
3. Curator-Demotion: Wenn geloeschte Gruppe die letzte Curator-Gruppe eines Users war → User-Rolle auf BASIC setzen (siehe "Curator-Demotion" Abschnitt)

**Kein Soft-Delete**, weil: (a) keine FOSS-Cleanup-Jobs existieren, (b) Soft-Delete-Rows wuerden in Queries auftauchen wenn nicht explizit gefiltert, (c) bei ~16 Gruppen ist Cascade-Delete performant und sicher.

**Response (204)**: Kein Body

#### Endpoint 5: `POST /api/manage/admin/user-group/{user_group_id}/add-users`

**Beschreibung**: User zu einer Gruppe hinzufuegen (additiv, ohne bestehende zu entfernen).

**Authentifizierung**: `current_curator_or_admin_user` + Per-Gruppe Validierung

**Path Parameter**: `user_group_id` (int)

**Request Body**:

```json
{
  "user_ids": ["uuid-1", "uuid-2"]
}
```

**Response (200)**: Kein Body (oder aktualisiertes `UserGroup` Objekt)

#### Endpoint 6: `POST /api/manage/admin/user-group/{user_group_id}/set-curator`

**Beschreibung**: Curator-Status fuer einen User in einer Gruppe setzen/entfernen.

**Authentifizierung**: `current_admin_user` (nur Admins duerfen Curators ernennen)

**Path Parameter**: `user_group_id` (int)

**Request Body**:

```json
{
  "user_id": "uuid",
  "is_curator": true
}
```

**Wichtig (validiert 2026-03-23):** Dieser Endpoint muss ZWEI Dinge tun:
1. `is_curator` in `user__user_group` setzen
2. `user.role` auf `CURATOR` setzen (wenn `is_curator=True`) bzw. auf `BASIC` zuruecksetzen (wenn letzte Curator-Gruppe, siehe Curator-Demotion)

**Grund:** Die FOSS-API blockiert `role=CURATOR` in `validate_user_role_update()` (`backend/onyx/db/users.py:71-76`). Es gibt keinen anderen Weg in FOSS die CURATOR-Rolle zu setzen. ext-rbac muss `user.role` direkt in der DB setzen (SQLAlchemy, kein API-Call).

User muss bereits Member der Gruppe sein.

**Response (200)**: Kein Body

#### Endpoint 7: `GET /api/manage/user-groups/minimal` (NEU — validiert 2026-03-23)

**Beschreibung**: Minimale Gruppenliste fuer Non-Admin Kontexte (Agent-Editor, Connector-Editor, LLM-Config).

**Authentifizierung**: `current_user` (jeder eingeloggte User)

**Warum noetig:** `useShareableGroups()` und `useUserGroups()` nutzen diesen Endpoint. Er wird aufgerufen in:
- Agent/Persona-Editor (`web/src/refresh-pages/AgentEditorPage.tsx`)
- Connector AccessTypeGroupSelector
- LLM-Config Modal (`web/src/sections/modals/llmConfig/shared.tsx`)
- Document Set Erstellung

**Response (200)**:

```json
[
  {"id": 1, "name": "Geschaeftsleitung"},
  {"id": 2, "name": "Rechenzentrum"}
]
```

**Hinweis**: Nur `id` und `name` — keine Members, Curators oder Ressourcen. Admin sieht alle Gruppen, BASIC User sieht nur eigene Gruppen.

### Bekannte UX-Problematik: Group-Selektoren auf DEV (validiert 2026-03-23)

**Status Quo:** Da ext-branding `enterpriseSettings` liefert, sind Group-Selektoren **bereits jetzt auf DEV sichtbar** in:
- Agent/Persona-Editor (`IsPublicGroupSelector`)
- Connector-Erstellung (`AccessTypeGroupSelector`)
- Document Set-Erstellung
- LLM-Config Modal

Alle rufen `/api/manage/admin/user-group` bzw. `/api/manage/user-groups/minimal` → **404**. User sehen leere Dropdowns.

**Sofort-Effekt von ext-rbac Deploy:** Sobald die 7 Endpoints live sind, funktionieren diese Selektoren automatisch — kein Frontend-Code noetig.

**FOSS-Limitationen bei Gruppen-Zuordnung zu Ressourcen (validiert 2026-03-23):**

| Ressource | Gruppen-Zuordnung (Schreiben) | Gruppen-Filterung (Lesen) | Code-Stelle |
|-----------|-------------------------------|--------------------------|-------------|
| **LLM Provider** | ✅ Funktioniert | ✅ Funktioniert | `db/llm.py:35-54` |
| **Persona/Agent** | ❌ `NotImplementedError` | ✅ Funktioniert | `db/persona.py:244-245` |
| **Document Set** | ❌ `NotImplementedError` | ✅ Funktioniert | `db/document_set.py:179-181` |
| **Connector** | ⚠️ Nur Mock-Credential-Flow | ✅ Funktioniert | `connector.py:1525` vs `:1564` |

**Persona/DocSet-Blockade:** FOSS wirft absichtlich `NotImplementedError("Onyx MIT does not support group-based sharing")` wenn `group_ids` nicht leer ist. Das Lesen (Access-Filtering per Gruppen-Join) funktioniert bereits.

**Connector-Einschraenkung:** Standard-Create (`POST /admin/connector`) verwirft `groups` silently. Mock-Credential-Route speichert korrekt.

**Entscheidung (Niko, 2026-03-23):** Core-Dateien-Liste von 10 auf 12 erweitert:
- `persona.py` als **Core #11** (Mittel-Hoch Risiko, 14 Commits/3 Mo, Upstream-Monitoring noetig)
- `document_set.py` als **Core #12** (Niedriges Risiko, 5 Commits/3 Mo, stabil)
- **Aktivierung in Phase 4g (ext-access)**, nicht Phase 4f (ext-rbac)
- Phase 4f liefert Gruppen-CRUD + LLM-Provider-Zuordnung (funktioniert in FOSS)
- #11 + #12 bereits gepatcht (ext-rbac). Phase 4g patcht #3 (access.py) fuer Document-Level ACLs

### Error Handling

| Fehler | HTTP-Status | Beschreibung |
|--------|------------|-------------|
| Gruppenname existiert bereits | 409 | Conflict — Name muss unique sein |
| Gruppe nicht gefunden | 404 | user_group_id existiert nicht |
| User nicht gefunden | 404 | user_id in Request existiert nicht |
| CC-Pair nicht gefunden | 404 | cc_pair_id existiert nicht |
| User nicht Member der Gruppe | 400 | set-curator: User muss erst Member sein |
| Nicht authentifiziert | 401 | Onyx Standard-Auth |
| Kein Admin/Curator | 403 | Rolle nicht ausreichend |
| Curator ohne Berechtigung fuer Gruppe | 403 | CVE-2025-51479: Curator ist nicht Curator dieser Gruppe |
| Ungueltige Eingabe | 400 | Pydantic-Validierung (name leer, etc.) |
| ~~Built-in Gruppe aendern~~ | — | ~~"Admin" und "Basic" existieren nicht als DB-Rows~~ (rein Frontend-Konstanten in `utils.ts`, keine Schutzlogik noetig) |
| Feature Flag deaktiviert | 404 | Router nicht registriert |
| DB/Server-Fehler | 500 | Generische Fehlermeldung |

---

## Datenbankschema

### Keine neuen Tabellen

ext-rbac erstellt **KEINE neuen Tabellen** und **KEINE Alembic Migration**. Alle benoetigten Tabellen existieren in FOSS:

| Tabelle | Primaerschluessel | Relevante Spalten | Verwendet fuer |
|---------|-------------------|-------------------|---------------|
| `user_group` | `id` (serial) | `name` (unique), `is_up_to_date`, `is_up_for_deletion` | Gruppen-Entitaet |
| `user__user_group` | (`user_group_id`, `user_id`) | `is_curator` (bool) | User-Zuordnung + Curator-Flag |
| `user_group__connector_credential_pair` | (`user_group_id`, `cc_pair_id`, `is_current`) | `is_current` (bool) | Connector-Zuordnung |
| `persona__user_group` | (`persona_id`, `user_group_id`) | — | Agent-Zuordnung |
| `llm_provider__user_group` | (`llm_provider_id`, `user_group_id`) | — | LLM-Modell-Zuordnung |
| `document_set__user_group` | (`document_set_id`, `user_group_id`) | — | DocumentSet-Zuordnung |
| `credential__user_group` | (`credential_id`, `user_group_id`) | — | Credential-Zuordnung |
| `token_rate_limit__user_group` | (`rate_limit_id`, `user_group_id`) | — | Token-Limit-Zuordnung |

### Document Index: OpenSearch mit Query-Time ACL Filtering

**PROD nutzt OpenSearch als Primary Document Index** (seit 2026-03-22). Vespa laeuft im Zombie-Mode (100m/512Mi, nur Celery Readiness Check).

**Warum Vespa-Sync irrelevant ist:**
OpenSearch speichert ACL-Felder pro Dokument (`access_control_list` als keyword-Array, `public` als boolean), filtert aber **zur Query-Zeit** — nicht durch Index-Sync. Bei jeder Suche wird `get_acl_for_user()` aufgerufen, das die Berechtigungen live aus der DB liest und als Filter an den OpenSearch-Query anhaengt.

| Aspekt | Vespa (alt) | OpenSearch (aktuell) |
|--------|-------------|---------------------|
| ACL-Filterung | Index-Zeit (periodischer Sync) | **Query-Zeit (live aus DB)** |
| Gruppen-Aenderungen | Verzoegert (Sync-Lag) | **Sofort wirksam** |
| Sync-Task noetig | Ja (`check_for_vespa_sync`) | **Nein** |
| `is_up_to_date` Flag | Relevant | **Irrelevant fuer ACLs** |

**Konsequenz fuer ext-rbac:**
- `is_up_to_date` setzen wir trotzdem (korrekte Semantik, schadet nicht)
- Kein Vespa-Sync-Workaround noetig — weder jetzt noch in Phase 4g
- ext-access (Phase 4g) muss `get_acl_for_user()` in `access.py` (CORE #3) erweitern: Gruppen-IDs aus DB laden und als `group_`-Prefix in den ACL-Filter einfuegen. Das ist ein Hook in einer bereits erlaubten Core-Datei.

**FOSS-Limitation (betrifft Phase 4g, NICHT 4f):**
`_get_acl_for_user()` in `backend/onyx/access/access.py` gibt aktuell nur `{email, PUBLIC}` zurueck — **ohne Gruppen**. OpenSearch-Schema unterstuetzt `group_`-Prefixes bereits, aber die FOSS-Logik fuellt sie nicht. Das ist die Aufgabe von ext-access.

**Referenz:** `backend/onyx/document_index/opensearch/search.py` (ACL-Filter), `backend/onyx/access/access.py:70-71` ("MIT version will wipe all groups")

---

## Backend-Dateien

### Neue Dateien in `backend/ext/`

| Datei | Zweck |
|-------|-------|
| `ext/schemas/rbac.py` | Pydantic Request/Response Schemas |
| `ext/services/rbac.py` | Business Logic: CRUD, Validierung, Curator-Check |
| `ext/routers/rbac.py` | FastAPI Router (6 Endpoints) |
| `ext/tests/test_rbac.py` | Unit Tests fuer Service-Layer |

### Schemas: `ext/schemas/rbac.py`

```python
from pydantic import BaseModel, Field
from uuid import UUID


class UserGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    user_ids: list[UUID] = Field(default_factory=list)
    cc_pair_ids: list[int] = Field(default_factory=list)


class UserGroupUpdate(BaseModel):
    user_ids: list[UUID]
    cc_pair_ids: list[int]


class AddUsersRequest(BaseModel):
    user_ids: list[UUID] = Field(..., min_length=1)


class SetCuratorRequest(BaseModel):
    user_id: UUID
    is_curator: bool
```

Response-Schema: Wir nutzen das bestehende `UserGroup` Interface-Format (dict-basiert), kein eigenes Response-Model. Das garantiert Kompatibilitaet mit der GroupsPage.

### Service-Layer: `ext/services/rbac.py`

Kernfunktionen:

```python
def fetch_all_user_groups(
    db_session: Session,
    user: User,
    only_curator_groups: bool = False,
) -> list[dict]:
    """Alle Gruppen laden. Curator sieht nur seine Gruppen."""

def fetch_user_group_by_id(
    db_session: Session,
    user_group_id: int,
) -> UserGroup:
    """Einzelne Gruppe laden. Wirft 404 wenn nicht gefunden."""

def create_user_group(
    db_session: Session,
    create_request: UserGroupCreate,
) -> dict:
    """Gruppe erstellen + initiale User/CC-Pair Zuordnung."""

def update_user_group(
    db_session: Session,
    user_group_id: int,
    update_request: UserGroupUpdate,
    user: User,
) -> dict:
    """Gruppe aktualisieren. Curator-Check wenn nicht Admin."""

def mark_user_group_for_deletion(
    db_session: Session,
    user_group_id: int,
) -> None:
    """Gruppe zum Loeschen markieren (is_up_for_deletion=True)."""

def add_users_to_group(
    db_session: Session,
    user_group_id: int,
    user_ids: list[UUID],
) -> None:
    """User additiv zur Gruppe hinzufuegen."""

def set_curator_status(
    db_session: Session,
    user_group_id: int,
    user_id: UUID,
    is_curator: bool,
) -> None:
    """Curator-Status fuer User in Gruppe setzen.
    Setzt auch user.role auf CURATOR (wenn is_curator=True)
    oder demoted zu BASIC (wenn letzte Curator-Gruppe entfernt)."""

def validate_curator_for_group(
    db_session: Session,
    user: User,
    user_group_id: int,
) -> None:
    """CVE-2025-51479: Prueft ob Curator Berechtigung fuer diese Gruppe hat.
    Admin: immer erlaubt. Curator: nur wenn is_curator=True in user__user_group.
    Wirft 403 wenn nicht berechtigt."""

def _build_user_group_response(
    db_session: Session,
    user_group: UserGroup,
) -> dict:
    """Baut Response-Dict kompatibel mit TypeScript UserGroup Interface."""
```

### CVE-2025-51479 Vermeidung

**Problem (in Onyx EE):** PATCH-Endpoint validierte nicht, ob ein Curator die Berechtigung fuer die spezifische Gruppe hat. Ein Curator konnte jede Gruppe aendern.

**Unsere Loesung:** `validate_curator_for_group()` wird in JEDEM Curator-Endpoint aufgerufen:

```python
def validate_curator_for_group(
    db_session: Session,
    user: User,
    user_group_id: int,
) -> None:
    if user.role == UserRole.ADMIN:
        return  # Admins duerfen alles

    if user.role == UserRole.GLOBAL_CURATOR:
        # Global Curator: pruefe ob Member der Gruppe
        membership = db_session.query(User__UserGroup).filter(
            User__UserGroup.user_group_id == user_group_id,
            User__UserGroup.user_id == user.id,
        ).first()
        if not membership:
            raise HTTPException(403, "Not a member of this group")
        return

    if user.role == UserRole.CURATOR:
        # Curator: pruefe ob is_curator=True fuer DIESE Gruppe
        membership = db_session.query(User__UserGroup).filter(
            User__UserGroup.user_group_id == user_group_id,
            User__UserGroup.user_id == user.id,
            User__UserGroup.is_curator == True,
        ).first()
        if not membership:
            raise HTTPException(403, "Not a curator of this group")
        return

    raise HTTPException(403, "Insufficient permissions")
```

### Curator-Demotion (validiert 2026-03-23)

**Problem:** Onyx hat KEINE automatische Curator-Demotion in FOSS. `remove_curator_status__no_commit()` existiert nur in EE (bei uns leer → noop). Wenn ein CURATOR aus seiner letzten Curator-Gruppe entfernt wird, behaelt er `role=CURATOR` aber hat leere Ergebnis-Sets bei allen Curator-Queries — ein verwirrender Zustand.

**Unsere Loesung: Explizite Demotion in ext-rbac.**

```python
def _check_and_demote_curator(
    db_session: Session,
    user_id: UUID,
) -> None:
    """Prueft ob User noch Curator in mindestens einer Gruppe ist.
    Wenn nicht: Rolle auf BASIC demoten.
    GLOBAL_CURATOR wird NICHT demoted (hat andere Semantik)."""
    user = db_session.get(User, user_id)
    if not user or user.role not in (UserRole.CURATOR,):
        return  # Nur CURATOR pruefen, nicht GLOBAL_CURATOR oder ADMIN

    remaining = db_session.query(User__UserGroup).filter(
        User__UserGroup.user_id == user_id,
        User__UserGroup.is_curator == True,
    ).count()

    if remaining == 0:
        user.role = UserRole.BASIC
        logger.info(f"[EXT-RBAC] User {user.email} demoted to BASIC (no curator groups left)")
```

**Aufgerufen bei:**
- `update_user_group()` wenn User-Liste sich aendert (und Curators entfernt werden koennten)
- `mark_user_group_for_deletion()` / Gruppen-Delete (alle Members verlieren Zuordnung)
- `set_curator_status(is_curator=False)` explizit

### Built-in Groups (validiert 2026-03-23)

**"Admin" und "Basic" existieren NICHT als DB-Rows.** Sie sind reine Frontend-Konstanten in `web/src/refresh-pages/admin/GroupsPage/utils.ts:3`. Konsequenz:
- GET-Endpoint gibt leere Liste zurueck bis Gruppen erstellt werden
- Kein Schutz gegen Loeschen noetig
- Frontend zeigt "Admin"/"Basic" als virtuelle Gruppen wenn der Name zufaellig matcht

---

## Core-Aenderungen

### CORE #10: `web/src/sections/sidebar/AdminSidebar.tsx`

**Bereits gepatcht fuer**: ext-branding (Billing→Branding), ext-token (Token Usage Link), ext-prompts (System Prompts Link), EE-Cleanup (ausgegraute Items ausblenden).

**Neue Aenderung**: Eigenen "Gruppen"-Link bei `EXT_RBAC_ENABLED` unter Permissions einfuegen. Zeigt auf `/admin/ext-groups` (NICHT `/admin/groups` wegen proxy.ts EE-Rewrite).

**Aktuelle Zeilen 133-137:**
```typescript
if (!isCurator) {
  add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.USERS);
  if (enableEnterprise) {
    add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.GROUPS);
    add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.SCIM);
  }
}
```

**Neue Zeilen:**
```typescript
if (!isCurator) {
  add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.USERS);
  if (extRbacEnabled) {
    add(SECTIONS.PERMISSIONS, {
      name: "Gruppen",
      path: "/admin/ext-groups",
      icon: SvgUsers,
    });
  }
  if (enableEnterprise) {
    add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.GROUPS);
    add(SECTIONS.PERMISSIONS, ADMIN_ROUTES.SCIM);
  }
}
```

**Zusaetzlich**: `extRbacEnabled` Variable + SvgUsers Import oben im Component:
```typescript
const extRbacEnabled = process.env.NEXT_PUBLIC_EXT_RBAC_ENABLED === "true";
```

**Patch-Update**: Bestehender `AdminSidebar.tsx.patch` wird kumulativ erweitert (alle ext-Hooks in einem Patch).

### Keine weiteren Core-Aenderungen

- **CORE #1 (main.py):** Nicht noetig — Router-Registration laeuft ueber `register_ext_routers()` (bereits gehooked)
- **CORE #2 (multi_llm.py):** Nicht noetig — kein LLM-Hook fuer Gruppen
- **CORE #3 (access.py):** Nicht noetig — kommt erst mit ext-access (Phase 4g)
- **CORE #5 (header/):** Nicht noetig
- **CORE #6 (constants.ts):** Nicht noetig

---

## Frontend-Komponenten

### Route-Entscheidung: `/admin/ext-groups` (NICHT `/admin/groups`)

**Blocker (validiert 2026-03-23):** `web/src/proxy.ts` (Zeile 82-86) schreibt `/admin/groups` auf `/ee/admin/groups` um, weil `SERVER_SIDE_ONLY__PAID_ENTERPRISE_FEATURES_ENABLED=true` (gesetzt durch `EXT_BRANDING_ENABLED=true`). Die FOSS GroupsPage ist daher NICHT erreichbar unter `/admin/groups`.

**Loesung:** Eigene Route `/admin/ext-groups` — analog zu `/admin/ext-branding` und `/admin/ext-token`:
- Kein Eintrag in `EE_ROUTES` → kein Proxy-Rewrite
- Kein Onyx-Code modifiziert (proxy.ts bleibt unveraendert)
- Zero Upstream-Merge-Risiko
- AdminSidebar-Patch zeigt auf `/admin/ext-groups`

**Konsequenz:** Die FOSS GroupsPage (`web/src/refresh-pages/admin/GroupsPage/`) wird NICHT verwendet. Stattdessen bauen wir eine eigene Gruppenliste in `web/src/ext/`. Dies gibt uns auch volle Kontrolle ueber CRUD-UI (Create-Modal, Detail-Seite, Delete-Button), die in der FOSS GroupsPage fehlen.

### Neue Frontend-Dateien

| Datei | Zweck |
|-------|-------|
| `web/src/app/admin/ext-groups/page.tsx` | Route fuer Gruppenliste (analog ext-token) |
| `web/src/app/admin/ext-groups/[groupId]/page.tsx` | Route fuer Gruppen-Detail |
| `web/src/ext/components/rbac/GroupsListPage.tsx` | Gruppenliste mit Create-Button + Suche |
| `web/src/ext/components/rbac/GroupDetailPage.tsx` | Gruppen-Detail + Edit UI |
| `web/src/ext/components/rbac/GroupCreateModal.tsx` | Modal zum Erstellen neuer Gruppen |
| `web/src/ext/components/rbac/GroupMemberTable.tsx` | User-Tabelle mit Curator-Toggle |
| `web/src/ext/components/rbac/AddConnectorForm.tsx` | Connector-Zuordnung |
| `web/src/ext/components/rbac/types.ts` | Lokale TypeScript-Interfaces |
| `web/src/ext/components/rbac/svc.ts` | API-Client Funktionen (fetch-Wrapper) |

### Gruppenliste (`/admin/ext-groups`)

**Route-Datei** (`web/src/app/admin/ext-groups/page.tsx`):
```typescript
export { default } from "@/ext/components/rbac/GroupsListPage";
```

**GroupsListPage** zeigt:
- Gruppenliste via `GET /api/manage/admin/user-group` (useSWR)
- Suchfunktion (Filter nach Name)
- "Neue Gruppe" Button → oeffnet GroupCreateModal
- GroupCards mit Klick-Navigation zu Detail-Seite
- Member-Count, Connector-Count pro Gruppe

### Gruppen-Detail-Seite (`/admin/ext-groups/[groupId]`)

**Route-Datei** (`web/src/app/admin/ext-groups/[groupId]/page.tsx`):
```typescript
export { default } from "@/ext/components/rbac/GroupDetailPage";
```

**GroupDetailPage** zeigt:
- Gruppenname (editierbar fuer Admin)
- Member-Tabelle mit Curator-Toggle
- Connector-Zuordnung
- Agent/Persona-Zuordnung
- "Gruppe loeschen" Button (nur Admin)

### i18n

Neue Strings ins Dictionary (`web/src/ext/i18n/translations.ts`):
- "New Group" → "Neue Gruppe"
- "Group Members" → "Gruppenmitglieder"
- "Add Members" → "Mitglieder hinzufuegen"
- "Set as Curator" → "Als Curator setzen"
- "Remove from Group" → "Aus Gruppe entfernen"
- "Delete Group" → "Gruppe loeschen"
- "Connectors" (im Gruppen-Kontext)
- "Agents" (im Gruppen-Kontext)
- Ca. 15-20 neue Strings

---

## Konfiguration

### Environment Variables

| Variable | Typ | Pflicht | Standard | Beschreibung |
|----------|-----|---------|---------|-------------|
| `EXT_ENABLED` | bool | Ja | `false` | Master-Switch (bereits vorhanden) |
| `EXT_RBAC_ENABLED` | bool | Ja | `false` | Gruppen-Modul aktivieren (bereits in config.py) |
| `NEXT_PUBLIC_EXT_RBAC_ENABLED` | bool | Nein | `false` | Frontend-Flag fuer AdminSidebar |

### Feature Flag Verhalten

**Wenn aktiviert (`EXT_RBAC_ENABLED=true`):**
- 6 API-Endpoints unter `/api/manage/admin/user-group` registriert
- Groups-Link in AdminSidebar sichtbar
- Gruppen-Detail-Seite erreichbar
- Alle CRUD-Operationen verfuegbar
- `can_user_access_llm_provider()` greift automatisch (FOSS-Logik)

**Wenn deaktiviert (`EXT_RBAC_ENABLED=false`):**
- Kein Router registriert → 404 auf alle Gruppen-Endpoints
- Groups-Link in AdminSidebar versteckt (es sei denn `enableEnterprise` aktiv)
- Onyx funktioniert unveraendert
- Keine Seiteneffekte

### Helm Values

```yaml
# deployment/helm/values/values-dev.yaml (ergaenzen)
configMap:
  env:
    EXT_RBAC_ENABLED: "true"
webConfigMap:
  env:
    NEXT_PUBLIC_EXT_RBAC_ENABLED: "true"

# deployment/helm/values/values-prod.yaml (ergaenzen nach Test)
configMap:
  env:
    EXT_RBAC_ENABLED: "true"
webConfigMap:
  env:
    NEXT_PUBLIC_EXT_RBAC_ENABLED: "true"
```

### Docker Compose (Lokal)

```bash
# deployment/docker_compose/.env
EXT_RBAC_ENABLED=true
NEXT_PUBLIC_EXT_RBAC_ENABLED=true
```

---

## Fehlerbehandlung und Logging

### Strategie

1. **Service-Layer:** Alle DB-Operationen in try/except, spezifische Fehler werfen HTTPException
2. **Router:** Pydantic-Validierung fuer Inputs, Service-Exceptions propagieren
3. **CVE-Fix:** `validate_curator_for_group()` vor JEDER Mutation
4. **Grundregel:** ext-rbac darf Onyx NIEMALS brechen. Router ist nur registriert wenn Flag aktiv.

### Logging

| Level | Beispiel | Wann |
|-------|----------|------|
| `INFO` | `"[EXT-RBAC] Group 'Geschaeftsleitung' created (id=1)"` | Create/Delete Operationen |
| `INFO` | `"[EXT-RBAC] User {email} added to group {name}"` | Member-Aenderungen |
| `WARN` | `"[EXT-RBAC] Curator {email} denied access to group {id}"` | CVE-2025-51479 Trigger |
| `ERROR` | `"[EXT-RBAC] Database error: ..."` | Unerwartete DB-Fehler |

**DSGVO:** Email-Adressen in INFO-Logs sind akzeptabel (Admin-Aktionen, kein User-Tracking). Keine Passwoerter oder Tokens.

**Logger:** `logging.getLogger("ext.rbac")`

---

## Test-Strategie

### Unit Tests (`backend/ext/tests/test_rbac.py`)

```python
class TestRbacService:
    # CRUD
    def test_create_group(self): ...
    def test_create_group_duplicate_name_fails(self): ...
    def test_fetch_all_groups_as_admin(self): ...
    def test_fetch_all_groups_as_curator_filters(self): ...
    def test_update_group_replaces_members(self): ...
    def test_delete_group_sets_deletion_flag(self): ...

    # User-Zuordnung
    def test_add_users_to_group(self): ...
    def test_add_users_idempotent(self): ...
    def test_set_curator_status(self): ...
    def test_set_curator_requires_membership(self): ...

    # CVE-2025-51479
    def test_curator_can_update_own_group(self): ...
    def test_curator_cannot_update_other_group(self): ...
    def test_global_curator_can_update_member_group(self): ...
    def test_admin_can_update_any_group(self): ...
    def test_basic_user_cannot_access(self): ...

    # Curator-Demotion
    def test_curator_demoted_when_removed_from_last_group(self): ...
    def test_curator_not_demoted_when_still_in_other_group(self): ...
    def test_global_curator_never_demoted(self): ...
    def test_admin_never_demoted(self): ...

    # Deletion
    def test_delete_group_cascades_all_m2m(self): ...
    def test_delete_group_demotes_orphaned_curators(self): ...

    # Edge Cases
    def test_empty_group_list_on_fresh_db(self): ...
    def test_response_matches_typescript_interface(self): ...
```

### Feature Flag Tests

```python
def test_ext_rbac_disabled_returns_404(self):
    """Endpoints return 404 when EXT_RBAC_ENABLED=false."""

def test_ext_rbac_enabled_returns_200(self):
    """Endpoints return 200 when EXT_RBAC_ENABLED=true."""
```

### Manuelle Validierung (4 Pilot-Gruppen)

Nach Implementierung auf DEV mit echtem Entra ID Login:

| Schritt | Erwartung |
|---------|-----------|
| Gruppe "Geschaeftsleitung" erstellen | 201, erscheint in GroupsPage |
| 3 User zuweisen | Members sichtbar in Detail-Seite |
| Stephan Henkel als Curator setzen | Curator-Badge sichtbar |
| Gruppe "Rechenzentrum" erstellen | 201, 7 Member |
| LLM-Provider "GPT-OSS 120B" zuweisen | Provider nur fuer Gruppe sichtbar |
| Als BASIC User: GPT-OSS 120B nutzen | 403 wenn nicht in Gruppe |
| Als Curator: eigene Gruppe aendern | 200 |
| Als Curator: andere Gruppe aendern | 403 (CVE-Fix) |

---

## Sicherheits-Checkliste

- [ ] Alle Inputs via Pydantic Schemas validiert (name: 1-255 Zeichen, UUIDs, int IDs)
- [ ] Keine SQL-Strings aus User-Input (NUR SQLAlchemy ORM)
- [ ] Alle Endpoints erfordern Auth (`current_admin_user` oder `current_curator_or_admin_user`)
- [ ] CVE-2025-51479: `validate_curator_for_group()` in JEDEM Mutation-Endpoint
- [ ] BASIC User wird von allen Endpoints blockiert
- [ ] Keine personenbezogenen Daten in Error-Responses (nur generische Meldungen)
- [ ] Logging: Email nur in Admin-Aktions-Logs (nicht in Error-Responses an Client)
- [ ] Hartes DELETE mit Cascade (alle M2M-Tabellen bereinigen)
- [ ] Curator-Demotion: User→BASIC wenn letzte Curator-Gruppe entfernt
- [ ] GLOBAL_CURATOR wird NICHT auto-demoted (andere Semantik)

---

## Performance

| Anforderung | Zielwert | Massnahme |
|------------|---------|-----------|
| GET alle Gruppen | < 200 ms | Eager-Loading der Relationships (joinedload) |
| POST/PATCH Gruppe | < 100 ms | Einzelne DB-Transaction |
| Curator-Validierung | < 5 ms | Einfacher Query auf user__user_group mit PK |

Bei ~16 Gruppen und ~100 Usern sind keine speziellen Optimierungen noetig.

---

## Offene Punkte

- [x] **[OPEN-1]** ~~Frontend-Ansatz: Wrapper um bestehende GroupsPage oder eigene Liste?~~
  - **Ergebnis (validiert 2026-03-23):** Eigene Liste in `web/src/ext/components/rbac/GroupsListPage.tsx` unter Route `/admin/ext-groups`. FOSS GroupsPage nicht nutzbar wegen proxy.ts EE-Rewrite auf `/admin/groups`.

- [ ] **[OPEN-2]** Persona/Agent-Zuordnung im UI: Eigenes Tab in Gruppen-Detail oder separate Seite?
  - **Verantwortlicher**: CCJ
  - **Kontext**: EE hat dies im Gruppen-Detail integriert

- [ ] **[OPEN-3]** `NEXT_PUBLIC_EXT_RBAC_ENABLED` als Build-Arg in Dockerfile + CI/CD?
  - **Verantwortlicher**: CCJ
  - **Kontext**: Analog zu `NEXT_PUBLIC_EXT_I18N_ENABLED` — braucht ARG/ENV in web/Dockerfile

- [x] **[OPEN-4]** ~~Vespa-Sync: Brauchen wir einen eigenen Background-Job oder reicht `is_up_to_date=False`?~~
  - **Ergebnis (validiert 2026-03-23):** Irrelevant. PROD nutzt OpenSearch mit Query-Time ACL Filtering — kein Index-Sync noetig. Gruppen-Aenderungen wirken sofort bei der naechsten Suche. Document ACLs werden in Phase 4g ueber `get_acl_for_user()` Hook in CORE #3 (`access.py`) geloest.

- [x] **[OPEN-5]** ~~Zusaetzliche Endpoints: `GET /manage/user-groups/minimal`?~~
  - **Ergebnis (validiert 2026-03-23):** JA — `useShareableGroups()` und `useUserGroups()` rufen `/api/manage/user-groups/minimal` auf. Endpoint 7 in Spec ergaenzt. Wird von Agent-Editor, Connector-Editor, LLM-Config, Document Set Erstellung benoetigt.

- [x] **[OPEN-6]** ~~12+ Frontend-Komponenten gated durch `usePaidEnterpriseFeaturesEnabled()`~~
  - **Ergebnis (validiert 2026-03-23):** Group-Selektoren SIND bereits sichtbar auf DEV (ext-branding Seiteneffekt). Endpoints 404. Sobald ext-rbac Endpoints 1-7 live sind, funktionieren Selektoren. ABER: Persona/DocSet-Save wirft `NotImplementedError` in FOSS (siehe OPEN-7).

- [x] **[OPEN-7]** ~~Persona + DocumentSet Gruppen-Zuordnung blockiert in FOSS~~
  - **Entscheidung (Niko, 2026-03-23):** Core-Dateien-Liste auf 12 erweitert. `persona.py` (#11) und `document_set.py` (#12) **gepatcht** (ext-rbac). Persona + DocumentSet Gruppen-Zuordnung funktioniert.
  - Dokumentiert in: `.claude/rules/core-dateien.md` und `.claude/rules/fork-management.md`

---

## Approvals

| Rolle | Name | Datum | Status |
|------|------|-------|--------|
| Technical Lead | Nikolaj Ivanov | TBD | Ausstehend |

---

## Revisions-Historie

| Version | Datum | Autor | Aenderungen |
|---------|-------|-------|-----------|
| 0.1 | 2026-03-23 | CCJ | Initialer Entwurf basierend auf Tiefenanalyse + `docs/analyse-rollenkonzept.md` |
| 0.2 | 2026-03-23 | CCJ | Validierung Runde 1: Vespa-Sync irrelevant (OpenSearch Query-Time ACL), API-Route konfliktfrei, useGroups via ext-branding bestaetigt, 12+ Frontend-Gates dokumentiert |
| 0.3 | 2026-03-23 | CCJ | Validierung Runde 2: (1) Built-in Groups "Admin"/"Basic" sind keine DB-Rows — Schutzlogik entfernt, (2) Deletion Cleanup ist EE-only — hartes DELETE mit Cascade statt Soft-Delete, (3) Curator-Demotion existiert nicht in FOSS — explizite Demotion in ext-rbac implementiert, Tests ergaenzt |
| 0.4 | 2026-03-23 | CCJ | Validierung Runde 3: (1) proxy.ts Blocker → Route `/admin/ext-groups`, (2) CURATOR-Rolle blockiert → `set-curator` setzt `user.role` direkt, (3) API-Prefix bestaetigt |
| 0.5 | 2026-03-23 | CCJ | Validierung Runde 4: Endpoint 7 (`/manage/user-groups/minimal`) ergaenzt, UX-Problematik (Group-Selektoren auf DEV sichtbar aber 404), Connector-Limitation dokumentiert. OPEN-5 geloest. |
| 0.6 | 2026-03-23 | CCJ | Validierung Runde 5: Persona/DocSet `NotImplementedError` in FOSS dokumentiert. LLM Provider funktioniert. Komplett-Matrix aller Ressourcen-Zuordnungen. |
| 0.7 | 2026-03-23 | CCJ | Core-Dateien 10→12. OPEN-7 geloest. |
| 0.8 | 2026-03-23 | CCJ | Core #11 (persona.py) + #12 (document_set.py) **aktiviert und gepatcht**. Persona + DocumentSet Gruppen-Zuordnung funktioniert. SQLAlchemy unique() Bugfix. |
