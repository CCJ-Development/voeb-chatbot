# Modulspezifikation: Extension Auth-Wrapper

**Dokumentstatus**: Freigegeben
**Version**: 1.0.0
**Autor**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Datum**: 2026-04-14 (Sync #5)
**Status**: [ ] Entwurf | [ ] Review | [x] Freigegeben
**Priorität**: [x] Kritisch | [ ] Hoch | [ ] Normal | [ ] Niedrig

---

## Modulübersicht

| Feld | Wert |
|------|------|
| **Modulname** | Extension Auth-Wrapper |
| **Modul-ID** | `ext_auth` (Datei: `backend/ext/auth.py`) |
| **Version** | 1.0.0 |
| **Phase** | Eingefuehrt mit Upstream-Sync #5 (2026-04-14) |
| **Feature Flag** | Keiner (Wrapper ist immer aktiv sobald ext-Framework geladen ist) |

---

## Zweck und Umfang

### Zweck

Upstream PR [onyx-dot-app/onyx#9930](https://github.com/onyx-dot-app/onyx/pull/9930) hat die Funktion `current_admin_user` aus `backend/onyx/auth/users.py` **entfernt**, im Rahmen einer Migration zum neuen account-type-Permission-System (Upstream Group-Permissions Phase 1 / Sync #5).

Alle ext-Router, die zuvor `from onyx.auth.users import current_admin_user` importiert haben, wuerden beim Boot mit `ImportError` crashen. Um die bisherige **Admin-Only-Semantik** unveraendert beizubehalten und zukuenftige Upstream-Refactorings dieser Auth-Funktion an einer einzigen Stelle abzufangen, kapselt dieses Wrapper-Modul die Dependency.

### Im Umfang enthalten

- Funktion `current_admin_user(user: User = Depends(current_user)) -> User` mit Admin-Only-Check
- Onyx-Extension-API-Attribut `_is_require_permission = True` am Wrapper, damit `check_router_auth` den Wrapper als legitime Auth-Dependency akzeptiert (und beim Boot nicht crasht)
- Zentrale Anlaufstelle fuer kuenftige Anpassungen, falls Upstream Auth-Funktionen weiter refactored

### Nicht im Umfang

- Neue Berechtigungsmodelle oder Rollen (Semantik bleibt 1:1 zum entfernten `current_admin_user`)
- RBAC / Gruppen-Permissions (siehe `ext-rbac.md`)
- Session-Management / OIDC-Callback-Handling (bleibt Onyx-FOSS)
- Token-Validierung (bleibt Onyx-FOSS)

### Abhängige Module / Prerequisites

- [x] Extension Framework (`ext-framework.md`) — fuer Paket-Struktur
- [x] Onyx-FOSS Auth-Stack (`backend/onyx/auth/users.py`) — fuer `current_user`-Dependency (existiert weiterhin)

---

## Architektur

### Komponenten-Übersicht

```
Request an ext-Admin-Endpoint (z.B. /api/ext/token/admin/limits)
       │
       ▼
FastAPI Router (backend/ext/routers/*)
       │  Depends(current_admin_user)  ← aus ext.auth (NEU seit Sync #5)
       ▼
ext.auth.current_admin_user (Wrapper)
       │  Depends(current_user)         ← aus onyx.auth.users (bleibt upstream)
       ▼
onyx.auth.users.current_user
       │  Liefert User-Objekt nach Auth-Validierung
       ▼
Wrapper: Admin-Check (User.role == UserRole.ADMIN)
       │  Bei Erfolg: User-Objekt weiterreichen
       │  Bei Fehler: HTTPException 403 Forbidden
       ▼
Router-Handler erhaelt User-Objekt
```

### Onyx-Integration via `_is_require_permission`-Sentinel

Onyx registriert alle FastAPI-Routen beim Boot und prueft dabei die Auth-Dependencies mit `backend/onyx/server/auth_check.py::check_router_auth`. Diese Funktion akzeptiert:

1. Onyx-eigene Permission-Dependencies (z.B. `current_user`, Permission-basierte Checks)
2. Externe Dependencies, die explizit per `fn._is_require_permission = True` als "Auth-Dependency" markiert sind (Onyx's offizielle Extension-API, siehe `onyx/auth/permissions.py:124`)

Ohne das Sentinel crasht der API-Server beim Boot mit `RuntimeError: Route X has no permission check`. Deshalb wird am Ende des Wrappers gesetzt:

```python
current_admin_user._is_require_permission = True
```

---

## Schnittstellen / API

### Backend-API

`backend/ext/auth.py` exportiert **eine** Funktion:

```python
async def current_admin_user(
    user: User = Depends(current_user),
) -> User:
    """Wrapper fuer Admin-Only-Check, kompatibel mit entferntem onyx.auth.users.current_admin_user.

    Raises HTTPException 403 wenn User nicht Admin ist.
    """
```

### Interne Nutzer (7 ext-Router, Stand 2026-04-17)

Folgende ext-Router importieren den Wrapper:

| Router | Pfad | Admin-Only-Endpoints |
|--------|------|---------------------|
| `ext.routers.branding` | `/api/ext/branding/*` | Logo-Upload, Settings-Update |
| `ext.routers.token` | `/api/ext/token/admin/*` | Limits-CRUD, Nutzungsreports |
| `ext.routers.prompts` | `/api/ext/prompts/admin/*` | Prompt-CRUD, Aktivierung |
| `ext.routers.analytics` | `/api/ext/analytics/admin/*` | Summary, Users, Agents, CSV-Export |
| `ext.routers.rbac` | `/api/ext/groups/*` | Gruppen-CRUD, Zuordnung |
| `ext.routers.access` | `/api/ext/access/*` | Resync, Status |
| `ext.routers.audit` | `/api/ext/audit/admin/*` | Event-Abfrage, CSV-Export |

Import-Pattern:

```python
# ALT (pre Sync #5, crasht jetzt):
# from onyx.auth.users import current_admin_user

# NEU (seit Sync #5):
from ext.auth import current_admin_user
```

---

## Konfiguration

Dieses Modul hat **keine** Konfiguration. Es wird implizit aktiviert, sobald das Extension Framework geladen ist (`EXT_ENABLED=true`).

Es existiert **kein Feature Flag** fuer dieses Modul, weil:
- Der Wrapper ist eine pure Code-Abstraktion ohne Laufzeit-Variabilitaet
- Das Deaktivieren wuerde alle 7 ext-Admin-Router brechen (ImportError)
- Es werden keine DB-Objekte, keine externen Services, keine neuen Rollen hinzugefuegt

---

## Daten / Persistenz

- **Keine neuen Tabellen**
- **Keine Alembic-Migration**
- **Keine Schema-Aenderungen**
- Keine Read/Write-Operationen auf der DB direkt aus dem Wrapper (nur Weitergabe des User-Objekts)

---

## Sicherheit

### Risikobewertung

| Risiko | Bewertung | Minderung |
|--------|-----------|-----------|
| Unbeabsichtigte Rechte-Erweiterung | **Sehr niedrig** | Admin-Check ist 1:1 zur entfernten Upstream-Funktion, keine neuen Rollen, kein erweiterter Scope |
| Bypass des Admin-Checks | **Sehr niedrig** | Wrapper nutzt `Depends(current_user)` aus Onyx-FOSS, keine eigene Auth-Logik, kein Token-Handling |
| Versehentliches Ausschalten | **Niedrig** | Kein Feature Flag; Entfernen der Datei bricht alle 7 ext-Admin-Router sofort sichtbar |
| Sentinel-Missbrauch | **Niedrig** | `_is_require_permission = True` ist Onyx's offizielle Extension-API, nicht eigene Umgehung |

### Admin-Only-Semantik

Ein User gilt als Admin, wenn `user.role == UserRole.ADMIN` (identisch zur historischen Upstream-Definition). Der Wrapper erzwingt diesen Check:

- Authentifizierung bleibt Aufgabe von Onyx-FOSS (`current_user` prueft OIDC-Token / Session-Cookie)
- Autorisierung (Admin-Only) prueft dieser Wrapper
- Bei Nicht-Admin: `HTTPException(status_code=403, detail="Admin access required")`

### Audit-Logging

Alle Admin-Aktionen, die ueber diesen Wrapper geschuetzt sind, werden durch `ext-audit` protokolliert (siehe `ext-audit.md`). Der Wrapper selbst logged nichts, er ist nur Gate.

---

## Tests

### Test-Strategie

Das Modul ist so trivial (ein Wrapper mit 2 Zeilen Logik + 1 Attribut), dass **externe Dependency Unit Tests nicht notwendig** sind. Die Verhaltensweisen sind durch die existierenden Integration Tests der 7 ext-Router implizit abgedeckt:

- **Positive Cases**: Admin-User erhaelt 200-Response auf `/api/ext/*/admin/*` Endpoints → validiert in Router-spezifischen Tests (z.B. `backend/ext/tests/test_token_admin.py::test_admin_can_list_limits`)
- **Negative Cases**: Non-Admin-User erhaelt 403 auf denselben Endpoints → validiert in denselben Router-Tests
- **Boot-Stabilitaet**: API-Server startet ohne `RuntimeError` → validiert durch jeden Deploy (DEV + PROD)

### Keine Unit Tests fuer diesen Wrapper

Begruendung:
1. Der Wrapper delegiert 100% an `onyx.auth.users.current_user` (Upstream-getestet)
2. Der Admin-Check ist eine triviale Bedingung (`user.role != UserRole.ADMIN → HTTPException`)
3. Der Sentinel ist eine Klassenattribut-Zuweisung (nicht sinnvoll mockbar)

---

## Deployment

### Automatisches Deployment

Keine speziellen Schritte noetig. Die Datei liegt in `backend/ext/auth.py` und wird durch das Extension Framework (`EXT_ENABLED=true`) mitgeladen. Bereits deployed auf:

- **DEV**: ✅ seit 2026-04-14 (Sync #5 Merge)
- **PROD**: ✅ seit 2026-04-17 (Sync #5 PROD-Rollout)

### Post-Deploy Check

```bash
# Boot-Stabilitaet
curl -sS https://chatbot.voeb-service.de/api/health
# → 200 = API-Server gestartet, alle Router registriert

# Admin-Router erreichbar (erfordert Admin-Token)
curl -sS https://chatbot.voeb-service.de/api/ext/token/admin/limits \
  -H "Cookie: <admin-session-cookie>"
# → 200 + JSON mit Limits (wenn Admin)
# → 403 (wenn kein Admin)
```

---

## Bekannte Einschränkungen / Upstream-Risiken

### Upstream-Refactor-Risiko

Bei zukuenftigen Upstream-Syncs koennte Onyx weitere Aenderungen an der Auth-Struktur durchfuehren:

1. **`current_user` wird umbenannt/entfernt**: Wrapper muss angepasst werden (1 Datei, 1 Import-Zeile)
2. **`UserRole.ADMIN` wird durch Permission-Grant ersetzt**: Wrapper-Logik muss auf das neue Modell portiert werden (5-10 Zeilen Aenderung)
3. **`_is_require_permission`-Sentinel wird obsolet**: Wenn Onyx eine neue Extension-API einfuehrt (z.B. Class-basierte `PermissionDependency`), ist Migration noetig

**Mitigation**: Bei jedem Upstream-Sync pruefen:
- Existiert `current_user` in `backend/onyx/auth/users.py` noch?
- Akzeptiert `check_router_auth` (`backend/onyx/server/auth_check.py`) weiterhin das `_is_require_permission`-Attribut?
- Gibt es eine neue offizielle Extension-API, die das Sentinel ersetzt?

Siehe auch `docs/runbooks/upstream-sync.md` (Szenario B: `current_admin_user`-Removal).

### Keine Caching-Strategie

Der Wrapper macht bei jedem Request einen vollstaendigen Admin-Check (ueber `Depends(current_user)` → DB-Query in Onyx). Das ist fuer Admin-Endpoints (selten aufgerufen) akzeptabel. **Keine Caching-Optimierung** geplant.

---

## Referenzen

- **Upstream PR**: [onyx-dot-app/onyx#9930](https://github.com/onyx-dot-app/onyx/pull/9930) — "Remove current_admin_user from auth.users (migration to account-type permission system)"
- **Onyx Extension-API**: `backend/onyx/server/auth_check.py::check_router_auth`, `backend/onyx/auth/permissions.py:124` (Sentinel-Handling)
- **Upstream-Sync-Runbook**: `docs/runbooks/upstream-sync.md`
- **Core-Dateien-Inventar**: `.claude/rules/core-dateien.md` (dieses Modul beruehrt keine Core-Dateien)
- **Sync #5 Changelog**: `docs/CHANGELOG.md` Eintrag "Fuenfter Upstream-Merge (2026-04-13/14)"
- **Dependent Modules**: `ext-branding.md`, `ext-token.md`, `ext-custom-prompts.md`, `ext-analytics.md`, `ext-rbac.md`, `ext-access.md`, `ext-audit.md`

---

## Änderungshistorie

| Version | Datum | Autor | Änderung |
|---------|-------|-------|----------|
| 1.0.0 | 2026-04-14 | COFFEESTUDIOS | Erstversion: Wrapper fuer `current_admin_user` nach Upstream PR #9930. `_is_require_permission`-Sentinel. 7 ext-Router umgestellt. DEV + PROD live. |
