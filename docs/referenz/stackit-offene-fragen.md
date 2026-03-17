# Offene Fragen an StackIT

**Stand:** 2026-03-16
**Kontext:** VÖB Chatbot — Backup-Analyse + Cloud-Infrastruktur-Audit
**Projekt-ID:** StackIT Projekt (SKE + PG Flex + Object Storage, Region eu01)

---

## Bereits beantwortet (durch eigene Recherche/Tests)

| Nr. | Frage | Antwort | Quelle |
|-----|-------|---------|--------|
| S4 | Gibt es eine API/CLI zum Abfragen ob das letzte Backup erfolgreich war? | **Ja.** `stackit postgresflex backup list --instance-id <ID>` zeigt Backup-Inventar mit Timestamps, Expiration, Size. API v2 hat `/backups`-Endpoint. Portal: Backups-Tab auf Instanz-Seite. | [Backup How-To](https://docs.stackit.cloud/products/databases/postgresql-flex/how-tos/backup-and-clone-postgresql-flex/), [CLI Docs](https://github.com/stackitcloud/stackit-cli/blob/main/docs/stackit_postgresflex.md) |
| S6 | Ist PITR bei Flex 2.4 Single (DEV/TEST) verfuegbar? | **Ja (sehr wahrscheinlich).** Doku macht keinen Unterschied zwischen Single und Replica bzgl. PITR. WAL ist "activated by default" fuer alle Instanzen. Einziger Unterschied: Verfuegbarkeit/SLA (Single = Downtime bei Maintenance). | [PG Flex Introduction](https://docs.stackit.cloud/products/databases/postgresql-flex/basics/introduction-to-postgresql-flex/), Service Certificate V1.1 |

### S4 Zusatzinfo

Unser `PGBackupCheck` CronJob (implementiert 2026-03-15) nutzt die StackIT REST API direkt (`GET /v2/.../backups`). JWT-Auth ueber Service Account Key. Alert `PGBackupCheckFailed` feuert wenn letztes Backup aelter als 26h. Details: `audit-output/backup-monitoring-ergebnis.md`.

---

## Teilweise beantwortet (Restfragen an StackIT)

| Nr. | Frage | Was wir wissen | Was offen ist |
|-----|-------|----------------|---------------|
| S3 | Ist die 30-Tage Backup-Retention konfigurierbar? Kosten? | Service Certificate sagt "30 days **(Default)**" — das "(Default)" impliziert Konfigurierbarkeit. Backup-Storage wird separat abgerechnet (pro GB/Stunde). Terraform hat `backup_schedule` aber kein `backup_retention_days`. | Welcher Mechanismus? Portal/API/Support-Ticket? Kosten-Staffelung? |
| S5 | Wie funktioniert der Clone-Restore technisch? Erbt die Clone-Instanz ACL/Config? | Restore = Clone auf neue Instanz (kein In-Place). Daten, User, Rollen werden restored. Storage-Class/Size konfigurierbar. Geloeschte Instanzen 5 Tage lang klonbar. | **ACL-Vererbung undokumentiert.** Muss die Netzwerk-ACL manuell neu konfiguriert werden? Werden PG-Konfigurationsparameter uebernommen? |

---

## Noch offen (an StackIT Support senden)

| Nr. | Frage | Kontext | Prioritaet |
|-----|-------|---------|------------|
| S1 | Werden PG Flex Backups ueber mehrere Availability Zones gespeichert? | Geo-Redundanz der Backup-Daten nicht dokumentiert. Object Storage nutzt 3-AZ Replikation — gilt das auch fuer PG Flex Backups? StackIT Region eu01 hat 3+ AZs. | MITTEL |
| S2 | Welcher Verschluesselungsalgorithmus wird fuer PG Flex Backup-Daten at-rest verwendet? | AES-256 fuer Object Storage bestaetigt, aber nicht explizit fuer PG Flex Backups. BSI C5 Type 2 Zertifizierung impliziert starke Verschluesselung, aber explizite Bestaetigung fehlt. | NIEDRIG |
| S3* | Ist die 30-Tage Retention konfigurierbar? Wenn ja, ueber welchen Mechanismus und zu welchen Kosten? | Service Certificate sagt "30 days (Default)". Terraform/CLI haben keinen Retention-Parameter. | MITTEL |
| S5* | Erbt eine per Clone wiederhergestellte PG Flex Instanz die Netzwerk-ACL und PG-Konfiguration der Quell-Instanz? | Relevant fuer Disaster-Recovery-Runbook. Falls ACL nicht vererbt wird, muss sie im Runbook als manueller Schritt dokumentiert werden. | MITTEL |

*S3 und S5 sind teilweise beantwortet, Restfrage offen.

---

## Support-Ticket Entwurf

**Betreff:** VÖB Chatbot — Technische Fragen PostgreSQL Flex Backups (4 Punkte)

Sehr geehrtes StackIT Support-Team,

wir nutzen StackIT PostgreSQL Flex (Flex 2.4 Single + Flex 4.8 HA) in der Region eu01 fuer unser Projekt "VÖB Chatbot". Im Rahmen unserer Sicherheitsdokumentation (BSI-orientiert) haben wir folgende technische Fragen zu den Backup-Mechanismen:

**1. Geo-Redundanz der PG Flex Backups (S1)**

Werden die automatischen Backups von PostgreSQL Flex ueber mehrere Availability Zones innerhalb der Region gespeichert? Die Dokumentation zu Object Storage nennt 3-AZ Replikation — gilt das analog fuer PG Flex Backup-Daten?

**2. Verschluesselung der Backup-Daten (S2)**

Welcher Verschluesselungsalgorithmus wird fuer PG Flex Backup-Daten at-rest verwendet? Fuer Object Storage ist AES-256 dokumentiert. Koennen Sie bestaetigen, dass PG Flex Backups ebenfalls mit AES-256 (oder vergleichbar) verschluesselt sind?

**3. Backup-Retention konfigurierbar? (S3)**

Das Service Certificate V1.1 nennt "Retention Period: 30 days (Default)". Das "(Default)" deutet auf Konfigurierbarkeit hin. Ueber welchen Mechanismus (Portal, API, Terraform, Support-Ticket) kann die Retention angepasst werden? Gibt es eine Kosten-Staffelung fuer laengere Retention-Zeitraeume?

**4. Clone-Restore: ACL-Vererbung (S5)**

Wenn wir eine PG Flex Instanz per Clone aus einem Backup wiederherstellen: Erbt die neue Instanz die Netzwerk-ACL-Konfiguration (`instance_acl`) der Quell-Instanz? Oder muss die ACL manuell neu konfiguriert werden? Dasselbe fuer etwaige PG-Konfigurationsparameter.

Hintergrund: Wir erstellen ein Disaster-Recovery-Runbook und muessen dokumentieren, welche Schritte nach einem Restore manuell notwendig sind.

Vielen Dank fuer Ihre Unterstuetzung.

Mit freundlichen Gruessen,
Nikolaj Ivanov
CCJ / Coffee Studios
(im Auftrag des VÖB — Bundesverband Oeffentlicher Banken Deutschlands)
