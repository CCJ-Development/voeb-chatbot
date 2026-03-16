# Backup & Recovery Konzept

## VÖB Chatbot

| Version | Datum | Autor | Aenderung |
|---------|-------|-------|-----------|
| 0.1 | 2026-03-15 | COFFEESTUDIOS | Erstversion — basierend auf Kickoff-Anforderungen, StackIT Service Certificate V1.1, IST-Analyse |

**Normativer Rahmen:** BSI CON.3 (Datensicherungskonzept), DSGVO Art. 32 (Sicherheit der Verarbeitung), ISO/IEC 27001 A.12.3 (Backup)

**Referenzen:**
- Kickoff-Meeting-Notizen: `docs/referenz/kickoff-meeting-notizen.md`
- StackIT Service Certificate V1.1: [PDF (EN)](https://www.stackit.de/wp-content/uploads/2025/09/V1.1_PostgreSQL-Flex_EN-valid-from-12.09.2025.pdf)
- StackIT-Backup-Recherche: `audit-output/stackit-backup-recherche.md`
- Betriebskonzept: `docs/betriebskonzept.md`
- Sicherheitskonzept: `docs/sicherheitskonzept.md`

---

## 1. Geltungsbereich

Dieses Konzept deckt alle persistenten Datenbestaende des VÖB Chatbot-Systems ab, die auf StackIT-Infrastruktur betrieben werden:

- **PostgreSQL-Datenbanken** (DEV, TEST, PROD) — StackIT Managed PG Flex
- **Object Storage Buckets** (vob-dev, vob-test, vob-prod) — StackIT Object Storage (S3-kompatibel)
- **Vespa-Indizes** (Embedding-Vektoren) — In-Cluster PersistentVolumes
- **Kubernetes-Konfiguration** — Helm Values, Secrets, Manifeste
- **Applikations-Code und IaC** — Git Repository (GitHub)
- **Monitoring-Daten** — Prometheus PersistentVolumes

**Nicht im Scope:**
- Microsoft Entra ID (externer Identity Provider, von VÖB verwaltet)
- StackIT Control Plane / etcd (von StackIT verwaltet, Vollbackup 24h + Delta 5min)
- LLM-Modelle (StackIT AI Model Serving, kein eigener State)
- Redis (Cache + Celery Broker, by-design ephemeral, kein Datenverlust-Impact)

---

## 2. Datenkategorien & Kritikalitaet

| Datenkategorie | Speicherort | Kritikalitaet | Personenbezug (DSGVO) | Backup-Anforderung | Retention |
|----------------|-------------|---------------|------------------------|---------------------|-----------|
| Chat-Verlaeufe | PostgreSQL | **Hoch** | Ja (Benutzer-ID, Inhalte) | Taegliches Backup + PITR (PROD) | 6 Monate (Kickoff-Beschluss), danach Auto-Purge |
| User-Accounts / Auth-Daten | PostgreSQL | **Hoch** | Ja (E-Mail, Name) | Taegliches Backup + PITR (PROD) | Solange Account aktiv |
| Token-Usage-Daten (ext-token) | PostgreSQL | Mittel | Ja (User-ID → E-Mail) | Taegliches Backup | 12 Monate (Abrechnung) |
| Custom System Prompts (ext-prompts) | PostgreSQL | Mittel | Nein | Taegliches Backup | Unbegrenzt (manuelles Loeschen) |
| Branding-Konfiguration (ext-branding) | PostgreSQL | Niedrig | Nein | Taegliches Backup | Unbegrenzt |
| Agent-Templates / Knowledge-Dokumente | PostgreSQL + Object Storage | **Hoch** | Ggf. (hochgeladene Dokumente) | Taegliches Backup | Bis manuelles Loeschen (Kickoff-Beschluss: persistent, nicht durch Chat-Retention betroffen) |
| Dokument-Embeddings (Vespa-Index) | PersistentVolume (in-cluster) | Mittel | Nein (nur Vektoren) | **Kein separates Backup** — Re-Indexierung aus Quelldaten moeglich | n/a |
| Helm Values / K8s Manifeste | Git (GitHub) | **Hoch** | Nein | Git = Backup | Unbegrenzt (Git History) |
| Terraform State | Lokal (.tfstate) | **Hoch** | Nein | Lokale Kopie (.tfstate.backup) | Unbegrenzt (lokal) |
| Secrets (DB-Passwoerter, API Keys) | GitHub Environments + K8s Secrets | **Hoch** | Nein (technisch) | GitHub = Backup fuer CI/CD, K8s Secrets bei Cluster-Neuaufbau manuell | n/a |
| Monitoring-Daten (Metriken) | Prometheus PV | Niedrig | Ggf. (IPs in Metriken) | **Kein separates Backup** | DEV/TEST: 30d, PROD: 90d (Helm konfiguriert) |
| Logdateien | Pod stdout/stderr | Niedrig | Ggf. (IPs, User-Aktionen) | **Kein Backup** — Logs gehen bei Pod-Restart verloren | Nur Laufzeit des Pods |

---

## 3. Backup-Strategie pro Umgebung

### 3.1 PROD (Produktionsumgebung)

| Komponente | Backup-Methode | Schedule | Retention | PITR | Verantwortlich |
|------------|----------------|----------|-----------|------|----------------|
| PostgreSQL (Flex 4.8 HA, 3-Node) | StackIT Managed Backup + WAL-Archivierung | `0 1 * * *` (01:00 UTC taeglich) | 30 Tage | **Ja** — sekundengenau | StackIT (Ausfuehrung), CCJ (Restore-Initiation) |
| Object Storage (vob-prod) | StackIT Managed Replikation (3 AZs) | Kontinuierlich | Unbegrenzt (Objekte bleiben bis Loeschung) | Nein | StackIT |
| Vespa-Index | **Kein Backup** — Re-Indexierung aus Quelldaten | n/a | n/a | n/a | CCJ |
| Helm Release History | Helm-intern (5 Revisionen) | Bei jedem Deploy | 5 Revisionen | n/a | CI/CD |
| Applikations-Code | Git (GitHub) | Bei jedem Push | Unbegrenzt | n/a | CCJ |
| Terraform State | Lokale Datei + .tfstate.backup | Bei jedem `terraform apply` | Unbegrenzt (lokal) | n/a | CCJ |
| Prometheus Metriken | PersistentVolume (50 Gi) | Kontinuierlich | 90 Tage / 40 GB | n/a | Helm-konfiguriert |

**PROD HA-Architektur (Verfuegbarkeitsschutz):**
- 3-Node PG Flex Cluster: Synchrone Replikation, automatisches Failover < 60 Sekunden (Patroni-basiert)
- 2x API Server Replicas, 2x Web Server Replicas
- `prevent_destroy = true` in Terraform (schuetzt vor versehentlicher Instanz-Loeschung)

### 3.2 TEST und DEV

**DEV und TEST werden abgeschaltet** (Kostenoptimierung). Backups fuer diese Umgebungen sind nicht erforderlich.

Solange die Instanzen existieren, laufen StackIT Managed Backups automatisch (DEV 02:00 UTC, TEST 03:00 UTC, 30 Tage Retention). Nach Abschaltung der PG-Instanzen sind die Backups nicht mehr verfuegbar (instanzgebunden).

**PITR auf Flex 2.4 Single:** Funktioniert (verifiziert im Restore-Test 2026-03-15 auf DEV).

---

## 4. StackIT Managed PostgreSQL — Backup-Details

### 4.1 Service Certificate V1.1 (gueltig ab 12.09.2025)

| Parameter | Wert |
|-----------|------|
| **RPO (vertraglich)** | 4 Stunden |
| **RTO (vertraglich)** | 4 Stunden (fuer DB < 500 GB) |
| **Retention** | 30 Tage (Default) |
| **Backup-Typ** | WAL-basiert (kontinuierlich) + taeglicher Snapshot (Cron-konfigurierbar) |
| **PITR** | Ja — sekundengenau innerhalb des Retention-Fensters |
| **Restore-Methode** | **Clone** (neue Instanz zum gewaehlten Zeitpunkt, KEIN In-Place Restore) |
| **Verschluesselung** | TLS 1.3 (Transit), AES-256 at Rest (wahrscheinlich, analog Object Storage) |
| **HA Failover** | < 60 Sekunden (Patroni, synchrone Replikation, 3 Replicas) |
| **Verfuegbarkeits-SLA** | 99.95% (Maintenance ausgenommen) |
| **Backup-Kosten** | Separat abgerechnet (pro GB/Stunde) |
| **Backup-Monitoring** | **Kundenverantwortung** |
| **Max. Storage** | 4 TB |
| **Soft-Delete geloeschter Instanzen** | 5 Tage (Restore per Clone moeglich) |

### 4.2 Kritische Betriebshinweise

1. **Kein In-Place Restore:** Restore erstellt immer eine neue (geklonte) Instanz. Die Applikation muss auf die neue Instanz umgestellt werden (Connection-String-Aenderung in K8s Secrets, Helm Re-Deploy).

2. **Backups sind instanzgebunden:** Bei Loeschung der PG-Instanz (z.B. versehentlicher `terraform destroy`) sind ALLE Backups unwiederbringlich verloren. `prevent_destroy = true` ist konfiguriert, aber bei manueller Override kein Schutz.

3. **Backup-Monitoring ist Kundenverantwortung:** StackIT bietet keine Alerts bei Backup-Fehlern. Wir muessen ueber Prometheus/Grafana selbst sicherstellen, dass Backups laufen.

4. **PITR fuer DEV/TEST (Flex 2.4 Single):** Unklar ob PITR bei Single-Instanzen verfuegbar ist. Fuer DEV/TEST nicht kritisch, aber fuer Vollstaendigkeit zu klaeren.

### 4.3 Aktuelle Backup-Schedules (Terraform-konfiguriert)

| Umgebung | Cron | Uhrzeit (UTC) | Terraform-Datei |
|----------|------|---------------|-----------------|
| DEV | `0 2 * * *` | 02:00 | `deployment/terraform/environments/dev/main.tf:46` |
| TEST | `0 3 * * *` | 03:00 | `deployment/terraform/environments/test/main.tf:28` |
| PROD | `0 1 * * *` | 01:00 | `deployment/terraform/environments/prod/main.tf:58` |

**Keine Ueberlappung** mit K8s Maintenance Windows (DEV/TEST: 02:00-04:00 UTC, PROD: 03:00-05:00 UTC). PROD-Backup laeuft 2 Stunden vor dem K8s Maintenance Window.

---

## 5. Zusaetzliche Backup-Massnahmen

### 5.1 Abgedeckt (bereits implementiert)

| Massnahme | Status | Details |
|-----------|--------|---------|
| PG Managed Backups (DEV/TEST/PROD) | ✅ Aktiv | Terraform-konfiguriert, alle 3 Environments |
| PG HA (PROD) | ✅ Aktiv | 3-Node Cluster, synchrone Replikation, <60s Failover |
| PG Lifecycle Protection | ✅ Aktiv | `prevent_destroy = true` in Terraform |
| Object Storage Replikation | ✅ Aktiv | StackIT Managed, 3 AZs, 11-Nines Durability |
| Object Storage Encryption at Rest | ✅ Aktiv | AES-256, SSE-C unterstuetzt |
| Git als Code-/Config-Backup | ✅ Aktiv | GitHub Repository, vollstaendige History |
| Helm Release History | ✅ Aktiv | 5 Revisionen (CI/CD `--history-max 5`) |
| K8s etcd Backup | ✅ Aktiv | StackIT Managed (24h Full + 5min Delta) |

### 5.2 Teilweise abgedeckt

| Massnahme | Status | Luecke |
|-----------|--------|--------|
| Terraform State Backup | ⚠️ Teilweise | Nur lokale Kopie (.tfstate.backup). Kein Remote-Backend, kein Offsite-Backup. Akzeptiertes Risiko (SEC-04, P3). |
| Object Storage Versionierung | ⚠️ Teilweise | Terraform-Ressource setzt nur `project_id` + `name`. Versionierung ist als Feature unterstuetzt, aber **NICHT explizit aktiviert** in Terraform. Audit-Finding H3 offen. |
| Secrets-Backup | ⚠️ Teilweise | GitHub Environments fuer CI/CD, aber K8s Secrets nicht extern gesichert. Bei Cluster-Verlust: manuelles Wiederherstellen aus Terraform Outputs + GitHub Secrets. |

### 5.3 NICHT abgedeckt (Luecken)

| Massnahme | Risiko | Empfehlung |
|-----------|--------|------------|
| **Vespa-Index Backup** | Mittel — Re-Indexierung moeglich, dauert aber Stunden bei grossen Datenbestaenden | Fuer V1.0 akzeptiert. Spaeter: Velero fuer PV-Snapshots evaluieren |
| **Backup-Monitoring / Alerting** | **Hoch** — Backup-Fehler werden nicht bemerkt | Alert-Rule in Prometheus: PG-Metriken auf letzte Backup-Zeit pruefen (falls StackIT-Metrik verfuegbar) |
| **Backup-Restore-Tests** | **Hoch** — Restore nie getestet, Audit M7 offen | Quartalmaessige Restore-Tests einfuehren (siehe Abschnitt 9) |
| **Cross-Instance PG Backup** | Mittel — Bei Instanz-Loeschung alle Backups verloren | Periodischer `pg_dump` als Fallback in Object Storage (z.B. monatlich per CronJob) |
| **Prometheus-Daten Backup** | Niedrig — Metriken sind operativ, nicht geschaeftskritisch | Kein Backup geplant. Daten gehen bei PV-Verlust verloren. |
| **Zentralisiertes Logging** | Niedrig — Logs gehen bei Pod-Restart verloren | Log-Aggregation (z.B. Loki) ist Nice-to-Have, nicht V1.0-Scope |

---

## 6. Recovery-Verfahren

### 6.1 Datenbank-Restore (PostgreSQL)

**Wer darf einen Restore ausloesen?** Tech Lead (CCJ) oder designierte Support-Person pro Umgebung (Kickoff-Beschluss).

**PROD-Restore-Verfahren (Self-Service per StackIT Clone):**

1. **Entscheidung:** Zeitpunkt fuer Restore festlegen (Sekunde genau moeglich dank PITR)
2. **Clone erstellen:**
   - StackIT Portal → PostgreSQL Flex → PROD-Instanz → Clone
   - Zeitpunkt waehlen (innerhalb der letzten 30 Tage)
   - Clone wird als neue Instanz provisioniert
3. **Clone validieren:**
   ```bash
   # Temporaerer Pod zum Pruefen des Clones
   kubectl run pg-verify --restart=Never --namespace onyx-prod \
     --image=postgres:16-alpine \
     --env="PGPASSWORD=<CLONE_PASSWORD>" \
     --command -- psql -h <CLONE_HOST> -p 5432 -U onyx_app -d onyx \
     -c "SELECT count(*) FROM chat_message; SELECT max(time_sent) FROM chat_message;"
   sleep 10 && kubectl logs pg-verify -n onyx-prod
   kubectl delete pod pg-verify -n onyx-prod
   ```
4. **Applikation umstellen:**
   - Connection-String in `values-prod-secrets.yaml` auf Clone-Instanz aendern
   - `helm upgrade` ausfuehren (oder CI/CD Re-Deploy)
   - Alternativ: K8s Secret direkt patchen + Pods neustarten
5. **Validierung:** Health Check, funktionale Pruefung (Chat senden, History pruefen)
6. **Alte Instanz:** Erst nach erfolgreicher Validierung + Beobachtungszeitraum (24h) loeschen
7. **Terraform-State aktualisieren:** `terraform import` fuer neue Instanz oder Terraform-Konfiguration anpassen

**Geschaetzte Dauer:** Clone-Erstellung ~30 Min (DB < 500 GB → RTO < 4h), Umstellung + Validierung ~30 Min. **Gesamt: 1-2 Stunden** (PROD < 1 GB aktuell).

**DEV/TEST-Restore:** Analog, aber weniger formell. Kein Beobachtungszeitraum noetig.

**Letzter Ausweg (wenn Clone nicht moeglich):**
1. StackIT Support kontaktieren
2. PITR oder letztes Backup anfordern
3. **Achtung:** Alle Daten nach dem Backup-Zeitpunkt gehen verloren

### 6.2 Kompletter Cluster-Neuaufbau

Falls der gesamte K8s-Cluster verloren geht:

1. **Terraform:** `terraform apply` fuer SKE Cluster + PG Flex + Object Storage (ca. 10-15 Min)
2. **K8s Setup:** Namespace, Secrets, cert-manager, Redis Operator (Runbook: `docs/runbooks/stackit-projekt-setup.md`)
3. **PG Restore:** Clone von letztem Backup (siehe 6.1) ODER Datenbank neu anlegen (Runbook: `docs/runbooks/stackit-postgresql.md`)
4. **Helm Deploy:** `helm install` mit values-Dateien (Runbook: `docs/runbooks/helm-deploy.md`)
5. **Monitoring:** kube-prometheus-stack deployen (values-monitoring-prod.yaml)
6. **DNS/TLS:** cert-manager ClusterIssuers + Ingress (Runbook: `docs/runbooks/dns-tls-setup.md`)
7. **Validierung:** Health Check, funktionale Pruefung

**Geschaetzte Dauer:** 2-4 Stunden (abhaengig von Terraform/StackIT API Responsiveness)

**Voraussetzungen fuer Cluster-Neuaufbau:**
- Terraform State vorhanden (lokal) ODER StackIT-Ressourcen manuell identifizierbar
- GitHub Secrets intakt (PG-Passwoerter, S3-Credentials, Registry-Credentials)
- Git Repository verfuegbar (Code + Helm Values + Terraform Config)

### 6.3 Einzelne Komponenten wiederherstellen

| Komponente | Verfahren | Dauer | Runbook |
|------------|-----------|-------|---------|
| **Einzelner Pod** | K8s Restart (automatisch) oder `kubectl delete pod` | 1-2 Min | n/a |
| **Deployment-Fehler** | `helm rollback onyx-{env} [REVISION]` | ~5 Min | `docs/runbooks/rollback-verfahren.md` |
| **Alembic-Migration-Fehler** | `alembic downgrade -1` | ~2 Min | `docs/runbooks/rollback-verfahren.md` |
| **Vespa-Index** | Re-Indexierung ueber Connector-Sync triggern | Stunden | Onyx Admin UI |
| **Object Storage Datei** | Version Recovery (wenn Versionierung aktiviert) | Minuten | StackIT Portal |
| **Secrets verloren** | Aus Terraform Output + GitHub Environments rekonstruieren | ~30 Min | Manuell |
| **Monitoring-Stack** | `helm upgrade monitoring` mit values-Datei | ~10 Min | `docs/referenz/monitoring-konzept.md` |

---

## 7. RPO & RTO

### 7.1 StackIT-Garantien (Service Certificate V1.1)

| Parameter | Wert | Bedingung |
|-----------|------|-----------|
| RPO (vertraglich) | 4 Stunden | StackIT PG Flex Garantie |
| RTO (vertraglich) | 4 Stunden | Fuer DB < 500 GB |
| RPO (praktisch, mit PITR) | ~0 (sekundengenau) | Innerhalb Retention-Fenster (30 Tage) |
| Verfuegbarkeits-SLA | 99.95% | Maintenance ausgenommen |

### 7.2 Projektziele (Vereinbarung mit VÖB)

| Umgebung | RPO (max. Datenverlust) | RTO (max. Ausfallzeit) | Status |
|----------|-------------------------|------------------------|--------|
| PROD | 24 Stunden (Kickoff-Vereinbarung, erster Monat Beobachtung) | **[AUSSTEHEND — Klaerung mit VÖB]** | RPO vereinbart, RTO offen |
| TEST | 24 Stunden | Keine Anforderung | Akzeptiert |
| DEV | 24 Stunden | Keine Anforderung | Akzeptiert |

**Kickoff-Kontext (Zeitstempel 00:30:24-00:31:33):**
- Initial-Vorschlag: 24-Stunden Backup-Frequenz fuer TEST und PROD
- Referenz VÖB-intern: 1-Stunden-Frequenz mit 30 Tagen Retention
- Beschluss: "Erstmal einen Monat durchlaufen lassen", dann Frequenz ggf. anpassen
- Backup-Retention: 30 Tage (StackIT Default)

**Bewertung:** Der vereinbarte 24h-RPO liegt deutlich ueber dem StackIT-garantierten 4h-RPO und dem durch PITR technisch moeglichen ~0-RPO. Die aktuelle Konfiguration (taegliches Backup + PITR) erfuellt die Anforderung komfortabel.

### 7.3 Szenario-basierte RTO-Schaetzung

| Szenario | Geschaetzte RTO | RPO | Anmerkung |
|----------|-----------------|-----|-----------|
| Einzelner Pod Ausfall | 1-2 Min | 0 | K8s Auto-Restart |
| API-Server Ausfall (PROD, 2 Replicas) | 0 (kein Ausfall) | 0 | HA: zweite Replica uebernimmt |
| Helm Rollback | ~5 Min | 0 | Code-/Config-Rollback, keine Daten betroffen |
| PG Failover (PROD HA) | < 60 Sek | 0 | Patroni automatisches Failover |
| PG Restore aus Clone | 1-2 Stunden | Sekundengenau (PITR) | Clone-Erstellung + Umstellung |
| Cluster-Neuaufbau | 2-4 Stunden | Bis letztes PG-Backup | Terraform + Helm + PG Restore |
| Vespa Re-Indexierung | 2-8 Stunden (schaetzung) | Embeddings verloren, Quelldaten intakt | Abhaengig von Dokumentenmenge |

---

## 8. Backup-Monitoring & Alerting

### 8.1 Herausforderung

StackIT exponiert **keine Prometheus-Metriken fuer Backup-Status**. Die 15 verfuegbaren PG-Metriken (pg_up, pg_stat_database_*, etc.) enthalten keine Backup-Informationen. "Monitoring of [...] backup plans are the responsibility of the customer" (Service Certificate V1.1).

**Loesung:** CronJob der die StackIT REST API pollt + Alert-Rules auf CronJob-Failures.

### 8.2 Implementierung (PROD)

| Komponente | Details |
|------------|---------|
| **CronJob** | `pg-backup-check` in Namespace `monitoring`, alle 4 Stunden |
| **API** | `GET /v2/projects/{projectId}/regions/eu01/instances/{instanceId}/backups` |
| **Auth** | StackIT Service Account Key (JWT → Token Exchange) |
| **Pruefung** | Letztes Backup: EndTime < 26h + kein Error-Feld |
| **Bei Fehler** | CronJob Exit 1 → kube-state-metrics → Alert |
| **NetworkPolicy** | `09-allow-backup-check-egress.yaml` (HTTPS Egress fuer API-Zugriff) |
| **Manifest** | `deployment/k8s/monitoring-exporters/pg-backup-check-prod.yaml` |

### 8.3 Alert-Rules (PROD)

| # | Alert | Metrik | Schwellwert | Severity | Beschreibung |
|---|-------|--------|-------------|----------|-------------|
| 21 | `PGBackupCheckFailed` | `kube_job_status_failed{job_name=~"pg-backup-check-.*"}` | > 0, for 5m | **critical** | CronJob fehlgeschlagen (Backup zu alt, API-Fehler, Auth-Fehler) |
| 22 | `PGBackupCheckNotScheduled` | `time() - kube_cronjob_status_last_schedule_time{cronjob="pg-backup-check"}` | > 21600 (6h), for 30m | warning | CronJob nicht gelaufen |

**Konfiguriert in:** `deployment/helm/values/values-monitoring-prod.yaml` (additionalPrometheusRulesMap)

**Routing:** Alle Alerts → Teams PROD-Kanal (`teams-prod` Receiver, `[PROD]`-Prefix). Critical alerts: repeat_interval 1h.

### 8.4 Setup-Anleitung

**Status:** LIVE auf PROD seit 2026-03-16. Erster manueller Test erfolgreich (PROD Backup von 01:00 UTC, 3.2 MB, kein Fehler).

```bash
# 1. SA Key vorbereiten
#    Die SA Key JSON-Datei (z.B. voeb-terraform-credentials.json) enthaelt
#    die Private Key EMBEDDED im Feld "credentials.privateKey".
#    Diese muss als separate PEM-Datei extrahiert werden:
python3 -c "
import json
with open('sa-key.json') as f:
    data = json.load(f)
with open('private-key.pem', 'w') as f:
    f.write(data['credentials']['privateKey'])
"

# 2. PG Instance ID ermitteln (aus PG-Host-Prefix oder Terraform)
#    PROD: fdc7610c-91dc-4d0a-9652-adafe1a509cd
#    DEV:  be7fe911-4eac-4c9d-a7a8-6dfff674c41f

# 3. K8s Secret erstellen
KUBECONFIG=~/.kube/config-prod kubectl create secret generic stackit-backup-check -n monitoring \
  --from-file=sa-key.json=<pfad/zu/sa-key.json> \
  --from-file=private-key.pem=<pfad/zu/extrahierte-private-key.pem> \
  --from-literal=PROJECT_ID=b3d2a04e-46de-48bc-abc6-c4dfab38c2cd \
  --from-literal=PG_INSTANCE_ID=fdc7610c-91dc-4d0a-9652-adafe1a509cd

# 4. NetworkPolicy deployen
kubectl apply -f deployment/k8s/network-policies/monitoring/09-allow-backup-check-egress.yaml

# 5. CronJob deployen
kubectl apply -f deployment/k8s/monitoring-exporters/pg-backup-check-prod.yaml

# 6. Helm upgrade (fuer Alert-Rules)
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring -f deployment/helm/values/values-monitoring-prod.yaml

# 7. Verifizierung
kubectl get cronjob pg-backup-check -n monitoring
kubectl create job --from=cronjob/pg-backup-check pg-backup-check-manual -n monitoring
kubectl logs -n monitoring job/pg-backup-check-manual -f
```

### 8.5 Noch fehlend (Nice-to-Have)

| Alert | Beschreibung | Prioritaet |
|-------|-------------|------------|
| `PGReplicationLag` | Alarm wenn Replikations-Lag > 60 Sekunden (PROD HA) | MITTEL — Metrik moeglicherweise nicht verfuegbar |
| `PGStorageNearFull` | Alarm wenn PG Storage > 80% belegt | MITTEL — `pg_database_size_bytes` ist verfuegbar, aber Storage-Limit nicht |

---

## 9. Test-Restores

### 9.1 Frequenz

| Umgebung | Test-Frequenz | Verantwortlich |
|----------|---------------|----------------|
| PROD | **Quartalsweise** (alle 3 Monate) | Tech Lead (CCJ) |
| TEST | Bei Bedarf / nach Upstream-Merges | Tech Lead (CCJ) |
| DEV | Nicht geplant | n/a |

### 9.2 Test-Restore-Verfahren (PROD)

1. Clone-Instanz erstellen (Zeitpunkt: 24h zurueck)
2. Daten auf Clone validieren:
   - Tabellen vorhanden (`\dt`)
   - Datenzaehlung (Chat Messages, Users, Token Usage)
   - Letzter Datensatz-Timestamp pruefen
3. Applikation testweise gegen Clone starten (separater Namespace oder Port-Forward)
4. Ergebnis dokumentieren in `docs/abnahme/` (Datum, Dauer, Ergebnis, Anomalien)
5. Clone-Instanz loeschen
6. **DSGVO-Hinweis:** Bei Restore muessen zwischenzeitlich geloeschte Daten erneut geloescht werden (EDSA Feb 2026 Richtlinie)

### 9.3 Durchgefuehrte Restore-Tests

| Datum | Umgebung | Ergebnis | Technische RTO | Operative RTO | Protokoll |
|-------|----------|----------|----------------|---------------|-----------|
| 2026-03-15 | DEV | ✅ ERFOLGREICH (100% Datenintegritaet) | 3 Min 16 Sek | 7 Min 15 Sek | `docs/abnahme/restore-test-protokoll-2026-03-15.md` |

**Naechster geplanter Test:** 2026-06-15 (quartalsmaessig)

**Erkenntnisse aus erstem Test (2026-03-15):**
- Clone-Erstellung dauerte 3:16 (17 MB DB) — weit unter StackIT RTO von 4h
- Passwort-Reset nach Clone noetig (Passwoerter werden NICHT uebernommen)
- ACL wird automatisch vom Original uebernommen
- `stackit` CLI v0.53.1 hat Bug beim Clone-Tracking (404), Clone wird trotzdem erstellt
- Audit-Finding M7: **GESCHLOSSEN**

---

## 10. Offene Punkte

| Nr. | Thema | Prioritaet | Klaerung mit | Status |
|-----|-------|------------|-------------|--------|
| B1 | RTO fuer PROD offiziell mit VÖB vereinbaren | **HOCH** | VÖB | AUSSTEHEND |
| B2 | Object Storage Versionierung in Terraform aktivieren (Audit H3) | MITTEL | CCJ (Terraform) | AUSSTEHEND |
| B3 | Backup-Monitoring Alert implementieren (PGBackupAge) | **HOCH** | CCJ (Prometheus) + StackIT (Metrik-Verfuegbarkeit) | AUSSTEHEND |
| B4 | Erster Restore-Test durchfuehren und dokumentieren (Audit M7) | **HOCH** | CCJ | AUSSTEHEND |
| B5 | PITR-Verfuegbarkeit fuer Flex 2.4 Single (DEV/TEST) klaeren | NIEDRIG | StackIT Support (S6) | AUSSTEHEND |
| B6 | Periodischer `pg_dump` als Cross-Instance-Fallback evaluieren | MITTEL | CCJ | AUSSTEHEND |
| B7 | Velero fuer PV-Snapshots (Vespa) evaluieren | NIEDRIG | CCJ | Geplant fuer spaeter |
| B8 | Backup-Kosten in Kostenaufstellung aufnehmen | NIEDRIG | CCJ | AUSSTEHEND |

---

## 11. Widersprueche in bestehender Dokumentation (bereinigt)

Bei der Erstellung dieses Konzepts wurden folgende Widersprueche identifiziert:

| Dokument | Aussage | Korrektur |
|----------|---------|-----------|
| `docs/sicherheitskonzept.md` (Zeile 348) | "PROD: Maintenance-Window 03:00-05:00 UTC" als Backup-Schedule | **Falsch.** 03:00-05:00 UTC ist das K8s Maintenance Window, NICHT der PG Backup-Schedule. PROD PG Backup laeuft um **01:00 UTC** (Terraform autoritativ). |
| `docs/referenz/stackit-infrastruktur.md` (Zeile 144) | "DEV/TEST: PG PITR (auto)" | **Unklar.** PITR-Verfuegbarkeit fuer Flex 2.4 Single nicht bestaetigt. Betriebskonzept sagt korrekt "abhaengig vom StackIT Flex Tier". |
| `docs/referenz/stackit-infrastruktur.md` (Zeile 71) | "PROD Backups: PG PITR + Object Store Versioning" | **Teilweise falsch.** Object Storage Versionierung ist als Feature unterstuetzt, aber NICHT in Terraform aktiviert (Audit H3 offen). |
| `docs/runbooks/rollback-verfahren.md` (Zeile 123) | "StackIT Support kontaktieren" fuer Restore | **Veraltet.** StackIT bietet Self-Service Restore per Clone-Funktion. Support-Kontakt nur als letzter Ausweg. |
| `docs/referenz/technische-parameter.md` (Zeile 307) | "PROD: StackIT Managed" ohne explizite Uhrzeit | **Unvollstaendig.** PROD Backup laeuft um 01:00 UTC (Terraform: `0 1 * * *`). |

**Hinweis:** Die Korrekturen werden in den jeweiligen Dokumenten vorgenommen (siehe Phase 4b der Backup-Analyse).
