# VÖB Service Chatbot — Enterprise-Fork von Onyx FOSS

Tech Lead: Nikolaj Ivanov (CCJ Development). Null Fehlertoleranz, Banking-Sektor.

## 4 Pflichtregeln (überschreiben alles)

1. **Feature-Branch Pflicht.** NIEMALS direkt auf `main` arbeiten. Session-Start: `git checkout -b feature/<thema>` von `main`. Details → @.claude/rules/commit-workflow.md
2. **Extend, don't modify.** Code NUR in `backend/ext/` und `web/src/ext/`. Nur 17 Core-Dateien dürfen minimal verändert werden → @.claude/rules/core-dateien.md
3. **Spec vor Code.** Vor jeder Implementierung: `/ext-framework` aufrufen. Kein Code ohne Modulspezifikation + Nikos Freigabe.
4. **Kein Commit ohne Freigabe.** Du commitst NICHT selbstständig. Präsentieren → Niko prüft → Freigabe → Commit.

Enterprise-Grundsätze (Banking, DSGVO, EU AI Act): @.claude/rules/enterprise-grundsaetze.md
EE/FOSS-Lizenzabgrenzung (KEINE EE-Nutzung): @.claude/rules/ee-foss-lizenz.md

---

## Projekt-Kontext

**Stack:** Python 3.11 + FastAPI + Celery (Backend), Next.js 16 + React 19 + TypeScript (Frontend), PostgreSQL 16, OpenSearch 3.4, Redis 7. Deployment auf StackIT SKE Kubernetes (Region EU01 Deutschland). Authentifizierung: Microsoft Entra ID (OIDC).

**Umgebungen:** DEV (live), PROD (live). TEST-Live abgebaut 2026-04-21; Code-Artefakte bleiben als Template im Repo.

**Projekt-Status:** @.claude/rules/voeb-projekt-status.md
**Codebase-Orientierung:** @.claude/rules/codebase-orientierung.md
**Fork-Management & Upstream-Sync:** @.claude/rules/fork-management.md
**Extension-Regeln:** @.claude/rules/extension-regeln.md
**Sicherheits-Checkliste:** @.claude/rules/sicherheit.md

**Single Source of Truth für Versionen, Ressourcen, Kosten:** `docs/referenz/technische-parameter.md`

---

## Build, Test & Dev

```bash
# Backend: Python venv aktivieren
source .venv/bin/activate

# Backend-Tests (ext-Module)
PYTHONPATH=backend python3 -m pytest backend/ext/tests/

# Frontend Dev-Server
cd web && npm run dev

# Lokales Docker-Setup (mit VÖB-Overlay)
docker compose -f deployment/docker_compose/docker-compose.yml \
  -f deployment/docker_compose/docker-compose.voeb.yml up

# Lokal Login: a@example.com / a, UI auf http://localhost:3000
```

**PostgreSQL:** Wir nutzen StackIT Managed Flex, nicht lokale Docker-PG. Zugriff auf DEV/PROD nur via `kubectl exec` + psycopg2 oder StackIT CLI — nicht `docker exec`.

**Celery-Restart:** Keine Auto-Restart bei Code-Änderungen. Nach Änderungen an Workers: Pod-Restart in K8s (oder Niko bitten).

---

## Skills (Slash-Commands)

- `/ext-framework` — Pflicht-Workflow vor jeder Extension-Implementierung
- `/modulspec` — Erstellt eine Modulspezifikation nach Enterprise-Template
- `/init` — Initial-Setup (selten nötig)

---

## Typische Gotchas

- **Feature-Flags für alles:** Jede ext-Erweiterung hinter `EXT_<MODUL>_ENABLED`, Default `false`. Siehe `backend/ext/config.py`.
- **FastAPI ohne `response_model`:** Funktionen direkt typisieren statt `response_model=` zu nutzen (Onyx-Konvention).
- **Celery-Tasks:** `@shared_task` statt `@celery_app`. Tasks unter `backend/ext/tasks/` oder `backend/onyx/background/celery/tasks/`.
- **DB-Operationen:** ALLE unter `backend/onyx/db/` oder `backend/ext/services/` — keine Queries außerhalb.
- **Backend-Calls vom Frontend:** IMMER über den Frontend-Proxy (`http://localhost:3000/api/…`), nicht direkt auf `:8080`.
- **Alembic-Chain:** Nach Upstream-Sync ist die Migrations-Chain oft durcheinander. Siehe `docs/runbooks/upstream-sync.md`.
- **Strict Typing:** Python (mypy) und TypeScript (`tsc --strict`). Beides durchgängig gewartet.

---

## Logs & Debugging

- **Lokal:** `backend/log/<service_name>_debug.log` (api_server, web_server, celery_*).
- **DEV/PROD:** `kubectl logs -n onyx-<env> <pod>` — alle Pods mit Log-Shipping an Loki (30 Tage Retention).
- **Grafana:** `kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80` → http://localhost:3001

---

## Weiterführende Doku

- Dokumenten-Index: `docs/README.md`
- Runbooks (Deploy, Upstream-Sync, Incident, Rollback): `docs/runbooks/`
- Sicherheitskonzept: `docs/sicherheitskonzept.md`
- Betriebskonzept: `docs/betriebskonzept.md`
- ADRs (Architektur-Entscheidungen): `docs/adr/`
- Modulspezifikationen: `docs/technisches-feinkonzept/`
