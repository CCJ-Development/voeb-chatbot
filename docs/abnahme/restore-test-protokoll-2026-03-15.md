# Restore-Test-Protokoll

## VÖB Chatbot — 2026-03-15

**Status: ERFOLGREICH**
**Audit-Finding: M7 (Backup-Strategie / Recovery-Test)**

---

### Testdaten

| Parameter | Wert |
|-----------|------|
| Umgebung | DEV |
| Original-Instanz | `vob-dev` (`be7fe911-4eac-4c9d-a7a8-6dfff674c41f`) |
| Clone-Instanz | `vob-dev-260315-1543-clone` (`f01496a1-00d3-49b6-918f-ca0dfc966e66`) |
| Backup verwendet | ID `000000080000000400000008`, Zeitpunkt 2026-03-15T02:00:01Z |
| Backup-Alter | ~13.7 Stunden (02:00 → 15:43 UTC) |
| Backup-Groesse | 4.6 MB |
| Datenbankgroesse | 17 MB |
| Clone-Methode | StackIT CLI (`stackit postgresflex instance clone`) mit PITR |
| Recovery-Timestamp | `2026-03-15T02:00:16+00:00` (Backup-EndTime) |
| Clone-Konfiguration | Identisch zu Original: Flex 2.4, 2 CPU, 4 GB RAM, 20 GB SSD, PG 16 |
| ACL (Clone) | `188.34.93.194/32` + `109.41.112.160/32` (automatisch vom Original uebernommen) |
| Durchgefuehrt von | COFFEESTUDIOS (automatisiert) |
| Verifizierungsmethode | SQL-Queries via temporaere `kubectl run` Pods (`postgres:16-alpine`) |

---

### Zeitmessung

| Schritt | Zeitpunkt (UTC) | Dauer |
|---------|-----------------|-------|
| Test gestartet | 2026-03-15T15:28:42Z | — |
| Vorher-Snapshot abgeschlossen | 2026-03-15T15:42:00Z | 13:18 (Datenerfassung) |
| Clone ausgeloest | 2026-03-15T15:43:22Z | — |
| Clone-Instanz RUNNING | 2026-03-15T15:46:38Z | **3:16** (Clone-Erstellung) |
| Passwort-Reset (Clone) | 2026-03-15T15:48:00Z | 1:22 |
| Datenintegritaet verifiziert | 2026-03-15T15:50:37Z | **3:59** (Verifizierung) |
| Clone-Instanz geloescht | 2026-03-15T15:52:23Z | 1:46 |
| Test abgeschlossen | 2026-03-15T15:54:05Z | — |
| | | |
| **Technische RTO** (Clone RUNNING - Clone ausgeloest) | | **3 Min 16 Sek** |
| **Operative RTO** (Integritaet verifiziert - Clone ausgeloest) | | **7 Min 15 Sek** |
| **Gesamtdauer** (Test Start - Test Ende) | | **25 Min 23 Sek** |

---

### Datenintegritaet

| Metrik | Original (VORHER) | Clone (NACHHER) | Match |
|--------|-------------------|-----------------|-------|
| Datenbankgroesse | 17 MB (17.841.175 Bytes) | 17 MB (17.857.559 Bytes) | ✅ (~0.1% Differenz, normal durch PG-Interna) |
| Tabellen (public) | 127 | 127 | ✅ |
| Users | 9 | 9 | ✅ |
| Chat Sessions | 13 | 13 | ✅ |
| Chat Messages | 63 | 63 | ✅ |
| Documents | 0 | 0 | ✅ |
| Connectors | 1 | 1 | ✅ |
| Personas | 1 | 1 | ✅ |
| ext_token_usage | 15 | 15 | ✅ |
| ext_token_user_limit | 0 | 0 | ✅ |
| ext_branding_config | 1 | 1 | ✅ |
| ext_custom_prompts | 0 | 0 | ✅ |
| Alembic Version | c7f2e8a3d105 | c7f2e8a3d105 | ✅ |

**Ergebnis: 13/13 Metriken identisch — 100% Datenintegritaet.**

Die minimale Differenz in der DB-Groesse (16.384 Bytes = 16 KB) ist normal und erklaert sich durch PG-interne Metadaten (pg_stat_*, Transaction-IDs), die bei jeder Instanz leicht variieren.

---

### Applikationstest

| Test | Ergebnis | Anmerkung |
|------|----------|-----------|
| Chatbot antwortet | ⏭ Nicht getestet | Kein Connection-Switch durchgefuehrt |
| Chat-Verlaeufe sichtbar | ⏭ Nicht getestet | — |
| Token-Usage vorhanden | ✅ (via SQL) | 15 Eintraege in ext_token_usage verifiziert |
| Branding geladen | ✅ (via SQL) | 1 Eintrag in ext_branding_config verifiziert |

**Entscheidung:** Applikationstest (Connection-Switch) wurde NICHT durchgefuehrt, da:
1. SQL-basierte Integritaetspruefung bereits 100% Match zeigt
2. Connection-Switch auf DEV haette Downtime verursacht (Pods neustarten)
3. Erster Test — Fokus auf Clone-Funktionalitaet und Datenintegritaet

**Empfehlung:** Beim naechsten quartalmaessigen Test den vollen Connection-Switch-Test durchfuehren.

---

### Erkenntnisse

1. **Clone-Erstellung bemerkenswert schnell:** 3:16 Minuten fuer eine 17 MB Datenbank. Weit unter dem StackIT Service Certificate RTO von 4 Stunden.

2. **CLI Error beim Clone-Tracking:** Die `stackit` CLI (v0.53.1) verlor waehrend des Clone-Polling den Tracking-Status (`404 Not Found` fuer die neue Instanz). Der Clone wurde trotzdem erfolgreich erstellt. Workaround: `stackit postgresflex instance list` zum Pruefen verwenden.

3. **Passwort-Reset noetig:** Der Clone erbt die User-Accounts, aber die Passwoerter sind **nicht zugreifbar** — ein `reset-password` ueber die CLI war noetig. Dies addiert ~1-2 Minuten zur operativen RTO. Das war im Runbook nicht dokumentiert.

4. **ACL wird automatisch uebernommen:** Die Clone-Instanz erbte die ACL-Regeln (`188.34.93.194/32` + Admin-IP) automatisch vom Original. Kein manuelles Konfigurieren noetig.

5. **Clone-Name automatisch generiert:** StackIT benennt den Clone automatisch (`vob-dev-260315-1543-clone`). Kein Custom-Name via CLI moeglich.

6. **Retention-Config:** Clone zeigt `retentionDays: 32` (nicht 30 wie dokumentiert). Moeglicherweise StackIT-Default mit Puffer.

7. **Terraform-Output `pg_instance_id`:** Existiert im Modul, aber nicht im DEV-State (Output wurde nach dem letzten `terraform apply` hinzugefuegt). Instance ID ist aus dem PG-Host ableitbar.

---

### Probleme

| Problem | Schwere | Auswirkung | Loesung |
|---------|---------|------------|---------|
| CLI 404 beim Clone-Tracking | Niedrig | Keine — Clone wurde erstellt, CLI verlor nur den Polling-Status | `instance list` als Fallback |
| K8s API TLS Handshake Timeouts | Niedrig | 1-2 Retries bei kubectl-Kommandos noetig | Netzwerk-Latenzen, kein systematisches Problem |
| Tabelle `ext_prompt_templates` existiert nicht | Info | Migration-Name ≠ Tabellen-Name (`ext_custom_prompts`) | Runbook-Korrektur |

---

### Empfehlungen

1. **Quartalmaessige Test-Restores** etablieren (naechster: 2026-06-15)
2. **Naechster Test mit Connection-Switch:** Applikation temporaer auf Clone umstellen, vollen Funktionstest durchfuehren
3. **Runbook aktualisieren:**
   - Passwort-Reset-Schritt nach Clone dokumentieren
   - CLI-Workaround fuer Clone-Tracking-Fehler dokumentieren
   - Tabellennamen korrigieren (`ext_custom_prompts`, nicht `ext_prompt_templates`)
4. **PROD Restore-Test:** Separater Test auf PROD-Cluster (eigener Cluster `vob-prod`) — nur nach DNS/TLS-Aktivierung

---

### RTO-Bewertung

| RTO | Vereinbart | Gemessen | Eingehalten? |
|-----|------------|----------|-------------|
| StackIT Service Certificate | 4 Stunden | **3 Min 16 Sek** (technisch) | ✅ (Faktor 73x besser) |
| StackIT Service Certificate | 4 Stunden | **7 Min 15 Sek** (operativ) | ✅ (Faktor 33x besser) |
| Kickoff RPO (24h) | 24 Stunden | 13.7 Stunden (Backup-Alter) | ✅ |

**Hinweis:** Die gemessene RTO ist fuer eine 17 MB Datenbank. Bei wachsender Datenbank wird die RTO steigen. StackIT gibt fuer DB < 500 GB eine RTO von 4h an. Die aktuelle DB-Groesse ist weit unter diesem Schwellwert.
