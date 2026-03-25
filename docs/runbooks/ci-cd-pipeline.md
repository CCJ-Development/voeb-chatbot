# CI/CD Pipeline — Runbook

> **Workflow**: `.github/workflows/stackit-deploy.yml`
> **Verifiziert**: 2026-03-02 (Run #5, Commit `ea70a11`)
> **Letzte Änderung**: 2026-03-22
>
> **Hinweis:** Seit Upstream-Sync #4 (2026-03-22) existiert `.github/workflows/storybook-deploy.yml` (Storybook Deploy). Harmlos, kann bei Bedarf deaktiviert werden.

---

## Zweck

**Wann dieses Runbook verwenden:**
- Deployment auf DEV, TEST oder PROD ausloesen (automatisch oder manuell)
- Deploy-Status pruefen und Pipeline-Fehler debuggen
- Secrets (Kubeconfig, Registry, DB) aktualisieren oder rotieren

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
curl https://test.chatbot.voeb-service.de/api/health   # TEST (heruntergefahren seit 2026-03-19)
curl https://chatbot.voeb-service.de/api/health         # PROD (HTTPS LIVE seit 2026-03-17)
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
  -f image_tag=<FUNKTIONIERENDER_TAG>
```

### Notfall: Direkter Image-Wechsel

Ohne Pipeline, direkt auf dem Cluster:

```bash
kubectl set image deployment/onyx-dev-api-server \
  api-server=registry.onstackit.cloud/voeb-chatbot/onyx-backend:<TAG> \
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

> **Wichtig bei Rollback:** `helm rollback` setzt die Deployment-Strategie auf den Helm-Chart-Default (RollingUpdate) zurück. Nach einem Rollback muss der `kubectl patch`-Schritt aus dem CI/CD-Workflow manuell wiederholt werden, um Recreate zu reaktivieren. Alternativ: erneuter Workflow-Run mit dem funktionierenden Image-Tag (`-f image_tag=<TAG>`).

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
