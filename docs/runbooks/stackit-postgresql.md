# Runbook: StackIT PostgreSQL Flex — Betriebswissen

**Zuletzt verifiziert:** 2026-02-27 (DEV/TEST). PROD-Abschnitt ergaenzt 2026-03-15.
**Ausgeführt von:** Nikolaj Ivanov

---

## Zweck

**Wann dieses Runbook verwenden:**
- Neue Datenbank auf einer StackIT PG Flex Instanz anlegen
- PG-Verbindungsprobleme debuggen (ACL, Credentials, Rollen)

**Zielgruppe:** DevOps / Tech Lead

**Voraussetzungen:**
- PG Flex Instanz provisioniert (Terraform apply)
- User-Credentials aus `terraform output`
- `kubectl` Zugriff auf den Cluster (fuer temporaeren Pod)

**Geschaetzte Dauer:** 10-20 Min

---

## Kontext

StackIT PostgreSQL Flex ist ein Managed Database Service. Im Vergleich zu selbst betriebenen PostgreSQL-Instanzen gibt es wichtige Unterschiede die beim Betrieb beachtet werden müssen.

---

## Datenbank anlegen

Terraform erstellt die PG-Instanz und den Applikations-User, aber NICHT die Datenbank selbst. Die Datenbank muss manuell angelegt werden bevor Onyx starten kann.

### Voraussetzung
- PG Flex Instanz provisioniert (terraform apply)
- User-Credentials aus `terraform output pg_password`
- kubectl Zugriff auf den Cluster (für temporären Pod)

### Namespaces pro Umgebung

| Umgebung | Namespace | PG-Host | Anmerkung |
|----------|-----------|---------|-----------|
| DEV | `onyx-dev` | Aus `terraform output -raw pg_host` (environments/dev) | Shared Cluster |
| TEST | `onyx-test` | Aus `terraform output -raw pg_host` (environments/test) | Shared Cluster |
| PROD | `onyx-prod` | Aus `terraform output -raw pg_host` (environments/prod) | Eigener Cluster `vob-prod`, Flex 4.8 HA (3-Node), PITR aktiviert |

### Befehl (via temporären Pod)

```bash
# <NS> = onyx-dev | onyx-test | onyx-prod
kubectl run pg-createdb --restart=Never --namespace <NS> \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<PG_PASSWORD>" \
  --command -- psql -h <PG_HOST> -p 5432 -U onyx_app -d postgres \
  -c "CREATE DATABASE onyx OWNER onyx_app ENCODING 'UTF8';"

# Ergebnis prüfen
sleep 8 && kubectl logs pg-createdb -n <NS>
# Erwartete Ausgabe: "CREATE DATABASE"

# Aufräumen
kubectl delete pod pg-createdb -n <NS>
```

### Validierung

```bash
# <NS> = onyx-dev | onyx-test | onyx-prod
kubectl run pg-check --restart=Never --namespace <NS> \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<PG_PASSWORD>" \
  --command -- psql -h <PG_HOST> -p 5432 -U onyx_app -d onyx -c "SELECT 1;"

sleep 5 && kubectl logs pg-check -n <NS>
kubectl delete pod pg-check -n <NS>
```

---

## Managed PG: Kein CREATEROLE

StackIT PG Flex erlaubt NICHT, dass App-User andere Rollen erstellen. Der Terraform-Provider unterstützt nur die Rollen `login` und `createdb`.

### Auswirkung auf Onyx

Die Alembic-Migration `495cb26ce93e_create_knowlege_graph_tables.py` versucht beim Startup einen `db_readonly_user` per SQL anzulegen (`CREATE USER`). Das schlägt fehl mit:

```
asyncpg.exceptions.InsufficientPrivilegeError: permission denied to create role
```

### Lösung

Den `db_readonly_user` als separate `stackit_postgresflex_user`-Resource in Terraform anlegen:

```hcl
resource "stackit_postgresflex_user" "readonly" {
  project_id  = var.project_id
  instance_id = stackit_postgresflex_instance.main.instance_id
  username    = "db_readonly_user"
  roles       = ["login"]
}
```

Das Passwort wird automatisch generiert. Es muss als `DB_READONLY_PASSWORD` ENV-Variable in den Pods landen (über configMap in values-dev-secrets.yaml, gitignored).

Die Alembic-Migration prüft per `IF NOT EXISTS` ob der User existiert und überspringt die Erstellung wenn er bereits vorhanden ist.

---

## Verfügbare User-Rollen

| Rolle | Bedeutung | Terraform |
|-------|-----------|-----------|
| `login` | Kann sich anmelden | Standard |
| `createdb` | Kann Datenbanken erstellen | Für App-User |
| `createrole` | Kann Rollen erstellen | **NICHT verfügbar** auf StackIT PG Flex |
| `superuser` | Volle Admin-Rechte | **NICHT verfügbar** auf StackIT PG Flex |

---

## Verbindung testen (ohne lokales psql)

Temporärer Pod mit PostgreSQL-Client:

```bash
# <NS> = onyx-dev | onyx-test | onyx-prod
kubectl run pg-client --restart=Never --namespace <NS> \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<PG_PASSWORD>" \
  --command -- psql -h <PG_HOST> -p 5432 -U onyx_app -d onyx -c "\dt"

sleep 8 && kubectl logs pg-client -n <NS>
kubectl delete pod pg-client -n <NS>
```

---

## Backup & Recovery

> Detailliertes Konzept: `docs/backup-recovery-konzept.md`
> StackIT-Recherche: `audit-output/stackit-backup-recherche.md`
> Quelle: StackIT Service Certificate V1.1 (gueltig ab 12.09.2025)

### Backup-Schedule (Terraform-konfiguriert)

| Umgebung | Cron | Uhrzeit (UTC) | PG Config | PITR |
|----------|------|---------------|-----------|------|
| DEV | `0 2 * * *` | 02:00 | Flex 2.4 Single | Unklar |
| TEST | `0 3 * * *` | 03:00 | Flex 2.4 Single | Unklar |
| PROD | `0 1 * * *` | 01:00 | Flex 4.8 HA (3-Node) | **Ja** (sekundengenau) |

**Retention:** 30 Tage (StackIT Default)
**RPO/RTO (vertraglich):** 4h / 4h (fuer DB < 500 GB)
**Backup-Kosten:** Separat abgerechnet (pro GB/Stunde)

### Restore per Clone (PROD)

**WICHTIG:** StackIT PG Flex bietet **kein In-Place Restore**. Restore erstellt immer eine neue (geklonte) Instanz. Die Applikation muss auf die Clone-Instanz umgestellt werden.

**Voraussetzung:** Zugriff auf StackIT Portal oder CLI/API

**Verfahren:**

```bash
# 1. Clone erstellen (StackIT Portal)
#    PostgreSQL Flex → PROD-Instanz → Clone → Zeitpunkt waehlen
#    Alternativ per CLI: stackit postgresflex instance clone --help

# 2. Clone-Credentials abfragen
#    StackIT Portal → Clone-Instanz → Credentials / Connection Info
#    CLONE_HOST, CLONE_PASSWORD notieren

# 3. Clone validieren
kubectl run pg-verify --restart=Never --namespace onyx-prod \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<CLONE_PASSWORD>" \
  --command -- psql -h <CLONE_HOST> -p 5432 -U onyx_app -d onyx \
  -c "SELECT count(*) FROM chat_message; SELECT max(time_sent) FROM chat_message;"

sleep 10 && kubectl logs pg-verify -n onyx-prod
kubectl delete pod pg-verify -n onyx-prod

# 4. Applikation umstellen
#    Option A: Helm Re-Deploy mit neuem Connection String
#      values-prod-secrets.yaml → POSTGRES_HOST auf CLONE_HOST aendern
#      helm upgrade onyx-prod ... -f values-prod-secrets.yaml
#
#    Option B: K8s Secret direkt patchen (schneller, fuer Notfaelle)
#      kubectl edit secret <pg-secret> -n onyx-prod
#      Pods neustarten: kubectl rollout restart deployment -n onyx-prod

# 5. Health Check
curl -s https://prod.chatbot.voeb-service.de/api/health | jq .

# 6. Alte Instanz erst nach 24h Beobachtung loeschen
```

**Geschaetzte Dauer:** Clone ~30 Min + Umstellung ~30 Min = **1-2 Stunden** (DB aktuell < 1 GB)

### Backup-Verifizierung

```bash
# Pruefen ob PG-Instanz erreichbar und Daten konsistent
# <NS> = onyx-dev | onyx-test | onyx-prod
kubectl run pg-backup-check --restart=Never --namespace <NS> \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<PG_PASSWORD>" \
  --command -- psql -h <PG_HOST> -p 5432 -U onyx_app -d onyx \
  -c "SELECT 'tables' AS check_type, count(*) AS result FROM information_schema.tables WHERE table_schema='public' UNION ALL SELECT 'chat_msgs', count(*) FROM chat_message UNION ALL SELECT 'users', count(*) FROM \"user\";"

sleep 10 && kubectl logs pg-backup-check -n <NS>
kubectl delete pod pg-backup-check -n <NS>
```

### PGBackupCheckFailed Alert

Wenn der Alert `PGBackupCheckFailed` oder `PGBackupCheckNotScheduled` feuert:

**Schritt 1: CronJob-Logs pruefen**
```bash
# Letzten fehlgeschlagenen Job finden
kubectl get jobs -n monitoring -l app=pg-backup-check --sort-by='.status.startTime'

# Logs des fehlgeschlagenen Jobs lesen
kubectl logs -n monitoring job/<JOB_NAME>
```

**Schritt 2: Ursache identifizieren**

| Log-Meldung | Ursache | Loesung |
|-------------|---------|---------|
| "SA Key ID nicht gefunden" | Secret `stackit-backup-check` fehlt oder falsch | Secret pruefen: `kubectl get secret stackit-backup-check -n monitoring -o yaml` |
| "StackIT-Authentifizierung fehlgeschlagen" | SA Key abgelaufen oder ungueltig | Neuen SA Key in StackIT Portal erstellen, Secret aktualisieren |
| "Keine Antwort von StackIT Backup API" | API nicht erreichbar | NetworkPolicy `09-allow-backup-check-egress` pruefen, StackIT Status pruefen |
| "Keine Backups vorhanden" | Instanz hat keine Backups | StackIT Portal pruefen, Backup-Schedule verifizieren |
| "Letztes Backup fehlgeschlagen: ..." | StackIT Backup-Job Fehler | StackIT Support kontaktieren |
| "Backup ist Xh alt (Limit: 26h)" | Backup nicht gelaufen | StackIT Portal → PG Instanz → Backups pruefen |

**Schritt 3: Manuellen Check ausfuehren**
```bash
kubectl create job --from=cronjob/pg-backup-check pg-backup-check-manual -n monitoring
kubectl logs -n monitoring job/pg-backup-check-manual -f
kubectl delete job pg-backup-check-manual -n monitoring
```

**Schritt 4: Eskalation**
- Wenn StackIT-seitiges Problem: StackIT Support kontaktieren
- P1 (kein Backup seit >48h): VÖB Operations informieren (sofort)
- P2 (kein Backup seit >26h): VÖB Operations informieren (innerhalb 1h)

### Kritische Hinweise

1. **Backups sind instanzgebunden.** Bei Loeschung der PG-Instanz (z.B. `terraform destroy`) sind ALLE Backups unwiederbringlich verloren. `prevent_destroy = true` schuetzt, aber bei manueller Override nicht.
2. **Backup-Monitoring ist Kundenverantwortung.** StackIT bietet keine Alerts bei Backup-Fehlern. Der `pg-backup-check` CronJob uebernimmt diese Aufgabe.
3. **Geloeschte Instanzen:** 5 Tage Soft-Delete, Restore per Clone moeglich.
4. **DSGVO bei Restore:** Nach Restore muessen zwischenzeitlich geloeschte Daten erneut geloescht werden (EDSA Feb 2026).

---

## Troubleshooting

| Problem | Ursache | Lösung |
|---------|---------|--------|
| `database "onyx" does not exist` | DB nicht angelegt nach Terraform | DB manuell anlegen (siehe oben) |
| `permission denied to create role` | Managed PG hat kein CREATEROLE | User per Terraform anlegen |
| `Connection refused` | PG Flex ACL blockiert | ACL in `environments/{env}/main.tf` prüfen. DEV+TEST: Egress `188.34.93.194/32`, PROD: Egress `188.34.73.72/32` (jeweils + Admin-IP) |
| `password authentication failed` | Falsches Passwort | `terraform output -raw pg_password` prüfen |

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

- [Helm Deploy](./helm-deploy.md) — DB-Credentials in Helm Secrets konfigurieren
- [Rollback-Verfahren](./rollback-verfahren.md) — PG-Backup-Restore bei Datenbank-Problemen
