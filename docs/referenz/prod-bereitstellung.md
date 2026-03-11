# PROD-Bereitstellung — Planungsdokument

**Status:** In Planung (Review-Runde 1 abgeschlossen: 2026-03-11)
**Erstellt:** 2026-03-11
**Letzte Aktualisierung:** 2026-03-11 — Alle Klaerungspunkte bearbeitet, Enterprise Best Practices angewendet
**Autor:** CCJ / Coffee Studios (Nikolaj Ivanov)
**Ziel-URL:** `https://chatbot.voeb-service.de`

---

## 1. Uebersicht

### 1.1 Kontext

Die DEV- und TEST-Umgebungen laufen seit Februar/Maerz 2026 stabil auf einem geteilten SKE-Cluster (`vob-chatbot`). Gemaess ADR-004 wird PROD auf einem **eigenen, dedizierten SKE-Cluster** betrieben. Dieses Dokument beschreibt alle Schritte, Abhaengigkeiten und offenen Punkte fuer die PROD-Bereitstellung.

### 1.2 Aktueller Stand (2026-03-11)

| Komponente | DEV | TEST | PROD |
|------------|-----|------|------|
| SKE Cluster | `vob-chatbot` (shared) | `vob-chatbot` (shared) | **Nicht provisioniert** |
| Namespace | `onyx-dev` (16 Pods) | `onyx-test` (15 Pods) | — |
| PostgreSQL | Flex 2.4 Single `vob-dev` | Flex 2.4 Single `vob-test` | — |
| Object Storage | `vob-dev` | `vob-test` | — |
| Domain | `dev.chatbot.voeb-service.de` | `test.chatbot.voeb-service.de` | `chatbot.voeb-service.de` (geplant) |
| TLS | HTTPS LIVE (Let's Encrypt) | HTTPS LIVE (Let's Encrypt) | — |
| Auth | Basic (kein OIDC) | Basic (kein OIDC) | OIDC (Entra ID) — geplant |
| Monitoring | kube-prometheus-stack | (shared mit DEV) | — |
| CI/CD Job | `deploy-dev` (auto) | `deploy-test` (manuell) | `deploy-prod` (manuell, Review) |
| Helm Values | `values-dev.yaml` | `values-test.yaml` | `values-prod.yaml` (Platzhalter) |
| Terraform | `environments/dev/` | `environments/test/` | **`environments/prod/` fehlt** |

### 1.3 Architekturentscheidung: Eigener Cluster

**Referenz:** ADR-004 (Umgebungstrennung DEV/TEST/PROD)

PROD laeuft auf einem **separaten SKE-Cluster** (nicht shared mit DEV/TEST). Begruendung:

1. **Blast Radius** — DEV/TEST-Fehler duerfen PROD nie beeinflussen
2. **Eigenes Maintenance-Window** — K8s-Upgrades unabhaengig planbar
3. **Strengere Security** — eigene RBAC, Audit Logging, Kubeconfig-Trennung
4. **Compliance** — nachweisbare Trennung Produktiv vs. Test (BAIT/BSI)
5. **Eigene Kubeconfig** — verschiedene Credentials, verschiedene Zugriffsrechte

---

## 2. PROD Zielzustand

### 2.1 Compute

| Parameter | Wert | Referenz |
|-----------|------|----------|
| Cluster-Name | `vob-prod` (oder `vob-chatbot-prod`, max 11 Zeichen) | Zu klaeren |
| Kubernetes-Version | `1.33` (aktuell, identisch DEV/TEST) | — |
| Node Pool | `prod`, 2x g1a.8d (8 vCPU, 32 GB RAM, 100 GB Disk) | ADR-005 |
| Allokierbare Kapazitaet | ~15.8 CPU, ~56.6 Gi RAM (2 Nodes) | stackit-infrastruktur.md |
| Erwartete Auslastung | CPU ~40%, RAM ~25% (bei 150 Usern) | stackit-infrastruktur.md |
| Availability Zone | `eu01-3` (Frankfurt) | — |
| Region | `eu01` | — |

### 2.2 Datenbank

| Parameter | Wert | Begruendung |
|-----------|------|-------------|
| Instanz-Name | `vob-prod` | Namenskonvention |
| Konfiguration | Flex 4.8 Replica | HA-Pflicht fuer PROD |
| CPU / RAM | 4 vCPU / 8 GB | Doppelte DEV/TEST-Kapazitaet |
| Replicas | 3 (Primary + 2 Standby) | Automatisches Failover |
| Storage | 50 GB, `premium-perf2-stackit` | Mehr als DEV/TEST (20 GB) |
| Backup | PITR (automatisch), Cron `0 1 * * *` (01:00 UTC) | Separates Fenster, kein Overlap mit DEV (02:00) / TEST (03:00) |
| ACL | Cluster-Egress-IP + Admin-IP | SEC-01 |

### 2.3 Object Storage

| Parameter | Wert |
|-----------|------|
| Bucket-Name | `vob-prod` |
| Endpoint | `https://object.storage.eu01.onstackit.cloud` |

### 2.4 Netzwerk / DNS / TLS

| Parameter | Wert |
|-----------|------|
| Domain | `chatbot.voeb-service.de` |
| DNS A-Record | `chatbot.voeb-service.de` → `[PROD-LB-IP]` |
| TLS | Let's Encrypt, ECDSA P-384, TLSv1.3 (BSI TR-02102) |
| cert-manager | DNS-01 via Cloudflare. **Version bei PROD-Deploy bewusst waehlen** (DEV/TEST: v1.19.4, nicht im Code fixiert) |
| HSTS | `max-age=31536000; includeSubDomains` (1 Jahr, PROD-Wert) |
| Load Balancer | Essential Network Load Balancer (NLB-10) |
| IngressClass | `nginx` (kein Namenskonflikt, eigener Cluster) |

### 2.5 Auth

| Parameter | Wert | Status |
|-----------|------|--------|
| AUTH_TYPE | `oidc` | **Blockiert — wartet auf Entra ID von VoEB IT** |
| Fallback | `basic` (temporaer, bis Entra ID bereit) | Entscheidung offen |
| Provider | Microsoft Entra ID | — |
| Protokoll | OpenID Connect (OIDC) | — |

### 2.6 Replicas / HA (Zielzustand)

| Komponente | Replicas | Begruendung |
|------------|----------|-------------|
| API Server | 2 | HA — kein Single-Point-of-Failure |
| Web Server | 2 | HA |
| Celery Primary | 2 | HA — kritischster Worker |
| Celery Beat | 1 | Singleton (Scheduler) |
| Celery Light/Heavy/DocFetch/DocProcess/Monitoring/UserFile | je 1 | ✅ **Gesetzt** (2026-03-11). Worker-Isolation = Onyx Standard Mode. 0 Replicas = Feature offline |
| Vespa | 1 | HA erfordert Content-Cluster-Config (spaeter evaluieren) |
| Redis | 1 | In-Cluster Standalone |
| Model Server (Inference + Index) | je 1 | Self-hosted Embedding |

> **Stand 2026-03-11:** Alle Celery-Worker auf Zielwerte gesetzt (`values-prod.yaml` aktualisiert). 6 Worker von `replicaCount: 0` auf `1` korrigiert. Begruendung: Worker-Isolation ist Onyx Best Practice (Standard Mode seit PR #9014). Jeder Worker hat eine spezialisierte Aufgabe — 0 Replicas bedeutet Feature offline (kein Document Processing, kein Monitoring Worker, etc.). 150 User benoetigen alle Worker-Typen.

---

## 3. Aufgabenliste

### Legende

- `[x]` = Erledigt
- `[ ]` = Offen
- `[B]` = Blockiert (externer Blocker)
- `[K]` = Klaerungsbedarf (Entscheidung noetig)

---

### Phase A: Terraform — PROD-Infrastruktur provisionieren

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| A1 | Terraform-Modul fuer PROD erstellen | [ ] | — | `environments/prod/main.tf` — nutzt `modules/stackit` (nicht `stackit-data`), da eigener Cluster |
| A2 | Cluster-Name festlegen | [K] | — | Max 11 Zeichen. Optionen: `vob-prod`, `voeb-prod`, `vob-chat-p`. Muss eindeutig im StackIT-Projekt sein |
| A3 | Node Pool konfigurieren | [ ] | A1 | Pool `prod`, 2x g1a.8d, `eu01-3`, Volume 100 GB `premium-perf2-stackit` |
| A4 | PG Flex 4.8 Replica provisionieren | [ ] | A1 | 3-Node HA, 4 CPU / 8 GB RAM, 50 GB Storage, Backup 01:00 UTC |
| A5 | PG ACL konfigurieren | [ ] | A4, A3 | Cluster-Egress-IP (erst nach Cluster-Erstellung bekannt) + Admin-IP. **Achtung:** PROD-Cluster hat eigene Egress-IP! |
| A6 | PG Datenbank `onyx` manuell anlegen | [ ] | A4 | Terraform erstellt nur Instanz + User, nicht die DB. `psql -h <host> -U onyx_app -c "CREATE DATABASE onyx;"` |
| A7 | Object Storage Bucket `vob-prod` erstellen | [ ] | A1 | Per Terraform |
| A8 | S3 Credentials erstellen | [ ] | A7 | StackIT Console → Object Storage → Credentials. Fuer GitHub Secret |
| A9 | `terraform apply` ausfuehren | [ ] | A1-A8 | Geschaetzte Dauer: ~10-15 Min. Outputs sichern: `pg_host`, `pg_password`, `pg_readonly_password`, `kubeconfig` |
| A10 | PROD-Egress-IP ermitteln | [ ] | A9 | `kubectl get nodes -o wide` → ExternalIP, oder NAT Gateway IP aus StackIT Console. Wird fuer PG ACL (A5) und NetworkPolicies benoetigt |

**Offene Fragen Phase A:**

- [ ] **A2:** Cluster-Name — Vorschlag `vob-prod` (7 Zeichen, passt)
- [ ] **A5:** Admin-IP fuer PG ACL — gleiche wie DEV/TEST (`109.41.112.160/32`) oder andere?
- [ ] Soll PROD im gleichen StackIT-Projekt laufen wie DEV/TEST, oder in einem separaten Projekt?

---

### Phase B: Kubernetes-Basis (nach Cluster-Provisioning)

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| B1 | Kubeconfig fuer PROD-Cluster holen | [ ] | A9 | `terraform output -raw kubeconfig > ~/.kube/config-prod`. Ablaufdatum notieren! |
| B2 | Kubeconfig base64-encodieren | [ ] | B1 | Fuer GitHub Secret: `base64 -i config-prod` |
| B3 | Image Pull Secret erstellen | [ ] | B1 | `kubectl create secret docker-registry stackit-registry --docker-server=registry.onstackit.cloud --docker-username=<USER> --docker-password=<TOKEN> -n onyx-prod` |
| B4 | cert-manager installieren | [ ] | B1 | `helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set crds.enabled=true` |
| B5 | Cloudflare API Token Secret erstellen | [ ] | B4 | `kubectl create secret generic cloudflare-api-token -n cert-manager --from-literal=api-token=<TOKEN>` — gleicher Token wie DEV/TEST |
| B6 | ClusterIssuer erstellen | [ ] | B4, B5 | `onyx-prod-letsencrypt`, DNS-01 via Cloudflare, Production ACME Server. Analog DEV/TEST (siehe `docs/runbooks/dns-tls-setup.md`) |
| B7 | ACME-Challenge CNAME bei GlobVill beantragen | [K] | B6 | `_acme-challenge.chatbot.voeb-service.de` → Cloudflare Zone. Muss Leif bei GlobVill setzen (wie bei DEV/TEST) |
| B8 | Redis Operator installieren | [ ] | B1 | `helm install redis-operator ot-container-kit/redis-operator --namespace onyx-prod` |
| B9 | Namespace `onyx-prod` erstellen | [ ] | B1 | Wird automatisch durch `helm upgrade --create-namespace` erstellt, kann aber vorab fuer Secrets noetig sein |

**Offene Fragen Phase B:**

- [ ] **B5:** Reicht der bestehende Cloudflare API Token (gleicher wie DEV/TEST)? Oder braucht PROD einen eigenen?
- [ ] **B7:** Leif (GlobVill) muss ACME-CNAME setzen — fruehzeitig anfragen!
- [ ] **B1:** Kubeconfig-Ablauf — DEV/TEST laeuft am 2026-05-28 ab. PROD-Kubeconfig gleich mit laengerem Ablauf erstellen?

---

### Phase C: DNS + TLS

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| C1 | PROD LoadBalancer IP ermitteln | [ ] | Erster Helm Deploy (D5) | NGINX Ingress Service → External IP |
| C2 | DNS A-Record setzen | [ ] | C1 | `chatbot.voeb-service.de` → `[PROD-LB-IP]`. Bei GlobVill/Cloudflare |
| C3 | ACME-Challenge CNAME verifizieren | [ ] | B7, C2 | `dig _acme-challenge.chatbot.voeb-service.de CNAME` |
| C4 | Certificate-Ressource erstellen | [ ] | B6, C3 | ECDSA P-384, DNS Names: `chatbot.voeb-service.de` |
| C5 | HTTPS verifizieren | [ ] | C4 | `curl -vI https://chatbot.voeb-service.de`, TLSv1.3, HTTP/2 pruefen |
| C6 | Cloudflare Proxy-Modus pruefen | [ ] | C2 | DNS-only (kein Proxy!) — sonst IP-Mismatch. Analog DEV/TEST |

**Hinweis:** C1 erfordert einen initialen Helm Deploy (Phase D). DNS kann erst danach gesetzt werden. Workaround: Erster Deploy ohne TLS (HTTP), dann TLS nachruestbar.

---

### Phase D: GitHub + Helm Deploy

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| D1 | GitHub Environment `prod` erstellen | [ ] | — | Settings → Environments → New |
| D2 | Required Reviewers aktivieren | [ ] | D1 | Mindestens 1 Reviewer (Niko) fuer PROD-Deployments |
| D3 | GitHub Secrets anlegen (Environment: prod) | [ ] | A9, B2 | 6 Secrets: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `DB_READONLY_PASSWORD`, `STACKIT_KUBECONFIG` |
| D4 | PROD-Kubeconfig als Environment-Secret anlegen | [ ] | D3 | Der Workflow liest `secrets.STACKIT_KUBECONFIG` — GitHub resolved Environment-Secrets vor Repository-Secrets. Es reicht, `STACKIT_KUBECONFIG` als Secret im GitHub Environment `prod` anzulegen. **Kein Workflow-Code-Aenderung noetig.** DEV/TEST nutzen weiterhin das globale Repository-Secret |
| D5 | `values-prod.yaml` vervollstaendigen | [~] | A9 | ✅ Celery Worker (6×) auf replicaCount: 1 gesetzt, HSTS auf 31536000 (1 Jahr), Ingress-Block ergaenzt, Extension-Flags ergaenzt (2026-03-11). ⏳ `POSTGRES_HOST` noch offen (braucht Terraform Output) |
| D6 | Erster PROD Deploy | [ ] | D1-D5, B3-B8 | `gh workflow run stackit-deploy.yml -f environment=prod` |
| D7 | Recreate-Strategie patchen | [x] | D6 | ✅ **Geloest (2026-03-11).** "Patch deployment strategy and wait (PROD)"-Step in `stackit-deploy.yml` ergaenzt (analog DEV Z.234-260 / TEST Z.356-382). Patcht 10 Deployments auf Recreate-Strategie + wartet auf Rollout. Enterprise-Begruendung: RollingUpdate fuehrt bei Onyx zu DB-Connection-Pool-Exhaustion (monitoring-konzept.md Lesson Learned #8) |
| D8 | Smoke Test verifizieren | [ ] | D6 | `/api/health` erreichbar, alle Pods Running |
| D9 | DB-Migration pruefen | [ ] | D6 | Alembic-Migrationen (inkl. ext_-Tabellen) muessen auf PROD-DB laufen. Wird automatisch beim ersten API-Start ausgefuehrt |

**Offene Fragen Phase D:**

- [x] **D4:** ~~Kubeconfig-Trennung~~ — Geloest: `STACKIT_KUBECONFIG` als Environment-Secret unter `prod` anlegen. GitHub Actions resolved Environment-Secrets automatisch vor Repository-Secrets → kein Code-Aenderung am Workflow noetig. DEV/TEST nutzen weiterhin das globale Repository-Secret
- [x] **D5 (teilweise):** ~~Celery Worker replicaCounts~~ — Geloest (2026-03-11): Alle 6 Worker von 0 auf 1 gesetzt. HSTS auf 1 Jahr. Ingress-Block ergaenzt. Extension-Flags ergaenzt. ⏳ POSTGRES_HOST wartet auf Terraform.
- [x] **D7:** ~~Recreate-Patch~~ — Geloest (2026-03-11): "Patch deployment strategy and wait (PROD)"-Step in CI/CD Workflow ergaenzt. Patcht 10 Deployments + wartet auf Rollout (analog DEV/TEST).

---

### Phase E: Security-Haertung (Pflicht vor Go-Live)

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| E1 | SEC-06 Phase 2: `runAsNonRoot: true` | [ ] | D6 | `runAsUser: 1001` + `runAsNonRoot: true` fuer alle Container (ausser Vespa). Onyx Dockerfile definiert User `onyx` UID 1001. Zuerst auf DEV/TEST testen! |
| E2 | NetworkPolicies PROD erstellen | [ ] | D6, A10 | Default-Deny + Allow-Policies. DEV/TEST haben aktuell 7 Policies im App-NS (5 Basis-SEC-03 + Monitoring-Scrape + Redis-Exporter-Ingress) + 7 im Monitoring-NS. PROD analog, ggf. granularer (per-Pod Egress fuer PG, S3, LLM API) |
| E3 | NetworkPolicies Monitoring-NS erstellen | [ ] | F1 | Analog `deployment/k8s/network-policies/monitoring/` |
| E4 | Cluster ACL pruefen | [ ] | A9 | `cluster_acl` in Terraform — soll PROD-API-Server nur von bestimmten IPs erreichbar sein? |
| E5 | HSTS Header auf 1 Jahr setzen | [x] | D5 | ✅ **Geloest (2026-03-11).** `values-prod.yaml` ueberschreibt `nginx.controller.config.http-snippet` mit `max-age=31536000` (1 Jahr). DEV/TEST bleiben bei `max-age=3600` (1h) aus `values-common.yaml`. BSI TR-02102: min. 6 Monate. OWASP: 1 Jahr + includeSubDomains. Env-spezifischer Override = Clean Architecture |
| E6 | Resource Quotas setzen | [~] | D6 | **Korrigiert (2026-03-11):** CPU: 12, RAM: 20 Gi (statt CPU: 8, RAM: 24 GB). Alter CPU-Wert war UNTER dem berechneten Bedarf (8.75 CPU Requests)! Berechnung: Summe aller Pod CPU/RAM Requests aus values-prod.yaml + 30-37% Buffer. stackit-infrastruktur.md aktualisiert. ResourceQuota-Manifest muss bei PROD-Deploy erstellt werden |
| E7 | Vespa Security evaluieren | [K] | D6 | Vespa laeuft als root (runAsUser: 0). Upstream-Limitation. Akzeptieren oder Subchart-Default (UID 1000) testen? |

**Offene Fragen Phase E:**

- [ ] **E1:** SEC-06 Phase 2 zuerst auf DEV/TEST validieren. Vespa ist dokumentierte Ausnahme (braucht root fuer `vm.max_map_count`)
- [ ] **E4:** Soll der PROD K8s API-Server per ACL eingeschraenkt werden (nur CI/CD Runner-IP + Admin)? Oder offen lassen?
- [ ] **E6:** Resource Quotas — sollen wir LimitRanges pro Pod zusaetzlich setzen?

---

### Phase F: Monitoring + Alerting

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| F1 | kube-prometheus-stack auf PROD-Cluster deployen | [ ] | B1 | Eigener Helm Release `monitoring` im Namespace `monitoring`. `values-monitoring.yaml` wiederverwenden |
| F2 | postgres_exporter fuer PROD erstellen | [x] | A9, F1 | ✅ **Geloest (2026-03-11).** `deployment/k8s/monitoring-exporters/pg-exporter-prod.yaml` erstellt. Identisch mit DEV/TEST-Struktur. Secret `pg-exporter-prod` muss bei Deploy manuell erstellt werden (DATA_SOURCE_NAME mit PROD-PG-Host) |
| F3 | redis_exporter fuer PROD erstellen | [x] | D6, F1 | ✅ **Geloest (2026-03-11).** `deployment/k8s/monitoring-exporters/redis-exporter-prod.yaml` erstellt. Target: `onyx-prod.onyx-prod.svc.cluster.local:6379`. Secret `redis-exporter-prod` muss bei Deploy manuell erstellt werden |
| F4 | Grafana Dashboards importieren | [ ] | F1 | PG Dashboard (ID 14114) + Redis Dashboard (ID 763). **Bekanntes Problem:** Nicht persistent bei Pod-Restart. Loesung: ConfigMap oder Grafana Provisioning evaluieren |
| F5 | AlertManager → Teams konfigurieren | [ ] | F1 | Gleicher Teams Webhook wie DEV/TEST, oder eigener PROD-Kanal? `send_resolved: true` |
| F6 | PROD-spezifische Alert-Rules pruefen | [ ] | F5 | 20 Alert-Rules aus DEV/TEST uebernehmen. Schwellwerte fuer PROD anpassen (hoehere Basislast) |
| F7 | Monitoring NetworkPolicies | [ ] | E3, F1 | 7 Policies in `monitoring` NS + App-NS Ingress-Policies |

**Offene Fragen Phase F:**

- [ ] **F4:** Grafana Dashboards persistent machen → **Entscheidung (2026-03-11): ConfigMap Provisioning.** Enterprise Best Practice: Kein manueller Zustand auf PROD. Alles was bei Pod-Restart verloren geht ist unakzeptabel. Grafana sidecar.dashboards liest JSON aus ConfigMaps → automatischer Import bei jedem Start. BSI OPS.1.1.2: "Wiederherstellbarkeit sicherstellen". Umsetzung bei F1 (kube-prometheus-stack Deploy auf PROD).
- [ ] **F5:** Eigener Teams-Kanal fuer PROD-Alerts → **Entscheidung (2026-03-11): Ja, eigener PROD-Kanal.** Enterprise Best Practice (ITIL Incident Management): PROD-Alerts duerfen nicht in DEV/TEST-Rauschen untergehen. Gleicher Kanal fuehrt zu "Alert Fatigue". Niko muss neuen Teams-Kanal erstellen + Webhook-URL bereitstellen.

---

### Phase G: Auth — Entra ID (OIDC)

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| G1 | Entra ID Zugangsdaten von VoEB erhalten | [B] | VoEB IT | **Blocker seit Projektstart.** Tenant ID, Client ID, Client Secret noetig |
| G2 | App-Registrierung in Entra ID | [B] | G1 | Redirect URI: `https://chatbot.voeb-service.de/auth/oauth/callback`. Anleitung: `docs/referenz/anleitung-entra-id-app-registration.docx` |
| G3 | OIDC-Secrets in GitHub Environment anlegen | [B] | G1, G2 | `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, etc. |
| G4 | `values-prod.yaml` Auth-Section befuellen | [B] | G1-G3 | `AUTH_TYPE: "oidc"`, Tenant ID, Discovery URL |
| G5 | Login-Flow testen | [B] | G4 | Redirect → Entra ID → Callback → Session |
| G6 | B2B-Gastzugang fuer CCJ | [B] | G1 | `n.ivanov@scale42.de` als Gastbenutzer in VoEB Tenant. Fuer Admin-Zugang nach Auth-Umstellung |
| G7 | Groups Claim konfigurieren | [B] | G1, ext-rbac | Fuer spaetere Gruppen-/Rollenzuordnung (Phase 4f) |

**Status:** Komplett blockiert durch fehlende Entra ID Zugangsdaten von VoEB IT.

**Fallback-Option:** PROD initial mit `AUTH_TYPE: "basic"` deployen (wie DEV/TEST), spaeter auf OIDC umstellen. **Entscheidung noetig.**

---

### Phase H: LLM + Embedding konfigurieren

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| H1 | Chat-Modelle in PROD konfigurieren | [ ] | D8 | 4 Modelle: GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, Llama 3.1 8B. Ueber Admin UI |
| H2 | Embedding-Modell konfigurieren | [ ] | D8 | Qwen3-VL-Embedding 8B (wie TEST). Ueber Admin UI |
| H3 | LLM API Key als Secret | [ ] | D6 | StackIT AI Model Serving Token. In `env-configmap` oder als Kubernetes Secret |
| H4 | Default-Modell festlegen | [K] | H1 | Welches Modell soll Default sein? GPT-OSS 120B (groesstes) oder Llama 3.3 70B (bestes Preis-Leistung)? |

---

### Phase I: Daten + Content (vor Nutzer-Freigabe)

| Nr | Aufgabe | Status | Abhaengigkeit | Detail |
|----|---------|--------|---------------|--------|
| I1 | Assistants / Personas erstellen | [ ] | H1 | PROD-spezifische Personas (z.B. "VoEB Assistent") |
| I2 | Connectors konfigurieren | [K] | D8 | Welche Datenquellen sollen angebunden werden? |
| I3 | Branding verifizieren | [ ] | D8 | Logo, App-Name, Login-Text, Greeting, Disclaimer. Analog DEV/TEST |
| I4 | System Prompts konfigurieren | [ ] | D8, I1 | Ueber Admin UI (ext-prompts) |
| I5 | Max Requests / Token Limits setzen | [K] | D8 | Ueber Admin UI (ext-token). Welche Limits fuer PROD? |

---

## 4. Abhaengigkeiten und Reihenfolge

```
Phase A: Terraform ──────────────────────────────────────────────────┐
  A1-A8: Infrastruktur definieren                                    │
  A9: terraform apply                                                │
  A10: Egress-IP ermitteln                                           │
                                                                     │
Phase B: K8s-Basis (nach A9) ───────────────────────────────────────┤
  B1-B2: Kubeconfig                                                  │
  B3: Image Pull Secret                                              │
  B4-B6: cert-manager + ClusterIssuer                                │
  B7: ACME-CNAME (Leif/GlobVill) ← Fruehzeitig anfragen!            │
  B8: Redis Operator                                                 │
                                                                     │
Phase D: GitHub + Deploy (nach B) ──────────────────────────────────┤
  D1-D3: GitHub Environment + Secrets                                │
  D4: CI/CD Kubeconfig-Trennung                                      │
  D5: values-prod.yaml                                               │
  D6: Erster Deploy → D7-D9: Verify                                  │
                                                                     │
Phase C: DNS + TLS (nach D6, braucht LB IP) ───────────────────────┤
  C1: LB IP → C2: DNS → C3-C5: TLS                                  │
                                                                     │
Phase E: Security (nach D6) ────────────────────────────────────────┤
  E1: runAsNonRoot (zuerst DEV/TEST!)                                │
  E2-E3: NetworkPolicies                                             │
  E4-E7: Haertung                                                    │
                                                                     │
Phase F: Monitoring (nach B1) ──────────────────────────────────────┤
  F1: kube-prometheus-stack                                          │
  F2-F3: Exporter                                                    │
  F4-F7: Dashboards + Alerting                                       │
                                                                     │
Phase G: Auth (blockiert) ──────────────────────────────────────────┤
  G1: Entra ID Zugangsdaten (VoEB IT)                                │
  G2-G7: App-Registrierung + OIDC                                   │
                                                                     │
Phase H+I: LLM + Content (nach D8) ────────────────────────────────┘
  H1-H4: Modelle
  I1-I5: Personas, Connectors, Branding
```

**Kritischer Pfad:** A → B → D → C (DNS) → Go-Live-Readiness
**Parallel moeglich:** F (Monitoring) ab B1, E (Security) ab D6

---

## 5. Offene Klaerungspunkte (Entscheidungen noetig)

### 5.1 Infrastruktur

| Nr | Frage | Optionen | Empfehlung | Entscheidung |
|----|-------|----------|------------|-------------|
| K1 | PROD im gleichen StackIT-Projekt oder separates Projekt? | (a) Gleich — einfacher, shared Registry (b) Separat — maximale Isolation | (a) Gleich — Container Registry wird geteilt, Kosten-Trennung nicht noetig | [ ] |
| K2 | Cluster-Name | `vob-prod` (7 Zeichen) | `vob-prod` | [ ] |
| K3 | Auth bei erstem Deploy | (a) Basic (temporaer) (b) Warten auf Entra ID | (a) Basic — ermoeglicht fruehes Setup + Testing | [ ] |
| K4 | Kubeconfig-Strategie im CI/CD | (a) Environment-Secret (b) Separates `_PROD` Secret | (a) Environment-Secret — GitHub resolved automatisch, kein Code-Aenderung noetig | [x] Geloest: Option (a) |

### 5.2 Security

| Nr | Frage | Optionen | Empfehlung | Entscheidung |
|----|-------|----------|------------|-------------|
| K5 | K8s API ACL | (a) Offen (0.0.0.0/0) (b) Eingeschraenkt (CI/CD + Admin) | (b) Eingeschraenkt — PROD sollte nicht offen sein. Enterprise Best Practice: Kubernetes API Server niemals oeffentlich exponieren. BSI APP.4.4.A7 (K8s): "Zugriff auf API-Server einschraenken". Terraform `cluster_acl` Variable existiert | [ ] |
| K6 | Resource Quotas | ~~(a) CPU 8, RAM 24 Gi~~ → **(a) CPU: 12, RAM: 20 Gi** (b) Keine Quotas | **(a) korrigiert** — CPU: 8 war UNTER dem berechneten Bedarf (8.75 CPU Requests)! | [x] **Geloest (2026-03-11):** CPU: 12 (8.75 benoetigte Requests + 37% Buffer), RAM: 20 Gi (15.25 Gi Requests + 31% Buffer). **Begruendung:** ResourceQuota muss >= Summe aller Pod-Requests sein, sonst koennen Pods nicht schedulen. Buffer erlaubt temporaere Debug-Pods und zukuenftige Skalierung. Berechnung: Summe aller Pod CPU Requests aus values-prod.yaml = 8.75 CPU (2×API 500m + 2×Web 250m + 1×Beat 250m + 2×Primary 500m + 6×Worker 500m/250m + Vespa 2000m + Redis 250m + 2×Model 500m). RAM analog: ~15.25 Gi. Alter Wert CPU: 8 haette Deployment verhindert! |
| K7 | SEC-06 Phase 2 Zeitpunkt | (a) Vor erstem PROD-Deploy (b) Nach stabilem Betrieb | **(a) — sauberer Start.** Enterprise Best Practice: Security-Haertung vor Inbetriebnahme, nicht nachruestbar. BSI SYS.1.6.A10: "Container sollten nicht als Root laufen". Vespa = dokumentierte Ausnahme (upstream runAsUser: 0 fuer vm.max_map_count) | [ ] |

### 5.3 Betrieb

| Nr | Frage | Optionen | Empfehlung | Entscheidung |
|----|-------|----------|------------|-------------|
| K8 | Teams-Kanal fuer PROD-Alerts | (a) Gleicher Kanal wie DEV/TEST (b) Eigener PROD-Kanal | **(b) Eigener Kanal.** Enterprise Best Practice: Prod-Alerts duerfen NICHT in DEV/TEST-Rauschen untergehen. ITIL Incident Management: Separate Kanaele pro Criticality Level. PROD-Alerts = Prio 1, DEV-Alerts = Prio 3. Gleicher Kanal fuehrt zu "Alert Fatigue" (DEV-Alerts werden ignoriert → PROD-Alerts werden uebersehen) | [ ] |
| K9 | Default LLM-Modell | GPT-OSS 120B / Qwen3-VL 235B / Llama 3.3 70B | Abhaengig von VoEB-Praeferenz | [ ] |
| K10 | Grafana Dashboards persistent? | (a) Manuell (b) ConfigMap Provisioning | **(b) ConfigMap Provisioning.** Enterprise Best Practice: Kein manueller Zustand auf PROD. Alles was bei Pod-Restart verloren geht = unakzeptabel. ConfigMap-basiertes Dashboard-Provisioning ist Grafana-Standard (sidecar.dashboards). Dashboards als JSON in ConfigMaps → automatischer Import bei jedem Start. BSI OPS.1.1.2: "Wiederherstellbarkeit sicherstellen" | [ ] |
| K11 | Maintenance-Window PROD | (a) 02:00-04:00 UTC (wie DEV/TEST) (b) Eigenes Fenster | **(b) Eigenes Fenster.** Enterprise Best Practice: PROD-Maintenance darf nie mit DEV/TEST-Maintenance kollidieren. Empfehlung: So 03:00-05:00 UTC. ITIL Change Management: Low-Impact-Window (Sonntag frueh). Kein Overlap mit PG-Backups (DEV 02:00, TEST 03:00, PROD 01:00 UTC) | [ ] |

### 5.4 Externe Abhaengigkeiten (VoEB / Dritte)

| Nr | Was | Wer | Status |
|----|-----|-----|--------|
| E-1 | Entra ID Zugangsdaten (Tenant ID, Client ID, Secret) | VoEB IT | **Blockiert** |
| E-2 | ACME-Challenge CNAME fuer `chatbot.voeb-service.de` | Leif (GlobVill) | **Noch nicht angefragt** |
| E-3 | DNS A-Record fuer `chatbot.voeb-service.de` | Leif (GlobVill) / Cloudflare | **Wartet auf LB IP** |
| E-4 | Datenquellen-Liste fuer Connectors | VoEB Fachbereich | **Noch nicht angefragt** |
| E-5 | Personas / Use Cases fuer PROD | VoEB Fachbereich | **Noch nicht angefragt** |
| E-6 | Token-/Request-Limits fuer PROD | VoEB Fachbereich | **Noch nicht geklaert** |

---

## 6. Terraform-Aenderungen (Technisches Detail)

### 6.1 Neues Environment `environments/prod/`

Das bestehende Terraform-Modul `modules/stackit` provisioniert Cluster + PG + S3. Fuer PROD wird ein neues Environment-Verzeichnis erstellt, das dieses Modul mit PROD-spezifischen Parametern aufruft:

```
deployment/terraform/environments/prod/
  main.tf          ← Ruft modules/stackit mit PROD-Werten auf
  backend.tf       ← State-Backend (analog dev/)
  terraform.tfvars ← Projekt-ID
```

### 6.2 PROD-spezifische Parameter (Abweichungen von DEV)

| Parameter | DEV | PROD |
|-----------|-----|------|
| `cluster_name` | `vob-chatbot` | `vob-prod` |
| `environment` | `dev` | `prod` |
| `node_pool.machine_type` | `g1a.8d` | `g1a.8d` |
| `node_pool.minimum/maximum` | 2 (shared DEV+TEST) | 2 (dedicated PROD) |
| `pg_flavor.cpu` | 2 | **4** |
| `pg_flavor.ram` | 4 | **8** |
| `pg_replicas` | 1 (Single) | **3 (Replica HA)** |
| `pg_storage_size` | 20 | **50** |
| `pg_backup_schedule` | `0 2 * * *` | `0 1 * * *` |
| `pg_acl` | Cluster-Egress + Admin | **PROD-Cluster-Egress + Admin** |
| `bucket_name` | `vob-dev` | `vob-prod` |

### 6.3 CI/CD Workflow-Aenderung

**Recreate-Patch-Step:** ✅ **Geloest (2026-03-11).** "Patch deployment strategy and wait (PROD)"-Step in `stackit-deploy.yml` ergaenzt. Patcht 10 Deployments (`onyx-prod-api-server`, `onyx-prod-celery-worker-primary`, `onyx-prod-celery-worker-light`, `onyx-prod-celery-worker-heavy`, `onyx-prod-celery-worker-docfetching`, `onyx-prod-celery-worker-docprocessing`, `onyx-prod-celery-worker-monitoring`, `onyx-prod-celery-worker-user-file-processing`, `onyx-prod-web-server`, `onyx-prod-celery-beat`) auf Recreate-Strategie. Wartet anschliessend auf Rollout aller 12 Deployments (inkl. `onyx-prod-indexing-model` + `onyx-prod-inference-model`). Timeout: 10 Min pro Deployment.

**Enterprise-Begruendung Recreate-Strategie:** RollingUpdate fuehrt bei Onyx zu DB-Connection-Pool-Exhaustion: Alte und neue Pods halten gleichzeitig DB-Connections → `max_connections` erschoepft → `TooManyConnectionsError` → CrashLoop. Dokumentiert in monitoring-konzept.md Lesson Learned #8 (2026-03-10). Recreate: Kurze Downtime (~30-60s), dafuer kein Datenverlust durch Deadlock.

**Kubeconfig:** Keine Workflow-Code-Aenderung noetig. `secrets.STACKIT_KUBECONFIG` wird automatisch aus dem GitHub Environment `prod` aufgeloest, wenn dort ein gleichnamiges Secret existiert. DEV/TEST nutzen weiterhin das globale Repository-Secret.

**Smoke Test:** PROD hat bereits einen laengeren Timeout (18 Versuche / 3 Min) gegenueber DEV/TEST (12 Versuche / 2 Min).

---

## 7. Kostenschaetzung PROD

| Ressource | PROD (monatlich) | DEV+TEST (monatlich) | Anmerkung |
|-----------|-----------------|---------------------|-----------|
| SKE Cluster (2x g1a.8d) | ~517 EUR | ~517 EUR | PROD: eigener Cluster. DEV+TEST: shared Cluster |
| PostgreSQL Flex | **~296 EUR** | ~100 EUR | PROD: Flex 4.8 Replica (4 CPU, 8 GB, **3 Nodes HA**). DEV+TEST: 2x Flex 2.4 Single (je ~50 EUR) |
| Object Storage | ~5 EUR | ~10 EUR | PROD: 1 Bucket. DEV+TEST: 2 Buckets |
| Load Balancer (NLB-10) | ~50 EUR | ~50 EUR | Je 1x IPv4 |
| LLM API (StackIT AI Model Serving) | ~96 EUR | ~191 EUR | PROD: 1 Env. DEV+TEST: 2 Envs |
| cert-manager / Let's Encrypt | 0 EUR | 0 EUR | Kostenlos |
| **Gesamt** | **~964 EUR** | **~868 EUR** | |

| | Monatlich | Jaehrlich |
|--|-----------|-----------|
| **DEV + TEST** | ~868 EUR | ~10.416 EUR |
| **PROD** | ~964 EUR | ~11.568 EUR |
| **Alle Environments** | **~1.832 EUR** | **~21.984 EUR** |

> **Referenzen:** ADR-005 (Kosten-Impact Tabelle: PROD ~964 EUR/Mo), ADR-004 (DEV+TEST ~868 EUR/Mo).
> Preise: StackIT Pricing API, Stand Maerz 2026. LLM-Kosten sind nutzungsabhaengig (Schaetzung fuer ~80 aktive Nutzer/Tag).
>
> **Warum ist PROD teurer als DEV+TEST zusammen?** Der Hauptkostentreiber ist die PostgreSQL HA-Konfiguration: PROD nutzt Flex 4.8 Replica mit 3 Nodes (Primary + 2 Standby, automatisches Failover) statt der einfachen Single-Instanzen bei DEV/TEST. Die dreifache Node-Anzahl bei doppelter Flavor-Groesse erklaert die ~296 EUR (vs. 2x ~50 EUR bei DEV+TEST).

---

## 8. Go-Live Checkliste (Pflicht vor Nutzer-Freigabe)

### Infrastruktur

- [ ] SKE Cluster `vob-prod` provisioniert und gesund
- [ ] Alle Pods Running (erwartet: ~20 Pods inkl. HA-Replicas)
- [ ] `/api/health` erreichbar und OK
- [ ] HTTPS aktiv, TLSv1.3, ECDSA P-384 (BSI TR-02102)
- [ ] DNS `chatbot.voeb-service.de` aufloesbar und korrekt

### Datenbank

- [ ] PG Flex 4.8 Replica (3 Nodes) gesund
- [ ] Datenbank `onyx` erstellt
- [ ] Alembic-Migrationen erfolgreich (inkl. ext_-Tabellen)
- [ ] PG ACL auf Cluster-Egress + Admin eingeschraenkt
- [ ] Backup-Schedule aktiv und erster Backup verifiziert

### Security

- [ ] SEC-06 Phase 2: `runAsNonRoot: true` aktiv (ausser Vespa)
- [ ] NetworkPolicies applied (Default-Deny + Allow-Rules)
- [ ] Image Pull Secret konfiguriert
- [ ] Keine Default-Credentials (Redis-Passwort, PG-Passwort individuell)
- [ ] HSTS Header auf `max-age=31536000` (1 Jahr)
- [ ] Security Headers verifiziert (X-Content-Type-Options, X-Frame-Options, etc.)

### Auth

- [ ] Entra ID OIDC konfiguriert und getestet — **ODER** bewusste Entscheidung fuer temporaeres Basic Auth dokumentiert
- [ ] Admin-Account erstellt
- [ ] B2B-Gastzugang fuer CCJ funktioniert (falls OIDC)

### Monitoring + Alerting

- [ ] Prometheus scrapet alle Targets
- [ ] Grafana erreichbar (PG + Redis Dashboards importiert)
- [ ] AlertManager → Teams-Kanal konfiguriert
- [ ] Alert-Rules aktiv (mind. 20 Rules)
- [ ] postgres_exporter + redis_exporter laufen

### Applikation

- [ ] Chat-Modelle konfiguriert (mind. GPT-OSS 120B + Qwen3-VL)
- [ ] Embedding-Modell konfiguriert (Qwen3-VL-Embedding 8B)
- [ ] Branding korrekt (Logo, App-Name, Login-Text)
- [ ] System Prompts konfiguriert (falls gewuenscht)
- [ ] Token Limits gesetzt (falls gewuenscht)

### Dokumentation

- [ ] Betriebskonzept aktualisiert (PROD-Spezifika)
- [ ] Sicherheitskonzept aktualisiert
- [ ] Rollback-Plan dokumentiert und getestet
- [ ] Incident-Prozess definiert
- [ ] M1-Abnahmeprotokoll abgeschlossen

### CI/CD

- [ ] GitHub Environment `prod` mit Required Reviewers
- [ ] PROD-Kubeconfig als Secret konfiguriert
- [ ] Deploy-Workflow getestet (mindestens 1 erfolgreicher Run)
- [ ] Rollback-Faehigkeit verifiziert (`helm rollback`)

---

## 9. Rollback-Strategie

### Helm Rollback

```bash
# Letzten erfolgreichen Release wiederherstellen
helm rollback onyx-prod -n onyx-prod

# Spezifische Revision
helm history onyx-prod -n onyx-prod
helm rollback onyx-prod <REVISION> -n onyx-prod
```

### Datenbank Rollback

- PostgreSQL PITR (Point-in-Time Recovery) ueber StackIT Console
- Alembic Downgrade: `alembic downgrade -1` (nur bei fehlerhafter Migration)

### Vollstaendiger Rollback

1. DNS auf Wartungsseite umleiten (oder A-Record entfernen)
2. `helm uninstall onyx-prod -n onyx-prod`
3. PG-Instanz per PITR wiederherstellen
4. Redeploy mit vorheriger Image-Version

---

## 10. Entscheidungsprotokoll (Review 2026-03-11)

Alle Entscheidungen, die waehrend der PROD-Bereitstellungsplanung getroffen wurden. Jede Entscheidung ist mit Enterprise Best Practices begruendet und nachvollziehbar dokumentiert.

### 10.1 Code-/Config-Aenderungen (implementiert)

| Nr | Aenderung | Datei(en) | Enterprise-Begruendung |
|----|-----------|-----------|----------------------|
| E1 | **Ingress-Block explizit in values-prod.yaml** — `className: "nginx"`, `host: "chatbot.voeb-service.de"` | `values-prod.yaml` | BSI SYS.1.6 (Container): Netzwerkkonfiguration muss explizit und nachvollziehbar sein. Chart-Defaults duerfen nie fuer Produktion verwendet werden. Jede Umgebung definiert ihren Ingress eigenstaendig. PROD auf eigenem Cluster (ADR-004), daher kein Namenskonflikt mit TEST (`nginx-test`) |
| E2 | **Extension-Flags aktiviert** — `EXT_TOKEN_LIMITS_ENABLED: "true"`, `EXT_CUSTOM_PROMPTS_ENABLED: "true"` | `values-prod.yaml` | 12-Factor App Principle X (Dev/Prod Parity): TEST und PROD muessen identisch konfiguriert sein. Features die auf TEST getestet und abgenommen sind, muessen auf PROD identisch aktiv sein. Abweichungen zwischen Environments fuehren zu "works on TEST"-Fehlern |
| E3 | **HSTS Override auf 1 Jahr** — `max-age=31536000; includeSubDomains` nur fuer PROD | `values-prod.yaml` (nginx.controller.config.http-snippet) | BSI TR-02102: HSTS mit min. 6 Monaten. OWASP: 1 Jahr + includeSubDomains. DEV/TEST bleiben bei 3600 (1h) aus values-common.yaml fuer Debugging-Flexibilitaet. Env-spezifischer Override statt Aenderung in values-common.yaml = Clean Architecture (Separation of Concerns) |
| E4 | **Celery Worker replicaCount: 0 → 1** (6 Worker) | `values-prod.yaml` | Worker-Isolation ist Onyx Best Practice (Standard Mode seit Upstream PR #9014). Jeder Worker hat eine spezialisierte Aufgabe. replicaCount: 0 = Feature offline (kein Document Processing, kein System-Monitoring, kein User-File-Processing). 150 User benoetigen alle Worker-Typen |
| E5 | **Recreate-Patch-Step fuer PROD** — 10 Deployments + Rollout-Wait | `stackit-deploy.yml` | RollingUpdate fuehrt bei Onyx zu DB-Connection-Pool-Exhaustion (monitoring-konzept.md Lesson Learned #8). Alte + neue Pods gleichzeitig → max_connections erschoepft → TooManyConnectionsError → CrashLoop. Recreate: Alle alten Pods zuerst beenden → Connections frei → neue Pods starten. Kurze Downtime (~30-60s), dafuer kein Datenverlust durch Deadlock |
| E6 | **PROD Monitoring-Exporter-Dateien erstellt** | `pg-exporter-prod.yaml`, `redis-exporter-prod.yaml` | BSI OPS.1.1.4 (Monitoring): Ueberwachung muss vor Inbetriebnahme eingerichtet sein. Day-0-Monitoring = Enterprise-Grundsatz. Kein Produktivsystem ohne Monitoring. Exporter-Manifeste vorbereitet, Secrets muessen bei Deploy manuell erstellt werden |

### 10.2 Dokumentations-Korrekturen (implementiert)

| Nr | Korrektur | Datei | Detail |
|----|-----------|-------|--------|
| D1 | **Resource Quotas korrigiert** | `stackit-infrastruktur.md` | Alter Wert: CPU: 8, RAM: 24 GB. Neuer Wert: CPU: 12, RAM: 20 Gi. Begruendung: CPU: 8 war UNTER dem berechneten Bedarf (8.75 CPU Requests aus values-prod.yaml). ResourceQuota muss >= Summe aller Pod-Requests sein. Berechnung: 2×API 500m + 2×Web 250m + 1×Beat 250m + 2×Primary 500m + 6×Worker (500m/250m) + Vespa 2000m + Redis 250m + 2×Model 500m = 8750m. RAM analog: 15250 Mi ≈ 15.25 Gi. Buffer: CPU +37% = 12, RAM +31% = 20 Gi |
| D2 | **PROD-Auslastung korrigiert** | `stackit-infrastruktur.md` | Alter Wert: "CPU ~40%, RAM ~25%". Neuer Wert: "CPU ~55% Requests / ~62% mit Monitoring, RAM ~27% / ~30% mit Monitoring". Begruendung: Alte Werte basierten auf DEV-Requests (die halb so gross sind wie PROD-Requests). Korrekte Berechnung: 8.75 CPU / 15.8 allocatable = 55%. Mit Monitoring (9.85 / 15.8) = 62% |
| D3 | **Monitoring-NS Policy-Anzahl korrigiert** | `monitoring-konzept.md` | Alter Wert: "5 Policies in monitoring". Neuer Wert: "7 Policies" (5 Basis + 2 Exporter-Egress seit Phase 4, 2026-03-10). Die Policies `06-allow-pg-exporter-egress` und `07-allow-redis-exporter-egress` wurden bei Phase 4 ergaenzt, aber die Zahl im Text nicht aktualisiert |

### 10.3 Entscheidungen (Niko, 2026-03-11)

| Nr | Frage | Entscheidung | Status |
|----|-------|------------|--------|
| O1 | PROD im gleichen StackIT-Projekt? | **Ja** (shared Registry, einfacher) | ✅ Entschieden |
| O2 | Cluster-Name | **`vob-prod`** | ✅ Entschieden |
| O3 | Auth bei erstem Deploy | **Basic temporaer** (Entra ID blockiert) | ✅ Entschieden |
| O4 | K8s API ACL | **Eingeschraenkt** (BSI APP.4.4.A7) | ✅ Entschieden |
| O5 | SEC-06 Phase 2 Zeitpunkt | **Vor erstem Deploy** (BSI SYS.1.6.A10) | ✅ Entschieden |
| O6 | Eigener Teams-Kanal fuer PROD | **Ja** (ITIL Incident Management) | ✅ Entschieden |
| O7 | Default LLM-Modell | VoEB-Praeferenz | ⏳ Offen (VoEB) |
| O8 | Maintenance-Window PROD | **So 03:00-05:00 UTC** | ✅ Entschieden |
| O9 | Datenquellen / Connectors fuer PROD | — | ⏳ Offen (VoEB) |
| O10 | Token-/Request-Limits fuer PROD | — | ⏳ Offen (VoEB) |

---

## 11. PROD Resource Budget (berechnet 2026-03-11)

Exakte Berechnung basierend auf `values-prod.yaml` (nach allen Korrekturen):

### 11.1 Onyx-Pods (Namespace `onyx-prod`)

| Komponente | Replicas | CPU Request | CPU Limit | RAM Request | RAM Limit |
|------------|----------|-------------|-----------|-------------|-----------|
| API Server | 2 | 1000m | 2000m | 1024 Mi | 4096 Mi |
| Web Server | 2 | 500m | 1000m | 512 Mi | 2048 Mi |
| Celery Beat | 1 | 250m | 500m | 512 Mi | 1024 Mi |
| Celery Primary | 2 | 1000m | 2000m | 2048 Mi | 4096 Mi |
| Celery Light | 1 | 500m | 1000m | 1024 Mi | 2048 Mi |
| Celery Heavy | 1 | 500m | 1000m | 1024 Mi | 2048 Mi |
| Celery DocFetching | 1 | 500m | 1000m | 1024 Mi | 4096 Mi |
| Celery DocProcessing | 1 | 500m | 1000m | 1024 Mi | 4096 Mi |
| Celery Monitoring | 1 | 250m | 500m | 256 Mi | 512 Mi |
| Celery UserFile | 1 | 500m | 1000m | 512 Mi | 2048 Mi |
| Vespa | 1 | 2000m | 4000m | 4096 Mi | 8192 Mi |
| Redis | 1 | 250m | 500m | 512 Mi | 1024 Mi |
| Inference Model | 1 | 500m | 2000m | 1024 Mi | 4096 Mi |
| Index Model | 1 | 500m | 2000m | 1024 Mi | 4096 Mi |
| **Summe onyx-prod** | **17** | **8750m** | **19500m** | **15616 Mi (~15.25 Gi)** | **43520 Mi (~42.5 Gi)** |

### 11.2 Monitoring-Pods (Namespace `monitoring`)

| Komponente | CPU Request | RAM Request |
|------------|-------------|-------------|
| Prometheus | 500m | 1024 Mi |
| Grafana | 100m | 256 Mi |
| AlertManager | 100m | 128 Mi |
| kube-state-metrics | 100m | 128 Mi |
| node-exporter (×2) | 200m | 256 Mi |
| prometheus-operator | 100m | 128 Mi |
| postgres-exporter | 50m | 64 Mi |
| redis-exporter | 25m | 32 Mi |
| **Summe monitoring** | **1175m** | **~2 Gi** |

### 11.3 Gesamt-Auslastung

| | CPU Requests | RAM Requests | CPU Limits | RAM Limits |
|---|---|---|---|---|
| onyx-prod (17 Pods) | 8750m | ~15.25 Gi | 19500m | ~42.5 Gi |
| monitoring (~9 Pods) | 1175m | ~2 Gi | ~2450m | ~4 Gi |
| System (kube-system) | ~500m | ~1 Gi | ~800m | ~2 Gi |
| **Gesamt** | **10425m** | **~18.25 Gi** | **22750m** | **~48.5 Gi** |
| **Allocatable (2× g1a.8d)** | 15820m | 56.6 Gi | 15820m | 56.6 Gi |
| **Auslastung** | **66%** | **32%** | **144%** | **86%** |

**Bewertung:**
- **CPU Requests 66%:** Komfortabel. Genug Headroom fuer Burst und temporaere Debug-Pods.
- **RAM Requests 32%:** Sehr komfortabel. Genug Reserve fuer Wachstum.
- **CPU Limits 144%:** Uebercommitted (normal bei Burstable QoS). Nur problematisch wenn ALLE Pods gleichzeitig am CPU-Limit laufen (praktisch nie).
- **RAM Limits 86%:** Akzeptabel. Bei extremer Last (alle Pods am Memory-Limit) waere der Cluster voll. In der Praxis nutzen Pods 30-50% ihres Limits (gemessen auf DEV/TEST, monitoring-konzept.md Lesson Learned).
- **Skalierung:** Bei Bedarf 3. Node hinzufuegen (g1a.8d). Dann: CPU 44%, RAM 21% (entspannt).

### 11.4 ResourceQuota (Namespace `onyx-prod`)

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: onyx-prod-quota
  namespace: onyx-prod
spec:
  hard:
    requests.cpu: "12"       # 8.75 benoetigte Requests + 37% Buffer
    requests.memory: "20Gi"  # 15.25 Gi benoetigte Requests + 31% Buffer
    limits.cpu: "22"         # 19.5 benoetigte Limits + 13% Buffer
    limits.memory: "48Gi"    # 42.5 Gi benoetigte Limits + 13% Buffer
```

---

## 12. Referenzen

| Dokument | Pfad |
|----------|------|
| ADR-004: Umgebungstrennung | `docs/adr/adr-004-umgebungstrennung-dev-test-prod.md` |
| ADR-005: Node-Upgrade | `docs/adr/adr-005-node-upgrade-g1a8d.md` |
| StackIT Infrastruktur | `docs/referenz/stackit-infrastruktur.md` |
| DNS/TLS Runbook | `docs/runbooks/dns-tls-setup.md` |
| Monitoring-Konzept | `docs/referenz/monitoring-konzept.md` |
| Helm Values PROD | `deployment/helm/values/values-prod.yaml` |
| Helm Values Common | `deployment/helm/values/values-common.yaml` |
| Terraform Modul | `deployment/terraform/modules/stackit/` |
| CI/CD Workflow | `.github/workflows/stackit-deploy.yml` |
| Entra ID Anleitung | `docs/referenz/anleitung-entra-id-app-registration.docx` |
| Sicherheitskonzept | `docs/sicherheitskonzept.md` |
| Betriebskonzept | `docs/betriebskonzept.md` |
| Monitoring-Exporter Spec | `docs/technisches-feinkonzept/monitoring-exporter.md` |
| PG Exporter PROD | `deployment/k8s/monitoring-exporters/pg-exporter-prod.yaml` |
| Redis Exporter PROD | `deployment/k8s/monitoring-exporters/redis-exporter-prod.yaml` |
