# CI/CD Pipeline — Runbook

> **Workflow**: `.github/workflows/stackit-deploy.yml`
> **Verifiziert**: 2026-03-02 (Run #5, Commit `ea70a11`)
> **Letzte Änderung**: 2026-04-21
>
> **Hinweis:** Seit Upstream-Sync #4 (2026-03-22) existiert `.github/workflows/storybook-deploy.yml` (Storybook Deploy). Harmlos, kann bei Bedarf deaktiviert werden.

> **Für Kunden-Klon-Projekte:** Dieses Runbook ist mit dem VÖB-Workflow und VÖB-Secret-Namen dokumentiert. Für einen neuen Kunden müssen die GitHub Environments (`dev`, `prod`) und die zugehörigen Secrets neu angelegt werden. Secret-Namen bleiben identisch (`POSTGRES_PASSWORD`, `S3_ACCESS_KEY_ID`, …); nur die **Werte** sind kundenspezifisch. Siehe [Master-Playbook §2](./kunden-klon-onboarding.md) für die vollständige Variablen-Tabelle und die empfohlene Reihenfolge (erst GitHub Environments + Secrets, dann `terraform apply`, dann `workflow_dispatch`).

---

## Zweck

**Wann dieses Runbook verwenden:**
- Deployment auf DEV oder PROD ausloesen (automatisch oder manuell)
- Deploy-Status pruefen und Pipeline-Fehler debuggen
- Secrets (Kubeconfig, Registry, DB) aktualisieren oder rotieren
- (Historisch) TEST-Template-Job triggern — TEST-Live-Infra seit 2026-04-21 abgebaut

**Zielgruppe:** DevOps / Tech Lead

**Voraussetzungen:**
- Zugriff auf GitHub-Repo `CCJ-Development/voeb-chatbot`
- `gh` CLI authentifiziert
- Fuer Cluster-Zugriff: `kubectl` mit gueltiger Kubeconfig

**Geschaetzte Dauer:** 15-30 Min (Deploy + Verifikation)

---

## Voraussetzungen

- Zugriff auf GitHub-Repo `CCJ-Development/voeb-chatbot`
- `gh` CLI authentifiziert (oder GitHub UI)
- Für Cluster-Zugriff: `kubectl` mit gültiger Kubeconfig
  - DEV/TEST-Cluster `vob-chatbot`: Ablauf **2026-06-14** (erneuert 2026-03-16)
  - PROD-Cluster `vob-prod`: Ablauf **2026-06-22** (erneuert 2026-03-24)

---

## 1. Pipeline-Architektur

### Übersicht

```
Push auf main / workflow_dispatch
        │
    ┌───▼───┐
    │prepare│  (6s) Image Tag bestimmen (Git SHA oder manuell)
    └───┬───┘
        │
   ┌────┴────┐
   ▼         ▼
┌──────┐  ┌──────┐
│build-│  │build-│  (~7 Min, parallel)
│back- │  │front-│
│end   │  │end   │
└──┬───┘  └──┬───┘
   │         │
   └────┬────┘
        │
   ┌────▼────┐
   │deploy-  │  (~2 Min) Helm upgrade + Smoke Test
   │{env}    │
   └─────────┘
```

### Was wird gebaut

| Image | Quelle | Registry | Warum |
|-------|--------|----------|-------|
| `onyx-backend` | `./backend` Dockerfile | StackIT Registry | Unser Fork-Code (Extensions, Config) |
| `onyx-web-server` | `./web` Dockerfile | StackIT Registry | Unser Fork-Code (Frontend). Build-Args: `NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=true`, `NEXT_PUBLIC_EXT_I18N_ENABLED=true` (seit ext-i18n, 2026-03-22) |
| `onyx-model-server` | Docker Hub Upstream | `docker.io/onyxdotapp` | Identisch mit Upstream — kein eigener Build nötig |

### Was wird NICHT gebaut

Der **Model Server** wird nicht gebaut. Er nutzt das offizielle Onyx-Image von Docker Hub, gepinnt auf Version `v2.9.8`. Begründung:

1. Wir ändern nichts am Embedding/Reranking-Code
2. Spart ~12 Min Build-Zeit
3. Eliminiert ImagePullBackOff-Probleme mit der StackIT Registry

> **Bei Upstream-Update**: Tag in `MODEL_SERVER_TAG` im Workflow aktualisieren. Vorher prüfen ob das neue Image kompatibel ist.

---

## 2. Deploy auslösen

### Automatisch (DEV)

Push auf `main` löst automatisch DEV-Deploy aus:
```bash
git push origin main
```

Ausnahme: Änderungen nur an `docs/**`, `*.md`, `.claude/**` lösen keinen Build aus.

### Manuell (DEV/TEST/PROD)

```bash
# DEV
gh workflow run "StackIT Build & Deploy" \
  --repo CCJ-Development/voeb-chatbot \
  --ref main \
  -f environment=dev

# TEST
gh workflow run "StackIT Build & Deploy" \
  --repo CCJ-Development/voeb-chatbot \
  --ref main \
  -f environment=test

# PROD (benötigt Required Reviewers in GitHub Settings)
gh workflow run "StackIT Build & Deploy" \
  --repo CCJ-Development/voeb-chatbot \
  --ref main \
  -f environment=prod
```

### Mit spezifischem Image-Tag

```bash
gh workflow run "StackIT Build & Deploy" \
  --repo CCJ-Development/voeb-chatbot \
  --ref main \
  -f environment=dev \
  -f image_tag=ea70a11
```

---

## 3. Deploy-Status prüfen

```bash
# Letzten Run anzeigen
gh run list --workflow="StackIT Build & Deploy" \
  --repo CCJ-Development/voeb-chatbot --limit 3

# Details eines Runs
gh run view <RUN_ID> --repo CCJ-Development/voeb-chatbot

# Logs eines Jobs
gh run view --job=<JOB_ID> --repo CCJ-Development/voeb-chatbot --log
```

### Auf dem Cluster

```bash
# Pod-Status
kubectl get pods -n onyx-dev

# Welche Images laufen
kubectl get pods -n onyx-dev \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'

# API Health Check (via HTTPS)
curl https://dev.chatbot.voeb-service.de/api/health    # DEV
curl https://chatbot.voeb-service.de/api/health         # PROD (HTTPS LIVE seit 2026-03-17)
# TEST war bis 2026-04-21 verfuegbar, Live-Infrastruktur ist abgebaut; Template im Repo.
```

---

## 4. Rollback

### Alle Environments (DEV/TEST/PROD)

Alle Environments verwenden `--wait --timeout 15m`. Kein automatischer Rollback bei Timeout — Release bleibt stehen und kann debuggt werden. Grund: 16+ Pods mit Cold Start (Alembic Migrations, Model Server) brauchen mehr Zeit. Bei Bedarf manueller Rollback:

```bash
# Letzte Helm Releases anzeigen
helm history onyx-dev -n onyx-dev

# Auf vorherige Revision zurückrollen
helm rollback onyx-dev <REVISION> -n onyx-dev

# Oder: Auf einen bestimmten Image-Tag deployen
gh workflow run "StackIT Build & Deploy" \
  --repo CCJ-Development/voeb-chatbot \
  --ref main \
  -f environment=dev \
  -f image_tag=<IMAGE_TAG>
```

### Notfall: Direkter Image-Wechsel

Ohne Pipeline, direkt auf dem Cluster:

```bash
kubectl set image deployment/onyx-dev-api-server \
  api-server=registry.onstackit.cloud/voeb-chatbot/onyx-backend:<IMAGE_TAG> \
  -n onyx-dev
```

---

## 5. Secrets verwalten

### Übersicht

| Secret | Scope | Beschreibung |
|--------|-------|-------------|
| `STACKIT_REGISTRY_USER` | Global | Robot Account Name |
| `STACKIT_REGISTRY_PASSWORD` | Global | Robot Account Token |
| `STACKIT_KUBECONFIG` | Global | Base64-encoded Kubeconfig fuer DEV/TEST-Cluster `vob-chatbot`, **Ablauf: 2026-06-14** |
| `STACKIT_KUBECONFIG` | Environment `prod` | Base64-encoded Kubeconfig fuer PROD-Cluster `vob-prod`, **Ablauf: 2026-06-22**. Ueberschreibt das globale Secret fuer PROD-Deployments. |
| `POSTGRES_PASSWORD` | Per Environment | PG Flex App-User Passwort |
| `S3_ACCESS_KEY_ID` | Per Environment | StackIT Object Storage |
| `S3_SECRET_ACCESS_KEY` | Per Environment | StackIT Object Storage |
| `DB_READONLY_PASSWORD` | Per Environment | PG Readonly User |
| `REDIS_PASSWORD` | Per Environment | Redis Standalone |
| `OPENSEARCH_PASSWORD` | Nur PROD | OpenSearch Admin-Passwort (NICHT Chart-Default nutzen!) |

> **Wichtig:** `STACKIT_KUBECONFIG` existiert zweimal — einmal global (DEV/TEST) und einmal als Environment Secret in `prod` (PROD). Das Environment Secret ueberschreibt das globale Secret wenn der Deploy-Job im GitHub Environment `prod` laeuft. Bei Kubeconfig-Renewal muessen **beide** Secrets aktualisiert werden.

### Secret aktualisieren

```bash
# Global
gh secret set STACKIT_KUBECONFIG \
  --repo CCJ-Development/voeb-chatbot \
  --body "$(base64 < ~/.kube/config)"

# Per Environment
gh secret set POSTGRES_PASSWORD \
  --repo CCJ-Development/voeb-chatbot \
  --env dev \
  --body "neues-passwort"
```

### Kubeconfig erneuern

Es gibt zwei Kubeconfigs fuer zwei separate Cluster:

| Cluster | Environments | Ablauf | GitHub Secret Scope |
|---------|-------------|--------|---------------------|
| `vob-chatbot` (DEV/TEST) | dev, test | **2026-06-14** (erneuert 2026-03-16) | Global |
| `vob-prod` (PROD) | prod | **2026-06-22** (erneuert 2026-03-24) | Environment `prod` |

**Schritt 1: DEV/TEST-Cluster erneuern**

```bash
# Neue Kubeconfig fuer DEV/TEST-Cluster holen
stackit ske kubeconfig create vob-chatbot \
  --project-id b3d2a04e-46de-48bc-abc6-c4dfab38c2cd \
  --login --expiration 90d

# Als GLOBALES GitHub Secret setzen
gh secret set STACKIT_KUBECONFIG \
  --repo CCJ-Development/voeb-chatbot \
  --body "$(base64 < ~/.kube/config)"
```

**Schritt 2: PROD-Cluster erneuern**

```bash
# Neue Kubeconfig fuer PROD-Cluster holen
stackit ske kubeconfig create vob-prod \
  --project-id <PROD_PROJECT_ID> \
  --login --expiration 90d
# PROD Projekt-ID: Siehe StackIT Portal, Projekt `vob-prod`. GitHub Environment: `prod` (Required Reviewer).

# Als ENVIRONMENT Secret im GitHub Environment `prod` setzen
gh secret set STACKIT_KUBECONFIG \
  --repo CCJ-Development/voeb-chatbot \
  --env prod \
  --body "$(base64 < ~/.kube/config)"
```

**Schritt 3: Dokumentation aktualisieren**

Neue Ablaufdaten aktualisieren in:
- Diesem Runbook (Tabelle oben + Secrets-Tabelle)
- Voraussetzungen-Abschnitt (Zeile 13-15)
- `MEMORY.md` (Kubeconfig-Ablauf)
- `.claude/rules/voeb-projekt-status.md` (falls Ablaufdatum erwaehnt)

---

## 6. Troubleshooting

### Pipeline schlägt fehl: Build

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| `unauthorized` bei Registry Login | Robot Account Token abgelaufen | Neues Token in StackIT Portal erstellen, `STACKIT_REGISTRY_PASSWORD` aktualisieren |
| Build Timeout | GHA-Cache ungültig nach großer Änderung | Manuell Cache löschen: GitHub UI → Actions → Caches |
| `COPY failed: file not found` | Dockerfile-Kontext falsch | `context:` im Workflow prüfen (`./backend` bzw. `./web`) |

### Pipeline schlägt fehl: Deploy

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| `helm dependency build` Fehler | Helm Repo nicht erreichbar | Prüfen ob Repo-URLs noch aktuell sind (Chart-Dependencies ändern sich upstream) |
| `Insufficient CPU` | Alte + neue Pods gleichzeitig auf Single Node | Recreate-Strategie-Patch prüfen. Ist nur für DEV relevant |
| `UPGRADE FAILED: timed out` | Pods kommen nicht hoch | Logs prüfen: `kubectl logs deployment/<name> -n onyx-dev` |

### Pods starten nicht

| Symptom | Ursache | Lösung |
|---------|---------|--------|
| `CrashLoopBackOff` API-Server | `LICENSE_ENFORCEMENT_ENABLED` nicht auf `"false"` | `kubectl get configmap env-configmap -n onyx-dev -o yaml \| grep LICENSE` |
| `ImagePullBackOff` | Registry-Credentials ungültig oder Image-Tag falsch | Image Pull Secret prüfen: `kubectl get secret stackit-registry -n onyx-dev -o yaml` |
| `Pending` | Nicht genug Ressourcen auf Node | `kubectl describe pod <name> -n onyx-dev` → Events prüfen |
| `OOMKilled` | Memory Limit zu niedrig | Resource Limits in `values-dev.yaml` erhöhen |

### Smoke Test schlägt fehl

Der Smoke Test prüft `/api/health` mit 12 Versuchen (alle 10s = 2 Min Timeout).

```bash
# Manuell prüfen (via HTTPS)
curl -v https://dev.chatbot.voeb-service.de/api/health    # DEV
curl -v https://test.chatbot.voeb-service.de/api/health   # TEST (heruntergefahren seit 2026-03-19)
curl -v https://chatbot.voeb-service.de/api/health         # PROD (HTTPS LIVE seit 2026-03-17)

# Pod-Logs ansehen
kubectl logs deployment/onyx-dev-api-server -n onyx-dev --tail=50

# Wenn Ingress-Problem: Nginx-Logs prüfen
kubectl logs deployment/onyx-dev-nginx-controller -n onyx-dev --tail=50
```

---

## 6b. Typische Fallstricke / Lessons Learned

### 1. Registry-Login Race Condition bei parallelem Build

**Symptom:** Einer von zwei parallelen Build-Jobs (`build-backend`, `build-frontend`) schlaegt mit `401 Unauthorized` beim `docker login` fehl. Zweiter Build-Versuch (via `gh run rerun --failed`) gelingt sofort.

**Ursache:** StackIT Harbor akzeptiert bei paralleler Last gelegentlich nur einen Login — seit Sync #5 beobachtet.

**Quick-Fix:**
```bash
gh run rerun --failed -R CCJ-Development/voeb-chatbot
```

**Langfristig-Fix (empfohlen bei haeufigem Auftreten):** `build-backend needs: build-frontend` im Workflow erzwingen:
```yaml
jobs:
  build-frontend: ...
  build-backend:
    needs: build-frontend  # wartet auf frontend-login-release
```
Trade-off: +~5 Min Build-Gesamtzeit (sequenziell statt parallel). Seit Sync #5 bereits aktiv.

### 2. Registry-Credentials-Drift zwischen K8s und GitHub

**Symptom:** Build schlaegt mit `401 Unauthorized` fehl, obwohl Pods im Cluster laufen (Image-Pull funktioniert).

**Ursache:** K8s-Secret `stackit-registry` wurde bei Token-Rotation aktualisiert, GitHub-Secret `STACKIT_REGISTRY_PASSWORD` nicht. CI/CD verwendet GitHub-Secret → 401.

**Recovery:** K8s-Secret ist Source of Truth, Credentials extrahieren und in GitHub nachziehen. Details: `docs/runbooks/secret-rotation.md` Abschnitt "Recovery bei Drift".

### 3. PR-Merge scheitert mit "base branch policy prohibits the merge"

**Symptom:** `gh pr merge <NR>` auf Upstream-Sync-PR schlaegt fehl mit "required checks not met".

**Ursache:** Branch Protection auf `main` verlangt Status-Checks `helm-validate`, `build-backend`, `build-frontend`. Diese laufen aber in `ci-checks.yml` nur auf `push: branches: main`, NICHT auf `pull_request`. PR erreicht nie die required Checks.

**Workaround:** `--admin` Flag (Niko ist Repo-Admin):
```bash
gh pr merge <NR> -R CCJ-Development/voeb-chatbot --merge --delete-branch --admin
```
Checks laufen nach dem Merge auf main und validieren nachtraeglich.

**Alternative (zukuenftig erwaegen):** `ci-checks.yml` auch auf `pull_request` triggern. Trade-off: +~5 Min pro PR, dafuer kein `--admin` mehr noetig. Nicht kritisch solange Solo-Dev.

### 4. `workflow_dispatch` ignoriert `paths`-Filter

**Symptom:** Manueller Deploy wird ausgefuehrt, obwohl nur docs/-Dateien geaendert wurden.

**Ursache:** `paths`-Filter gelten nur fuer `push` und `pull_request` Events, nicht fuer `workflow_dispatch`. Ein manueller Trigger baut immer neu.

**Anwendung:** Bei kleinen Doku-Aenderungen ohne Deploy-Bedarf NICHT manuell triggern, normalen Push-Flow nutzen (der Paths-Filter greift).

### 5. OpenSearch-Passwort MUSS explizit in `--set` stehen (PROD)

**Symptom:** PROD-Deploy crasht OpenSearch-Pod mit Authentication-Fehler. Chart-Default-Passwort wird statt GitHub-Secret verwendet.

**Ursache:** Fehlender `--set "auth.opensearch.values.opensearch_admin_password=${{ secrets.OPENSEARCH_PASSWORD }}"` im Workflow.

**Anwendung:** Bei Helm-Upgrade PROD IMMER `--set` explizit mitgeben. Vergleiche `stackit-deploy.yml`:
```yaml
helm upgrade ... \
  --set "auth.opensearch.values.opensearch_admin_password=${{ secrets.OPENSEARCH_PASSWORD }}"
```

### 6. Smoke-Test-Timeout zu niedrig fuer Cold Start

**Symptom:** Smoke Test `curl /api/health` schlaegt fehl, obwohl API-Server 2 Minuten spaeter verfuegbar ist.

**Ursache:** Default Smoke-Test-Timeout (12 Versuche × 10s = 2 Min) reicht bei Cold Start (Alembic-Migrations + Model-Server-Pull) nicht aus.

**Anwendung:** Bei Upstream-Syncs oder erster Provisionierung Smoke-Test manuell verlaengern oder nach Deploy-Completion separat pruefen:
```bash
for i in $(seq 1 30); do
  curl -sS https://chatbot.voeb-service.de/api/health && break
  sleep 10
done
```

### 7. `--wait --timeout 15m` bei Helm rollt NICHT zurueck

**Symptom:** Helm-Upgrade Timeout → Pods bleiben in CrashLoop, Release-Status "failed".

**Ursache:** `--wait` ohne `--atomic` rollt bei Timeout NICHT zurueck (das ist beabsichtigt — bessere Debug-Bedingungen).

**Anwendung:** Bei "failed"-Release zuerst Logs pruefen, dann manuell `helm rollback <name> <REVISION>` aufrufen. Siehe `docs/runbooks/rollback-verfahren.md`.

### 8. Recreate-Strategie verschwindet nach `helm rollback`

**Symptom:** Nach Rollback laufen Pods im RollingUpdate-Modus → alte + neue Pods gleichzeitig → DB Pool Exhaustion.

**Ursache:** `kubectl patch` im Workflow setzt `strategy.type: Recreate` nach jedem Helm-Upgrade. Helm-Rollback uebertraegt diese Patch-Aenderung nicht (ist nur auf der Live-Resource, nicht in der Chart-Revision).

**Anwendung:** Nach Rollback SOFORT den Patch-Step manuell wiederholen:
```bash
for DEPLOYMENT in $(kubectl get deployments -n onyx-prod -o name); do
  kubectl patch "$DEPLOYMENT" -n onyx-prod -p '{"spec":{"strategy":{"type":"Recreate"}}}'
done
```
Alternativ: `stackit-deploy.yml` mit dem alten funktionierenden Image-Tag triggern.

---

## 7. Entscheidungslog

Dokumentation der "Warum"-Fragen für Audits und Nachvollziehbarkeit.

### Warum SHA-gepinnte Actions?

GitHub Actions mit Major-Version-Tags (`@v4`) können jederzeit vom Maintainer geändert werden. Ein kompromittiertes Action-Repository könnte Code injizieren, der Secrets exfiltriert. SHA-Pinning fixiert den exakten Stand und erfordert bewusste Updates. Relevant für: BSI-Grundschutz APP.6, orientiert an BAIT (Nachvollziehbarkeit).

### Warum kein eigener Model Server Build?

Der Onyx Model Server (Embedding + Reranking) ist reiner Upstream-Code. Wir ändern nichts daran. Ein eigener Build:
- Dauert ~12 Minuten
- Erzeugt ein identisches Image
- Verursachte ImagePullBackOff (StackIT Registry Latenz)

Docker Hub Image ist öffentlich, schnell, und mit `v2.9.8` gepinnt.

### Warum Recreate statt RollingUpdate (DEV)?

Der DEV-Cluster hat 2 Nodes (g1a.4d, 4 vCPU je, Downgrade seit 2026-03-16). Recreate ist beibehalten um Port-Konflikte bei Model Servern zu vermeiden und bei begrenzten Ressourcen keine Pending-Pods zu erzeugen. Downtime ist für DEV akzeptabel.

> **Wichtig bei Rollback:** `helm rollback` setzt die Deployment-Strategie auf den Helm-Chart-Default (RollingUpdate) zurück. Nach einem Rollback muss der `kubectl patch`-Schritt aus dem CI/CD-Workflow manuell wiederholt werden, um Recreate zu reaktivieren. Alternativ: erneuter Workflow-Run mit dem funktionierenden Image-Tag (`-f image_tag=<IMAGE_TAG>`).

### Warum `LICENSE_ENFORCEMENT_ENABLED: "false"`?

Onyx FOSS hat seit einer neueren Version den Default `"true"` für diese Variable. Das aktiviert Enterprise-Edition-Code-Pfade, die das Modul `onyx.server.tenants` importieren. Dieses Modul existiert nur im proprietären EE-Repository. Ohne die explizite Deaktivierung crasht der API-Server mit `ModuleNotFoundError`.

### Warum `--wait --timeout 15m` statt `--atomic`?

Alle Environments nutzen `--wait --timeout 15m` statt `--atomic`. `--atomic` würde bei Timeout automatisch zurückrollen, was bei 16+ Pods mit Cold Start (Alembic Migrations, Model Server) kontraproduktiv ist — der Rollback verursacht einen weiteren Neustart-Zyklus. Mit `--wait` bleibt der Release bei Timeout stehen und kann debuggt werden.

### Warum Redis-Passwort als GitHub Secret?

War vorher hardcoded in `values-dev.yaml` — steht im Git-Repository. Credentials gehören nicht in Git, auch nicht für DEV. Alle anderen Credentials (PG, S3) waren bereits als Secrets konfiguriert.

### OpenSearch-Migration (2026-03-19 DEV, 2026-03-22 PROD)

Onyx migriert von Vespa auf OpenSearch als Vektor-Datenbank (ab v4.0.0 entfernt Vespa komplett). Der CI/CD-Workflow muss `OPENSEARCH_PASSWORD` als Secret bereitstellen — der Chart-Default ist ein bekanntes Passwort und darf in Produktion nicht verwendet werden. Vespa läuft in einem Übergangsmodus ("Zombie-Mode") bis die Migration abgeschlossen ist; erst danach kann der Vespa-Pod entfernt werden. Details: `memory/project_opensearch-migration.md`.

---

## 8. Wartung

### Regelmäßig prüfen

| Was | Wann | Wie |
|-----|------|-----|
| Kubeconfig-Ablauf | Monatlich | Beide Kubeconfigs pruefen: DEV/TEST `vob-chatbot` (aktuell: 2026-06-14) + PROD `vob-prod` (aktuell: 2026-06-22) |
| GitHub Actions Updates | Bei Dependabot-Alert oder monatlich | SHA im Workflow gegen neuestes Release-Tag prüfen |
| Model Server Version | Bei Onyx-Release | Docker Hub Tags prüfen, `MODEL_SERVER_TAG` aktualisieren |
| Robot Account Token | Bei Ablauf | StackIT Portal → Container Registry → Robot Account |
| Helm Chart Updates | Bei Upstream-Merge | `helm dependency build` nach Merge testen |

### GitHub Actions SHA aktualisieren

```bash
# Aktuellen SHA für ein Action-Tag ermitteln
gh api repos/actions/checkout/git/ref/tags/v4 --jq '.object.sha'

# Im Workflow ersetzen:
# ALT: uses: actions/checkout@<alter-sha> # v4
# NEU: uses: actions/checkout@<neuer-sha> # v4
```

---

## Eskalation

| Situation | Aktion | Kontakt |
|-----------|--------|---------|
| Runbook-Schritte schlagen fehl | Troubleshooting-Tabelle pruefen, ggf. Rollback | Tech Lead (CCJ) |
| PROD-Ausfall > 15 Min | Incident-Prozess starten (P1/P2) | Tech Lead (CCJ), VÖB Operations [AUSSTEHEND] |
| StackIT-Infrastruktur-Problem | StackIT Support kontaktieren | StackIT Support [AUSSTEHEND] |

> Vollstaendiger Eskalationsprozess: Siehe `docs/betriebskonzept.md` Abschnitt "Incident Management" und `docs/runbooks/rollback-verfahren.md`.

---

## Verwandte Runbooks

- [Helm Deploy](./helm-deploy.md) — Manuelles Helm-Deployment oder -Update
- [Rollback-Verfahren](./rollback-verfahren.md) — Rollback bei fehlerhaftem Deploy
