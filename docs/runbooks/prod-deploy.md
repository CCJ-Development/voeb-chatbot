# PROD-Deploy Runbook (Template)

**Erstmalig angewendet:** 2026-04-17 (Sync #5 + Monitoring-Optimierung + OOM-Fix)
**Zweck:** Wiederverwendbare Schritt-fuer-Schritt-Anleitung fuer PROD-Deploys nach Upstream-Sync oder Infrastructure-Changes.
**Voraussetzung:** Alle Code-Aenderungen sind auf `main` gemerged und auf DEV verifiziert.

**Anpassung fuer neuen Deploy:**
- Alembic-Revisionen in Schritt 3 auf aktuelle Heads anpassen (aktuell: `689433b0d8de` → `503883791c39` → `d8a1b2c3e4f5`)
- Szenario-spezifische Patches in Schritt 1 (OOM-Fix ist Sync-#5-spezifisch — bei kuenftigen Deploys evtl. ueberspringen)
- Helm-Monitoring-Cleanup (Schritt 5) nur noetig falls manuelle `kubectl replace` passiert ist

---

## Checkliste VOR dem Start

- [ ] `kubectl --context vob-prod get pods -n onyx-prod` — alle Pods Running?
- [ ] `curl https://chatbot.voeb-service.de/api/health` — 200?
- [ ] Keine aktiven StackIT-Incidents (`status.stackit.cloud` pruefen)
- [ ] PROD-Kubeconfig gueltig? (Ablauf: 2026-06-22)
- [ ] VÖB informieren: "Maintenance-Window, moegliche kurze Unterbrechungen"

---

## Schritt 1 — OOM-Fix per kubectl (SOFORT, stoppt Crashes)

**Dauer:** ~2 Min, Rolling Update, keine Downtime

```bash
# API-Server: 2Gi → 4Gi (OOM-Fix)
kubectl --context vob-prod patch deploy onyx-prod-api-server -n onyx-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"api-server","resources":{"limits":{"memory":"4Gi"},"requests":{"memory":"1Gi"}}}]}}}}'

# docfetching: 4Gi → 2Gi (Optimierung, 30d-Peak nur 224 MiB)
kubectl --context vob-prod patch deploy onyx-prod-celery-worker-docfetching -n onyx-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"celery-worker-docfetching","resources":{"limits":{"memory":"2Gi"},"requests":{"memory":"512Mi"}}}]}}}}'

# docprocessing: 4Gi → 2Gi (Optimierung, 30d-Peak nur 225 MiB)
kubectl --context vob-prod patch deploy onyx-prod-celery-worker-docprocessing -n onyx-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"celery-worker-docprocessing","resources":{"limits":{"memory":"2Gi"},"requests":{"memory":"512Mi"}}}]}}}}'
```

**Verifikation:**
```bash
kubectl --context vob-prod get pods -n onyx-prod -l app=api-server
# Erwartung: 2 neue Pods, 0 Restarts, READY 1/1 innerhalb 2 Min
```

---

## Schritt 2 — PROD-Deploy Sync #5 via CI/CD

**Dauer:** ~10-15 Min (Build + Deploy)

```bash
gh workflow run stackit-deploy.yml -R CCJ-Development/voeb-chatbot \
  -f environment=prod --ref main
```

**Was deployed wird:**
- Upstream-Sync #5 (344 Commits, Chart 0.4.44)
- Deep-Health-Endpoint `/api/ext/health/deep` (Router-Pfad intern: `/ext/health/deep`, Public-URL mit `/api/` Prefix)
- ext/auth.py (current_admin_user Wrapper)
- Core #15 (useSettings.ts, NEXT_PUBLIC_EXT_BRANDING_ENABLED)
- Readiness-Probe auf `/api/ext/health/deep`
- Pre-commit Hook Update
- CI-Race-Fix (build-backend needs build-frontend)
- API-Server Memory 4Gi + docfetching/docprocessing 2Gi (values-prod.yaml)

**Verifikation:**
```bash
kubectl --context vob-prod get pods -n onyx-prod
# Alle Pods Running, 0 Restarts
curl -sS https://chatbot.voeb-service.de/api/ext/health/deep
# HTTP 200 mit JSON: postgres=ok, redis=ok, opensearch=ok
kubectl --context vob-prod logs -l app=api-server -n onyx-prod --tail=20 | grep "Extension"
# Erwartung: Alle 7 ext-Router registriert
```

---

## Schritt 3 — Alembic-Chain-Recovery (11 Upstream-Migrationen)

**KRITISCH: Muss NACH Schritt 2 ausgefuehrt werden (neuer Code muss im Pod sein).**

**Dauer:** ~5 Min

**Hintergrund:** Unsere ext-Chain (ff7273065d0d → ... → d8a1b2c3e4f5) setzt auf dem
alten Upstream-Head auf. Upstream fuegt 11 neue Migrationen in der Mitte ein. Alembic
sieht: current == head → fuehrt nichts aus → DB-Schema haengt hinterher.

**VOR der Migration — Gruppen-Check:**
```bash
POD=$(kubectl --context vob-prod get pods -n onyx-prod -l app=api-server \
  -o jsonpath='{.items[0].metadata.name}')

# Pruefen ob "Admin" oder "Basic" Gruppen existieren
kubectl --context vob-prod exec -n onyx-prod $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    print('alembic_version:', conn.execute(text('SELECT version_num FROM alembic_version')).scalar())
    rows = conn.execute(text(\"SELECT name FROM user_group ORDER BY name\")).fetchall()
    print('UserGroups:', [r[0] for r in rows])
    has_acct = conn.execute(text(\"SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='account_type'\")).scalar()
    print('user.account_type exists:', bool(has_acct))
"
# ERWARTUNG: alembic_version = d8a1b2c3e4f5 (unser ext-audit Head)
# ERWARTUNG: user.account_type = False (Migration fehlt noch)
# ACHTUNG: Falls UserGroups "Admin" oder "Basic" enthalten, werden sie durch
#          seed_default_groups Migration zu "Admin (Custom)" umbenannt!
```

**Migration ausfuehren:**
```bash
# alembic_version temporaer auf alten Upstream-Head zuruecksetzen
kubectl --context vob-prod exec -n onyx-prod $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text(\"UPDATE alembic_version SET version_num = '689433b0d8de'\"))
    conn.commit()
    print('alembic_version set to:', conn.execute(text('SELECT version_num FROM alembic_version')).scalar())
"

# Upstream-Migrationen ausfuehren (689433b0d8de → 503883791c39)
kubectl --context vob-prod exec -n onyx-prod $POD -- alembic upgrade 503883791c39
# ERWARTUNG: 11 "Running upgrade" Zeilen, keine Errors

# alembic_version auf unseren echten Head zuruecksetzen
kubectl --context vob-prod exec -n onyx-prod $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text(\"UPDATE alembic_version SET version_num = 'd8a1b2c3e4f5'\"))
    conn.commit()
    print('alembic_version restored:', conn.execute(text('SELECT version_num FROM alembic_version')).scalar())
"
```

**Verifikation nach Migration:**
```bash
kubectl --context vob-prod exec -n onyx-prod $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    print('alembic_version:', conn.execute(text('SELECT version_num FROM alembic_version')).scalar())
    print('user.account_type:', bool(conn.execute(text(\"SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='account_type'\")).scalar()))
    print('persona.is_listed:', bool(conn.execute(text(\"SELECT 1 FROM information_schema.columns WHERE table_name='persona' AND column_name='is_listed'\")).scalar()))
    print('permission_grant:', bool(conn.execute(text(\"SELECT 1 FROM information_schema.tables WHERE table_name='permission_grant'\")).scalar()))
    print('UserGroups:', [r[0] for r in conn.execute(text(\"SELECT name FROM user_group ORDER BY name\")).fetchall()])
"
# ERWARTUNG: Alle True, UserGroups enthalten jetzt "Admin" + "Basic" (seeded)

# API-Server neustarten um neuen DB-Stand zu laden
kubectl --context vob-prod delete pod -l app=api-server -n onyx-prod
# Warten bis neue Pods ready sind (~60s)
```

---

## Schritt 4 — API-Server Pod-Restart (nach Alembic)

```bash
kubectl --context vob-prod delete pod -l app=api-server -n onyx-prod
kubectl --context vob-prod get pods -n onyx-prod -l app=api-server -w
# Warten bis READY 1/1 (ca. 60s)
```

---

## Schritt 5 — Helm monitoring upgrade (Blackbox + Cleanup)

**Dauer:** ~5 Min

```bash
# Schritt 5a: Fehlgeschlagene Helm-Releases bereinigen
kubectl --context vob-prod delete secret -n monitoring sh.helm.release.v1.monitoring.v7 2>/dev/null
kubectl --context vob-prod delete secret -n monitoring sh.helm.release.v1.monitoring.v6 2>/dev/null

# Schritt 5b: Helm upgrade mit --force (loest ownership conflicts)
helm --kube-context vob-prod upgrade monitoring prometheus-community/kube-prometheus-stack \
  --version 82.10.3 \
  -n monitoring \
  -f deployment/helm/values/values-monitoring-prod.yaml \
  --force \
  --timeout 5m
```

**Verifikation:**
```bash
helm --kube-context vob-prod history monitoring -n monitoring --max 3
# Erwartung: Neueste Revision = "deployed"
kubectl --context vob-prod get pods -n monitoring
# Alle Pods Running
```

---

## Schritt 6 — Smoke-Test PROD

```bash
# 1. API Health
curl -sS https://chatbot.voeb-service.de/api/health
# → 200

# 2. Deep Health (NEU nach Sync #5)
curl -sS https://chatbot.voeb-service.de/api/ext/health/deep
# → 200 mit postgres=ok, redis=ok, opensearch=ok

# 3. Enterprise Settings (VÖB-Branding)
curl -sS https://chatbot.voeb-service.de/api/enterprise-settings | head -c 100
# → JSON mit application_name="VÖB Service Chatbot"

# 4. Browser-Test:
#    - Login via Entra ID
#    - Chat-Seite: deutsche Strings, VÖB-Logo
#    - Admin-Sidebar: Branding, Token, Prompts, Gruppen sichtbar
#    - Datei-Upload im Chat testen (kleine Datei, <1 MB)

# 5. Monitoring-Check:
#    - Teams-Channel: Keine neuen Alerts nach Deploy
#    - Prometheus: pg_up == 1, probe_success == 1
```

---

## Rollback-Plan

**Falls Schritt 2 (CI/CD Deploy) schiefgeht:**
```bash
# Letztes funktionierendes Image Tag finden
helm --kube-context vob-prod history onyx-prod -n onyx-prod --max 3
# Rollback auf vorherige Revision
helm --kube-context vob-prod rollback onyx-prod <REVISION> -n onyx-prod
```

**Falls Schritt 3 (Alembic) schiefgeht:**
```bash
# alembic_version sofort auf unseren bisherigen Head zuruecksetzen
kubectl --context vob-prod exec -n onyx-prod $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text(\"UPDATE alembic_version SET version_num = 'd8a1b2c3e4f5'\"))
    conn.commit()
"
# API-Server neustarten
kubectl --context vob-prod delete pod -l app=api-server -n onyx-prod
```

---

## Typische Fallstricke / Lessons Learned

### 1. Schritt-Reihenfolge ist kritisch

**Reihenfolge: Pre-Patch → Code-Deploy → Alembic → Restart → Monitoring-Upgrade.**

- **Alembic VOR Code-Deploy** = API-Server crasht beim Start, wenn neue Migrationen alte Models referenzieren, die noch nicht im Pod sind.
- **Code-Deploy VOR Alembic** = API-Server laeuft mit neuem Code, aber DB-Schema haengt hinterher. Meist "nur" 500-Errors fuer Models die neue Spalten lesen. Meist tolerierbar waehrend der ~5 Min Alembic-Recovery.
- **OOM-Fix VOR CI/CD-Deploy** = Neue Pods starten nicht nochmal mit altem OOM-Limit. Alte Pods werden durch Rolling Update ersetzt.

### 2. Alembic-Chain-Recovery ist der Regelfall bei Upstream-Syncs

**Wann notwendig:** Bei JEDEM Upstream-Sync, der neue Migrationen in die Chain einfuegt.

**Erkennung vorab:** `git diff main..upstream/main --name-only | grep alembic/versions` — wenn neue Files in `backend/alembic/versions/` erscheinen, ist Recovery noetig.

**Die 3-Phasen-Rotation:**
1. `UPDATE alembic_version SET version_num = '<alter_upstream_head>'` (reset zurueck)
2. `alembic upgrade <neuer_upstream_head>` (die neuen Migrationen laufen)
3. `UPDATE alembic_version SET version_num = '<unser_ext_head>'` (zurueck auf unseren aktuellen Head)

Details: `docs/runbooks/upstream-sync.md` Szenario A.

### 3. `seed_default_groups` Migration ueberschreibt existierende VÖB-Gruppen

**Symptom:** Nach Upstream-Sync #5 heissen unsere Gruppen "Admin (Custom)" und "Basic (Custom)" statt "Admin" / "Basic".

**Ursache:** Upstream PR #9795 fuehrte `seed_default_groups` Migration ein, die existierende "Admin"/"Basic"-Gruppen zu "(Custom)" umbenennt und neue Default-Gruppen anlegt.

**Anwendung:**
- **Gruppen-Check VOR der Migration durchfuehren** (siehe Schritt 3 "VOR der Migration").
- Wenn "Admin"/"Basic" existieren UND umbenannt werden soll: Migration einfach laufen lassen.
- Wenn "Admin"/"Basic" existieren UND NICHT umbenannt werden soll: Gruppen temporaer umbenennen (`UPDATE user_group SET name='Admin-vob' WHERE name='Admin'`), Migration laufen lassen, dann zurueck umbenennen + die neu erstellten "Admin"/"Basic" loeschen.

### 4. `kubectl patch` verschwindet beim naechsten `helm upgrade` (wenn values nicht nachziehen)

**Symptom:** OOM-Fix via `kubectl patch` war live, aber nach einer Woche OOM-Kills wieder da. Helm-Upgrade hat den Patch zurueckgerollt.

**Ursache:** `kubectl patch` aendert nur die Live-Deployment-Resource, nicht die Helm-Values. Beim naechsten `helm upgrade` schreibt Helm die Values wieder, der Patch ist weg.

**Anwendung:** Jeder `kubectl patch` fuer Production muss SOFORT auch in `values-prod.yaml` committet werden. Die Sync-#5-OOM-Fix-Werte (API 4Gi, docfetching 2Gi, docprocessing 2Gi) sind deshalb **beide** — im Sofort-Patch und in values-prod.yaml.

### 5. Helm-Release-History-Cleanup bei failed Upgrades

**Symptom:** Helm History zeigt Rev 5 (deployed) + Rev 6 (failed) + Rev 7 (failed). Naechstes `helm upgrade` schlaegt fehl mit "another operation in progress".

**Ursache:** Failed Upgrades lassen das Release in "pending-upgrade" oder "failed" Status. Secrets `sh.helm.release.v1.<name>.v<N>` enthalten die gesamte Release-History und blockieren.

**Recovery:**
```bash
# Failed Release-Secrets identifizieren
kubectl --context vob-prod get secrets -n monitoring -l owner=helm | grep monitoring

# Failed Revisionen loeschen (sh.helm.release.v1.*.v<FAILED_REV>)
kubectl --context vob-prod delete secret -n monitoring \
  sh.helm.release.v1.monitoring.v6 \
  sh.helm.release.v1.monitoring.v7

# Naechster helm upgrade nutzt den letzten "deployed" Stand als Basis
helm --kube-context vob-prod upgrade monitoring ... --force-replace --server-side=false
```

### 6. Deep-Health-Endpoint als Readiness-Probe

**Warum:** `/api/health` prueft nur Python-Prozess, nicht DB. Pod bleibt "ready" bei PG-Ausfall → Traffic geht auf kaputten Pod.

**Seit Sync #5 in values-prod.yaml:** `readinessProbe.httpGet.path: /api/ext/health/deep` (prueft PG + Redis + OpenSearch). Liveness bleibt auf `/api/health` (schnell, nur fuer Deadlock-Detection).

**Wichtig bei initialem Deploy:** `initialDelaySeconds: 30` nicht niedriger — Deep-Health braucht alle 3 Stores bereit, was beim ersten Start 10-20s dauern kann.

### 7. CI/CD `--admin` Flag ist Workaround fuer Branch-Protection

**Warum:** `ci-checks.yml` laeuft nur auf `push: branches: main`, nicht auf `pull_request`. PR erreicht nie die "required" Status-Checks.

**Anwendung:** Upstream-Sync-PRs mit `gh pr merge --admin` (Niko ist Repo-Admin). Checks laufen dann nach dem Merge auf main. Trade-off: Kurzes Fenster ohne Validierung. Bei haeufigem PR-Workflow: `ci-checks.yml` auch auf `pull_request` triggern.

---

## Zeitplan (geschaetzt)

| Schritt | Dauer | Kumuliert |
|---------|-------|-----------|
| Checkliste | 5 Min | 5 Min |
| 1. OOM-Fix kubectl | 2 Min | 7 Min |
| 2. CI/CD Deploy | 12 Min | 19 Min |
| 3. Alembic-Recovery | 5 Min | 24 Min |
| 4. Pod-Restart | 2 Min | 26 Min |
| 5. Helm monitoring | 5 Min | 31 Min |
| 6. Smoke-Test | 10 Min | 41 Min |
| **Gesamt** | | **~45 Min** |
