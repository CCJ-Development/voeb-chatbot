# Loeschkonzept -- VoeB Service Chatbot

**Status:** ENTWURF -- Abstimmung mit VoeB ausstehend
**Version:** 0.1
**Datum:** 2026-03-14
**Autor:** CCJ / Coffee Studios (Nikolaj Ivanov)
**Naechste Ueberpruefung:** Bei VoeB-Abstimmung (vor PROD Go-Live)

> Dieses Dokument orientiert sich an **DIN EN ISO/IEC 27555:2025-09** (vormals DIN 66398:2016-05, zurueckgezogen September 2025). Alle `[KLAERUNG]`-Marker erfordern eine Entscheidung durch VoeB. Alle `[NICHT IMPLEMENTIERT]`-Marker bezeichnen technische Massnahmen die noch gebaut werden muessen.

---

## Aenderungshistorie

| Version | Datum | Autor | Aenderungen |
|---------|-------|-------|-------------|
| 0.1 | 2026-03-14 | CCJ | Initialer Entwurf basierend auf Compliance-Research, Betriebs- und Sicherheitskonzept |

---

## 1. Geltungsbereich

Dieses Loeschkonzept gilt fuer alle personenbezogenen und personenbeziehbaren Daten die im VoeB Service Chatbot verarbeitet werden. Es umfasst:

**Systeme:**
- PostgreSQL (StackIT Managed Flex) -- Chat-Daten, User-Accounts, Token-Usage, Extension-Konfiguration
- Vespa (In-Cluster) -- Vektor-Embeddings und indexierte Dokumentinhalte
- StackIT Object Storage (S3-kompatibel) -- Datei-Uploads, Connector-Dokumente
- Redis (In-Cluster) -- Cache und Session-Daten (ephemer)
- Prometheus (In-Cluster) -- Monitoring-Metriken (aggregiert)
- Kubernetes Pod-Logs -- Anwendungsprotokolle

**Umgebungen:**
- DEV (`https://dev.chatbot.voeb-service.de`)
- TEST (`https://test.chatbot.voeb-service.de`)
- PROD (deployed, DNS/TLS ausstehend)

**Betroffene Personen:**
- VoeB-Mitarbeiter (Chat-Nutzer)
- Administratoren (CCJ / VoeB IT)
- Personen deren Daten in indexierten Dokumenten enthalten sein koennten

---

## 2. Rechtliche Grundlagen

### 2.1 Direkt anwendbare Rechtsgrundlagen

| Norm | Artikel/Paragraph | Relevanz |
|------|-------------------|----------|
| **DSGVO** | **Art. 5 Abs. 1 lit. e** (Speicherbegrenzung) | Personenbezogene Daten duerfen nur so lange gespeichert werden, wie es fuer den Verarbeitungszweck erforderlich ist |
| **DSGVO** | **Art. 17** (Recht auf Loeschung) | Betroffene haben das Recht, die Loeschung ihrer Daten zu verlangen; Verantwortlicher muss ohne ungebuehrliche Verzoegerung loeschen |
| **DSGVO** | **Art. 17 Abs. 3** (Ausnahmen) | Loeschpflicht entfaellt bei gesetzlichen Aufbewahrungspflichten, Ausuebung/Verteidigung von Rechtsanspruechen, oeffentliches Interesse |
| **DSGVO** | **Art. 25 Abs. 2** (Privacy by Default) | Nur die fuer den Zweck erforderlichen Daten werden standardmaessig verarbeitet |
| **DSGVO** | **Art. 30** (Verzeichnis der Verarbeitungstaetigkeiten) | Loeschfristen muessen im VVT dokumentiert sein |
| **BDSG** | **§ 35** (Einschraenkung statt Loeschung) | Falls Loeschung technisch unverhaeltnismaessig: Einschraenkung der Verarbeitung als Alternative |
| **HGB** | **§§ 238, 257** | Handelsrechtliche Aufbewahrungspflichten (6/10 Jahre) -- gilt fuer VoeB-Geschaeftsunterlagen, NICHT fuer Chatbot-Konversationen |
| **AO** | **§ 147** | Steuerliche Aufbewahrungspflichten (6/10 Jahre) -- gilt fuer steuerlich relevante Unterlagen, NICHT fuer Chatbot-Konversationen |

### 2.2 Freiwillige Orientierung

| Norm/Standard | Relevanz |
|---------------|----------|
| **DIN EN ISO/IEC 27555:2025-09** | Struktur und Methodik dieses Loeschkonzepts (Datenarten, Loeschklassen, Loeschregeln, Umsetzungsregeln) |
| **BSI IT-Grundschutz CON.6** | Differenzierung nach Schutzbedarf: Normal = logisches Loeschen ausreichend bei Encryption-at-Rest |
| **BAIT Kap. 8** (freiwillig) | Datensicherung und Datenhaltung im IT-Betrieb |

### 2.3 Abgrenzung: Chat-Daten vs. Geschaeftsunterlagen

Chat-Konversationen im VoeB-Chatbot sind im Regelfall **KEINE** Handelsbriefe (HGB §257) oder Buchungsbelege (AO §147). Sie fallen primaer unter DSGVO-Grundsaetze (Zweckbindung, Speicherbegrenzung). Die HGB/AO-Mindestfristen von 6-10 Jahren greifen fuer Chatbot-Daten **NICHT** direkt.

**Ausnahme:** Falls einzelne Chat-Inhalte steuerlich oder handelsrechtlich relevant werden (unwahrscheinlich bei Wissensmanagement-Tool), greift Art. 17 Abs. 3 lit. b DSGVO (Aufbewahrungspflicht als Loeschausnahme).

---

## 3. Dateninventar und Loeschfristen

### 3.1 Loeschklassen (nach DIN EN ISO/IEC 27555)

| Loeschklasse | Frist | Beschreibung |
|--------------|-------|-------------|
| **LK-SESSION** | Session-Ende + 24h | Ephemere Session-/Cache-Daten |
| **LK-30D** | 30 Tage | Logs, Backups, temporaere Daten |
| **LK-6M** | 6 Monate | Chat-Verlaeufe (Kickoff-Beschluss) |
| **LK-12M** | 12 Monate | Nutzungsmetriken (Empfehlung fuer Jahresberichte) |
| **LK-AKTIV** | Solange Account aktiv | Konfigurationsdaten gebunden an aktiven User |
| **LK-UNBEGRENZT** | Unbegrenzt | System-Konfiguration ohne Personenbezug |
| **LK-PROMETHEUS** | 30d DEV/TEST, 90d PROD | Aggregierte Monitoring-Metriken |

### 3.2 Dateninventar

| # | Datenart | Speicherort | Personenbezug | Rechtsgrundlage | Loeschklasse | Aufbewahrungsfrist | Loeschmechanismus | Status |
|---|----------|-------------|---------------|-----------------|--------------|--------------------|--------------------|--------|
| D1 | **Chat-Verlaeufe** (Konversationen, Nachrichten) | PostgreSQL (`chat_session`, `chat_message`) | **Ja** (User-ID, Inhalte koennten PII enthalten) | Art. 6(1)(f) berechtigtes Interesse | **LK-6M** | **6 Monate** (Kickoff-Beschluss) | `[NICHT IMPLEMENTIERT]` -- Cronjob/DB-Funktion | :warning: |
| D2 | **Token-Usage-Logs** (LLM-Nutzungsstatistiken) | PostgreSQL (`ext_token_usage`) | **Ja** (User-ID, aufloesbar zu E-Mail via `_resolve_user_uuid()`) | Art. 6(1)(f) berechtigtes Interesse | **LK-12M** | **12 Monate** (Empfehlung, `[KLAERUNG]` VoeB) | `[NICHT IMPLEMENTIERT]` -- Anonymisierung nach Frist | :warning: |
| D3 | **User-Token-Limits** (Per-User Budgets) | PostgreSQL (`ext_token_user_limit`) | **Ja** (User-ID als FK) | Art. 6(1)(f) berechtigtes Interesse | **LK-AKTIV** | Solange User-Account aktiv | Manuell (Admin-UI) + CASCADE bei User-Loeschung | :warning: |
| D4 | **User-Accounts** (E-Mail, Rollen, Hashes) | PostgreSQL (`user`) | **Ja** | Art. 6(1)(f) berechtigtes Interesse | **LK-AKTIV** | Beschaeftigungsdauer + 30 Tage (`[KLAERUNG]` VoeB) | `[NICHT IMPLEMENTIERT]` -- Deprovisioning via Entra ID | :warning: |
| D5 | **Prompt-Templates** (System Prompts) | PostgreSQL (`ext_prompt_templates`) | **Nein** (System-Konfiguration) | -- | **LK-UNBEGRENZT** | Unbegrenzt | Manuell (Admin-UI) | :white_check_mark: |
| D6 | **Branding-Config** (Logo, App-Name, Disclaimer) | PostgreSQL (`ext_branding_config`) | **Nein** (System-Konfiguration) | -- | **LK-UNBEGRENZT** | Unbegrenzt | Manuell (Admin-UI) | :white_check_mark: |
| D7 | **Auth-Sessions** (Session-Tokens, Cookies) | PostgreSQL + Redis | **Ja** (Session-ID, User-Zuordnung) | Art. 6(1)(f) berechtigtes Interesse | **LK-SESSION** | Session-Dauer (Cookie-Expiry) | Automatisch (Cookie/Redis TTL) | :white_check_mark: |
| D8 | **Indexierte Dokumente** (Embeddings + Quelltexte) | Vespa + PostgreSQL (`document`, `document_by_connector_credential_pair`) | **Ggf.** (Dokumentinhalte koennten PII enthalten) | `[KLAERUNG]` -- abhaengig von Dokumentquelle | `[KLAERUNG]` | `[KLAERUNG]` -- Lebensdauer des Connectors | Manuell (Connector-Loeschung in Admin-UI loescht Docs + Embeddings) | :warning: |
| D9 | **Monitoring-Metriken** | Prometheus PVC (`monitoring` Namespace) | **Nein** (aggregierte Zaehler, keine PII) | Art. 6(1)(f) berechtigtes Interesse | **LK-PROMETHEUS** | 30d DEV/TEST, 90d PROD | Automatisch (Prometheus `--storage.tsdb.retention.time`) | :white_check_mark: |
| D10 | **Kubernetes Pod-Logs** | Node-Filesystem (ephemer) | **Ggf.** (IP-Adressen in Access-Logs) | Art. 6(1)(f) berechtigtes Interesse | Ephemer | Pod-Lebensdauer (kein persistentes Log-Aggregation) | Automatisch (Pod-Restart loescht Logs) | :warning: |
| D11 | **PostgreSQL-Backups** | StackIT Object Storage (Managed) | **Ja** (enthalten alle DB-Daten) | Art. 6(1)(f) berechtigtes Interesse | **LK-30D** | StackIT Managed (geschaetzt 30 Tage, `[KLAERUNG]` exakte Policy) | Automatisch (StackIT Managed Backup-Rotation) | :white_check_mark: |
| D12 | **Object Storage Dateien** (Uploads, Connector-Files) | StackIT Object Storage (`vob-dev`, `vob-test`, `vob-prod`) | **Ggf.** (Dateiinhalte koennten PII enthalten) | `[KLAERUNG]` -- abhaengig von Dokumentquelle | `[KLAERUNG]` | `[KLAERUNG]` -- an Connector-Lebensdauer gebunden | Manuell (Connector-Loeschung) + S3 Lifecycle Policies (`[NICHT IMPLEMENTIERT]`) | :warning: |
| D13 | **Search-Docs / Chat-Referenzen** | PostgreSQL (`chat_message__search_doc`) | **Ja** (indirekt via Chat-Message FK) | Art. 6(1)(f) berechtigtes Interesse | **LK-6M** | Folgt Chat-Session (CASCADE) | CASCADE bei Chat-Loeschung | :white_check_mark: |

### 3.3 Zusammenfassung nach Loeschklasse

| Loeschklasse | Datenarten | Automatisiert? |
|--------------|-----------|----------------|
| LK-SESSION | D7 Auth-Sessions | :white_check_mark: Ja (Cookie/Redis TTL) |
| LK-30D | D11 PG-Backups | :white_check_mark: Ja (StackIT Managed) |
| LK-PROMETHEUS | D9 Monitoring-Metriken | :white_check_mark: Ja (Prometheus Retention) |
| **LK-6M** | **D1 Chat-Verlaeufe, D13 Search-Docs** | :x: **NICHT IMPLEMENTIERT** |
| **LK-12M** | **D2 Token-Usage** | :x: **NICHT IMPLEMENTIERT** |
| LK-AKTIV | D3 User-Limits, D4 User-Accounts | :warning: Teilweise (CASCADE vorhanden, Deprovisioning fehlt) |
| LK-UNBEGRENZT | D5 Prompts, D6 Branding | :white_check_mark: Kein Loeschbedarf |

---

## 4. Loeschprozesse

### 4.1 Chat-Retention (6 Monate) -- `[NICHT IMPLEMENTIERT]`

**Datenart:** D1 Chat-Verlaeufe + D13 Search-Docs
**Trigger:** Fristablauf -- Chat-Sessions aelter als 6 Monate nach `time_created`
**Frist:** 6 Monate (180 Tage), festgelegt im Kickoff

**Mechanismus (noch zu implementieren):**

Variante A -- PostgreSQL Cronjob (empfohlen):
```sql
-- Loescht Chat-Sessions aelter als 6 Monate
-- CASCADE loescht automatisch: chat_message, chat_message__search_doc, chat_message__standard_answer
DELETE FROM chat_session
WHERE time_created < NOW() - INTERVAL '6 months'
  AND deleted = false;
```

Variante B -- Celery Periodic Task:
```python
# Laeuft als Celery Beat Task (z.B. taeglich um 04:00 UTC)
# Nutzt SQLAlchemy ORM fuer saubere CASCADE-Loeschung
```

**Empfehlung:** Variante B (Celery Task) -- konsistent mit Onyx-Architektur, loggbar, Feature-Flag-faehig.

**Onyx-Besonderheit:** Onyx hat ein `deleted`-Flag auf `chat_session` (Soft-Delete). Das Loeschkonzept muss entscheiden:
- **Option 1:** Soft-Delete setzen (`deleted = true`) bei 6 Monaten, Hard-Delete nach 7 Monaten (Grace Period)
- **Option 2:** Direktes Hard-Delete bei 6 Monaten (kein Recovery moeglich)
- **Empfehlung:** Option 1 mit 30 Tagen Grace Period (`[KLAERUNG]` VoeB)

**Verantwortung:** Automatisch (System), ueberwacht durch Monitoring-Metrik
**Nachweis:** Log-Eintrag mit Anzahl geloeschter Sessions + Zeitstempel

### 4.2 Token-Usage-Retention (12 Monate Empfehlung) -- `[NICHT IMPLEMENTIERT]`

**Datenart:** D2 Token-Usage-Logs
**Aufbewahrungsfrist:** `[KLAERUNG]` -- VoeB muss entscheiden
**Empfehlung:** 12 Monate Vollstaendig, danach Anonymisierung

**Begruendung der 12-Monats-Empfehlung:**
- Ermoeglicht Jahresberichte und Kostenanalysen (Geschaeftsjahr-Vergleich)
- Token-Usage enthaelt User-ID (pseudonymisiert als UUID, aber via `_resolve_user_uuid()` zu E-Mail aufloesbar) -- daher DSGVO-relevant
- Bei ~100k Rows/Monat (150 User) waechst die Tabelle auf ~1,2 Mio Rows/Jahr -- technisch unproblematisch

**Mechanismus (noch zu implementieren):**

Phase 1 -- Anonymisierung nach 12 Monaten:
```sql
-- Entfernt Personenbezug, behaelt aggregierte Daten fuer Statistiken
UPDATE ext_token_usage
SET user_id = NULL
WHERE created_at < NOW() - INTERVAL '12 months'
  AND user_id IS NOT NULL;
```

Phase 2 -- Hard-Delete nach 24 Monaten (optional):
```sql
DELETE FROM ext_token_usage
WHERE created_at < NOW() - INTERVAL '24 months';
```

**Verantwortung:** Automatisch (Celery Task oder PG Cronjob)
**Nachweis:** Log-Eintrag mit Anzahl anonymisierter/geloeschter Rows

### 4.3 Betroffenenrechte -- Art. 17 Loeschantrag

**Datenart:** Alle personenbezogenen Daten eines Betroffenen (D1, D2, D3, D4, D7)
**Rechtsgrundlage:** Art. 17 DSGVO (Recht auf Loeschung)
**Frist:** 1 Monat nach Eingang (Art. 12 Abs. 3 DSGVO), verlaengerbar um 2 Monate bei Komplexitaet

**Prozess:**

```
1. Eingang: Loeschantrag per E-Mail an VoeB-DSB
   └→ Verantwortlich: VoeB (Verantwortlicher i.S.d. DSGVO)

2. Pruefung (VoeB-DSB):
   ├→ Identitaet des Antragstellers verifizieren
   ├→ Pruefung Art. 17 Abs. 3 (Ausnahmen: Aufbewahrungspflicht, Rechtsansprueche)
   └→ Bei Ausnahme: Einschraenkung statt Loeschung (BDSG §35), Begruendung an Betroffenen

3. Durchfuehrung (CCJ / System-Admin):
   ├→ Chat-Sessions des Users: DELETE FROM chat_session WHERE user_id = ?
   ├→ Token-Usage: UPDATE ext_token_usage SET user_id = NULL WHERE user_id = ?
   │   (Anonymisierung statt Loeschung -- aggregierte Daten bleiben fuer Berichte)
   ├→ User-Limits: DELETE FROM ext_token_user_limit WHERE user_id = ?
   ├→ Auth-Sessions: Redis Invalidierung + Cookie Revocation
   └→ User-Account: Deaktivierung oder Loeschung (je nach VoeB-Entscheidung)

4. Nachweis:
   ├→ Loeschprotokoll erstellen (Datum, Umfang, durchfuehrende Person)
   └→ Bestaetigung an Betroffenen (innerhalb 1 Monat)

5. Sonderfaelle:
   ├→ Backups: Loeschung in Backups NICHT zwingend erforderlich,
   │   WENN bei Restore die Loeschung wiederholt wird (EDSA Feb 2026)
   ├→ Vespa-Embeddings: Keine nutzerspezifischen Embeddings im System
   │   (Embeddings sind dokumentbezogen, nicht userbezogen)
   └→ Shared Chats: Falls Chat geteilt wurde, Loeschung nur der User-Zuordnung
```

**`[KLAERUNG]`**: Manueller Prozess oder Self-Service-Portal? Empfehlung fuer v1: Manuell ueber VoeB-DSB (geringes Volumen erwartet).

### 4.4 Account-Deprovisioning (bei Austritt) -- `[NICHT IMPLEMENTIERT]`

**Datenart:** D4 User-Accounts + abhaengige Daten (D1, D2, D3, D7)
**Trigger:** Entra ID Account deaktiviert/geloescht (SCIM oder manuell)

**Prozess:**

```
1. Trigger: User-Account in Entra ID deaktiviert
   └→ [NICHT IMPLEMENTIERT] -- Erkennung ueber ext-rbac Modul (Phase 4f, blockiert durch Entra ID)

2. Sofort-Massnahmen:
   ├→ Auth-Sessions invalidieren (Redis + Cookie)
   ├→ User-Account deaktivieren (kein Login moeglich)
   └→ User-Token-Limit deaktivieren

3. Nach Karenzzeit (Empfehlung: 30 Tage):
   ├→ Chat-Sessions: Soft-Delete setzen (deleted = true)
   ├→ Token-Usage: Anonymisierung (user_id = NULL)
   ├→ User-Limits: CASCADE-Loeschung (FK ON DELETE CASCADE vorhanden)
   └→ User-Account: Hard-Delete

4. Regulaere Frist:
   └→ Chat-Inhalte: Regulaere 6-Monats-Retention greift weiterhin
```

**Abhaengigkeit:** Entra ID Integration (Phase 3, blockiert) + ext-rbac Modul (Phase 4f)

### 4.5 Indexierte Dokumente und Embeddings

**Datenart:** D8 Indexierte Dokumente, D12 Object Storage Dateien
**Loeschprinzip:** Embedding + Quelldokument = eine Loescheinheit (keine separaten Zyklen)

**Aktueller Mechanismus (manuell):**
- Admin loescht Connector in Onyx Admin-UI
- Onyx loescht automatisch alle zugehoerigen Dokumente aus Vespa (Embeddings) und PostgreSQL (Metadaten)
- Celery-Worker fuehrt `connector_deletion` Task aus

**Offene Punkte:**
- `[KLAERUNG]`: Sollen Dokument-Loeschfristen an Connector-Konfiguration gebunden werden?
- `[KLAERUNG]`: Wie wird sichergestellt, dass geloeschte Quelldokumente nicht erneut indexiert werden? (Connector-Re-Sync koennte geloeschte Docs wiederherstellen)
- `[NICHT IMPLEMENTIERT]`: S3 Lifecycle Policies fuer automatische Bereinigung verwaister Dateien

### 4.6 Monitoring-Daten und Logs

**Datenart:** D9 Monitoring-Metriken, D10 Pod-Logs

| System | Retention | Mechanismus | Status |
|--------|-----------|-------------|--------|
| Prometheus DEV/TEST | 30 Tage | `--storage.tsdb.retention.time=30d` | :white_check_mark: Implementiert |
| Prometheus PROD | 90 Tage | `--storage.tsdb.retention.time=90d` | :white_check_mark: Implementiert |
| Pod-Logs | Pod-Lebensdauer | Kubernetes-nativ (logsrotation) | :warning: Kein persistentes Logging |

**Hinweis:** Ohne zentralisierte Log-Aggregation (ELK/Loki) gehen Pod-Logs bei Restart verloren. Dies ist aus Datenschutzsicht vorteilhaft (automatische Loeschung), aber aus Audit-Sicht problematisch (BSI OPS.1.1.5 A6 nicht erfuellt).

---

## 5. Loeschmethoden und Schutzbedarf

### 5.1 Schutzbedarf-Einstufung (nach BSI CON.6)

| Datenart | Schutzbedarf | Loeschmethode |
|----------|-------------|---------------|
| Chat-Verlaeufe (D1) | **Normal** | Logisches Loeschen (SQL DELETE) + PostgreSQL Autovacuum. Ausreichend bei Encryption-at-Rest (StackIT AES-256, SEC-07 verifiziert) |
| Token-Usage (D2) | **Normal** | Anonymisierung (SET user_id = NULL) + spaeteres DELETE. Ausreichend bei Encryption-at-Rest |
| User-Accounts (D4) | **Normal** | SQL DELETE mit CASCADE |
| Indexierte Dokumente (D8) | **Normal bis Hoch** (abhaengig von Dokumentinhalt) | Vespa `document.remove()` + SQL DELETE. Bei hohem Schutzbedarf: `[KLAERUNG]` VoeB |
| PG-Backups (D11) | **Normal** | Automatische Rotation durch StackIT Managed Service |

### 5.2 Verfahrenshinweise

**PostgreSQL:**
- `DELETE` + Autovacuum gibt Speicherplatz frei und ueberschreibt Datenseiten beim naechsten Schreibvorgang
- Encryption-at-Rest (StackIT AES-256) schuetzt vor physischem Zugriff auf geloeschte Datenreste
- Kein `VACUUM FULL` erforderlich fuer normalen Schutzbedarf
- **KEIN** Column-Level Encryption implementiert (Onyx-Standardverhalten)

**Vespa:**
- `document.remove()` per Document API loescht Embedding + Quelldokument als Einheit
- Keine Re-Indexierung mit geloeschten Dokumenten (Connector-Deletion-Task entfernt Mapping)

**Object Storage (S3):**
- S3 Lifecycle Policies koennen automatische Loeschung nach Frist konfigurieren (`[NICHT IMPLEMENTIERT]`)
- Versionierung beachten: Ohne Ablauf-Policy bleiben alte Versionen bestehen

**Redis:**
- TTL-basierte automatische Bereinigung (Cache + Sessions)
- Kein Backup -- Datenverlust bei Restart hat keine Auswirkung auf persistente Daten

---

## 6. Technischer Umsetzungsplan

| # | Massnahme | Prioritaet | Aufwand | Abhaengigkeit | Loeschklasse |
|---|----------|-----------|---------|--------------|--------------|
| U1 | **Chat-Retention Cronjob** -- Celery Beat Task fuer automatische Loeschung nach 6 Monaten | **HOCH** | 1 PT | Loeschfrist bestaetigt durch VoeB | LK-6M |
| U2 | **Token-Usage Anonymisierung** -- Celery Beat Task: `SET user_id = NULL` nach 12 Monaten | MITTEL | 0,5 PT | Loeschfrist bestaetigt durch VoeB | LK-12M |
| U3 | **Loeschantrag-Prozedur** -- Dokumentierter manueller Prozess + SQL-Skript-Template | MITTEL | 0,5 PT | VoeB-DSB definiert Prozess | Art. 17 |
| U4 | **Account-Deprovisioning** -- Automatisierung bei Entra ID Deaktivierung | NIEDRIG | Teil von ext-rbac (Phase 4f) | Entra ID aktiv + ext-rbac | LK-AKTIV |
| U5 | **S3 Lifecycle Policies** -- Automatische Bereinigung verwaister Dateien | NIEDRIG | 0,5 PT | Connector-Loeschverhalten analysiert | LK-6M |
| U6 | **Loeschprotokoll-Metrik** -- Prometheus Counter fuer durchgefuehrte Loeschvorgaenge | NIEDRIG | 0,25 PT | U1 implementiert | Nachweis |

### 6.1 Implementierungsreihenfolge

```
Phase 1 (vor PROD Go-Live):
  U3 Loeschantrag-Prozedur (dokumentiert, manuell)
  → Minimale DSGVO-Compliance: Betroffenenrechte sind durchsetzbar

Phase 2 (nach Loeschfrist-Bestaetigung durch VoeB):
  U1 Chat-Retention Cronjob
  U2 Token-Usage Anonymisierung
  → Automatisierte Loeschung laeuft

Phase 3 (nach Entra ID Integration):
  U4 Account-Deprovisioning
  → Vollstaendiger Lifecycle

Phase 4 (Optimierung):
  U5 S3 Lifecycle Policies
  U6 Loeschprotokoll-Metrik
```

---

## 7. Sonderfaelle

| # | Sonderfall | Regelung |
|---|-----------|----------|
| S1 | **Mitarbeiter-Austritt** | Account sofort deaktivieren. Loeschung nach Karenzzeit (Empf.: 30 Tage). Chat-Inhalte: regulaere 6-Monats-Frist laeuft weiter |
| S2 | **Art. 17 Loeschantrag** | Prozess gemaess Abschnitt 4.3. Pruefung Art. 17 Abs. 3. Frist: 1 Monat. Bei Aufbewahrungspflicht: Einschraenkung statt Loeschung |
| S3 | **Gesetzliche Aufbewahrungspflicht** | Dokumentieren: welche Datensaetze, warum gesperrt, bis wann. Einschraenkung statt Loeschung (BDSG §35 Abs. 3) |
| S4 | **Backup-Loeschung** | Physische Loeschung in Backups NICHT zwingend (EDSA Feb 2026). Bei PG-Restore aus Backup: Loeschung muss wiederholt werden. Prozess dokumentieren |
| S5 | **Behoerdenanfragen / Litigation Hold** | Loeschstopp fuer betroffene Daten. Nach Verfahrensende: regulaere Loeschung nachholen. VoeB-Recht informieren |
| S6 | **Vektor-Embeddings** | Embedding + Quelldokument = eine Loescheinheit. Keine Re-Indexierung mit geloeschten Dokumenten. Vespa `document.remove()` loescht beides |
| S7 | **Mandantenloesung / Projektende** | Gesamtloeschung aller Daten des Mandanten. Prozess + Frist definieren (`[KLAERUNG]` VoeB). PG Flex: Instanz loeschen. S3: Bucket leeren. Vespa: Namespace loeschen |
| S8 | **Widerruf der Einwilligung** | Derzeit nicht relevant (keine Einwilligungs-basierte Verarbeitung). Falls zukuenftig Einwilligung eingefuehrt: Loeschung ohne ungebuehrliche Verzoegerung |
| S9 | **Zweckwegfall** | Falls Pilotprojekt endet oder Chatbot-Betrieb eingestellt wird: Gesamtloeschung aller personenbezogenen Daten mit definierter Frist |
| S10 | **Shared Chats** | Bei Loeschantrag eines Users: Loeschung der User-Zuordnung, Chat-Inhalt bleibt fuer andere Teilnehmer sichtbar (falls geteilt). `[KLAERUNG]` VoeB |

---

## 8. Nachweispflichten

### 8.1 Loeschprotokoll

Jede Loeschung personenbezogener Daten wird protokolliert:

| Feld | Beschreibung |
|------|-------------|
| Zeitstempel | Datum und Uhrzeit der Loeschung |
| Loeschklasse | LK-6M, LK-12M, etc. |
| Datenart | Chat-Verlaeufe, Token-Usage, etc. |
| Umfang | Anzahl geloeschter/anonymisierter Datensaetze |
| Trigger | Automatisch (Fristablauf) / Manuell (Art. 17 Antrag) / System (Deprovisioning) |
| Durchfuehrende Instanz | System (Cronjob) / Admin (Name) |
| Pruefung Art. 17 Abs. 3 | Entfaellt / Keine Ausnahme / Aufbewahrungspflicht (Begruendung) |

**Speicherort:** `[KLAERUNG]` -- Optionen:
- (a) Eigene PostgreSQL-Tabelle `ext_deletion_log` -- empfohlen, querybar
- (b) Log-Datei im Monitoring -- schwieriger auszuwerten
- (c) Prometheus-Metrik -- nur Zaehler, kein Detail

**Aufbewahrung Loeschprotokoll:** 3 Jahre (Verjaehrungsfrist §195 BGB fuer Schadensersatzansprueche)

### 8.2 Regelmaessige Ueberpruefung

| Pruefung | Intervall | Verantwortlich |
|----------|-----------|---------------|
| Loeschfristen eingehalten? | Quartalsweise | CCJ (System-Admin) |
| Loeschprotokoll vollstaendig? | Quartalsweise | VoeB-DSB |
| Neue Datenarten identifiziert? | Bei jedem Release mit neuen Datenstrukturen | CCJ (Entwickler) |
| Backup-Restore-Test: Loeschung wird wiederholt? | Jaehrlich | CCJ + VoeB |

---

## 9. Offene Punkte (Zusammenfassung aller `[KLAERUNG]`-Marker)

| # | Punkt | Entscheider | Kontext |
|---|-------|------------|---------|
| K1 | **Token-Usage Aufbewahrungsfrist** -- 12 Monate akzeptabel? | VoeB | ~100k Rows/Monat, Anonymisierung (nicht Loeschung) nach Frist. Fuer Jahresberichte und Kostenanalyse benoetigt |
| K2 | **Chat-Retention: Soft-Delete + Grace Period oder Hard-Delete?** | VoeB | Empfehlung: Soft-Delete bei 6 Monaten, Hard-Delete bei 7 Monaten (30 Tage Recovery-Fenster) |
| K3 | **Deprovisioning-Karenzzeit** -- 30 Tage akzeptabel? | VoeB | Bei Mitarbeiter-Austritt: sofort deaktivieren, nach 30 Tagen loeschen |
| K4 | **Loeschantrag-Prozess: Manuell oder Self-Service?** | VoeB-DSB | Empfehlung: Manuell (geringes Volumen), Self-Service erst bei >500 Usern |
| K5 | **Indexierte Dokumente: Eigene Loeschfrist?** | VoeB | Abhaengig von Dokumentquelle und Inhalt. Aktuell: manuell via Connector-Loeschung |
| K6 | **Object Storage Lifecycle Policies** | VoeB + CCJ | Automatische Bereinigung verwaister Dateien konfigurieren |
| K7 | **StackIT Backup-Retention: Exakte Policy?** | StackIT / VoeB | PG Flex Managed Backup -- geschaetzt 30 Tage, exakte Policy verifizieren |
| K8 | **Shared Chats: Loeschverhalten bei Art. 17 Antrag** | VoeB-DSB | User-Zuordnung loeschen vs. gesamten Chat loeschen |
| K9 | **Loeschprotokoll-Speicherort** | CCJ + VoeB | Empfehlung: `ext_deletion_log` PostgreSQL-Tabelle |
| K10 | **VoeB-DSB: Wer ist der Datenschutzbeauftragte?** | VoeB | Wird fuer Art. 17 Prozess und DSFA-Konsultation benoetigt |

---

## 10. Referenzen

| Dokument | Pfad / Quelle |
|----------|---------------|
| Compliance-Research (Regulatorik-Grundlagen) | `docs/referenz/compliance-research.md` |
| Sicherheitskonzept (TOMs, Verschluesselung, Auth) | `docs/sicherheitskonzept.md` |
| Betriebskonzept (Backup, Infrastruktur, Monitoring) | `docs/betriebskonzept.md` |
| ext-token Modulspezifikation (Token-Usage Schema) | `docs/technisches-feinkonzept/ext-token.md` |
| Monitoring-Konzept (Prometheus Retention, Alerting) | `docs/referenz/monitoring-konzept.md` |
| DIN EN ISO/IEC 27555:2025-09 | Norm (ersetzt DIN 66398:2016-05) |
| EDSA Feb 2026 (Backup-Loeschung) | `https://www.bits.gmbh/loeschung-von-personenbezogenen-daten-in-backups-das-ende-eines-jahrelangen-dsgvo-dilemmas/` |
| DSK Muss-Liste V1.1 | `https://www.datenschutzkonferenz-online.de/media/ah/20181017_ah_DSK_DSFA_Muss-Liste_Version_1.1_Deutsch.pdf` |
| BSI CON.6 (Loeschmethoden nach Schutzbedarf) | BSI IT-Grundschutz Kompendium Edition 2023 |
| BankingHub Loeschkonzept | `https://bankinghub.de/innovation-digital/loeschkonzept-eu-dsgvo` |

---

*Erstellt: 2026-03-14 | Methode: Analyse von Compliance-Research, Betriebs- und Sicherheitskonzept, ext-token Modulspezifikation, Monitoring-Konzept, Onyx DB-Schema*
