# VERZEICHNIS VON VERARBEITUNGSTAETIGKEITEN -- ENTWURF

**Rechtsgrundlage:** Art. 30 Abs. 1 DSGVO
**Status:** ENTWURF -- Abstimmung mit VÖB ausstehend
**Version:** 0.1
**Datum:** 2026-03-14
**Autor:** COFFEESTUDIOS (CCJ Development UG)

> **Hinweis:** Dieses VVT bezieht sich ausschließlich auf die Verarbeitungstätigkeiten des VÖB Service Chatbot-Systems. Es ersetzt nicht ein ggf. bereits bestehendes unternehmensweites VVT der VÖB Service GmbH, sondern ergänzt dieses um die chatbot-spezifischen Verarbeitungen. Felder die von VÖB zu befüllen sind, sind mit `[VÖB]` markiert. Klärungsbedarf ist mit `[KLÄRUNG]` gekennzeichnet.

---

## Änderungshistorie

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|------------|
| 0.1 | 2026-03-14 | COFFEESTUDIOS (CCJ) | Initialer Entwurf auf Basis Sicherheitskonzept v0.6, Betriebskonzept v0.6, Compliance-Research (2026-03-09) |

---

## 1. Angaben zum Verantwortlichen (Art. 30 Abs. 1 S. 2 lit. a)

| Feld | Wert |
|------|------|
| Name des Verantwortlichen | VÖB Service GmbH |
| Anschrift | `[VÖB -- Adresse einfügen]` |
| Gesetzlicher Vertreter | `[VÖB -- Name des Geschäftsführers einfügen]` |
| Datenschutzbeauftragter (DSB) | `[VÖB -- Name und Kontaktdaten des DSB einfügen]` |
| Kontakt DSB | `[VÖB -- E-Mail und Telefon des DSB einfügen]` |

> **Offener Punkt:** Der VÖB-DSB muss gemäß Art. 35 Abs. 2 DSGVO auch während der parallel laufenden DSFA konsultiert werden.

---

## 2. Verarbeitungstätigkeiten

### 2.1 Chat-Verarbeitung (Kernfunktion)

| Feld | Inhalt |
|------|--------|
| **Bezeichnung** | KI-gestützte Chat-Verarbeitung (Frage-Antwort-System) |
| **Zweck** | Bereitstellung eines KI-Chatbots für interne Wissensabfragen und Informationsabruf durch VÖB-Mitarbeiter. Effizienzsteigerung bei der internen Informationsrecherche. |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse). `[KLÄRUNG -- VÖB-DSB]` Drei-Stufen-Test: (1) Berechtigtes Interesse an KI-gestütztem Informationsabruf zur Effizienzsteigerung, (2) Verarbeitung von Identität und Chat-Inhalt ist für Chatbot-Service erforderlich, (3) Maßnahmen (Datenminimierung, Zugriffskontrolle, Löschfristen, kein Performance-Monitoring) kippen Interessenabwägung zugunsten VÖB. NICHT Art. 6 Abs. 1 lit. b (kein vertraglicher Zwang zur Nutzung) und NICHT Art. 6 Abs. 1 lit. e (VÖB ist privatrechtlicher Verein). |
| **Kategorien betroffener Personen** | VÖB-Mitarbeiter (~150 Personen), die den Chatbot nutzen |
| **Kategorien personenbezogener Daten** | (1) **Konversationsdaten:** Chat-Nachrichten (User-Prompts), KI-generierte Antworten, Konversationsverläufe, Konversations-Metadaten (Zeitstempel, Session-ID, Konversations-ID). (2) **Identitätsdaten im Kontext:** User-ID (E-Mail-Adresse), Zuordnung Chat-Session zu Benutzer. (3) **System Prompts:** Admin-konfigurierte Anweisungen an das LLM (ext-prompts Modul). |
| **Empfänger** | (1) StackIT AI Model Serving (LLM-Verarbeitung, EU01 Frankfurt) -- Chat-Nachrichten werden als Prompt an das LLM übermittelt. (2) Onyx-Backend (Verarbeitung und Speicherung). (3) Administratoren (CCJ, ggf. VÖB-Admins) -- Einsicht in Konversationsdaten über Admin-UI. |
| **Drittlandübermittlung** | **NEIN.** LLM-Verarbeitung erfolgt ausschließlich über StackIT AI Model Serving (Region EU01, Frankfurt am Main, Deutschland). Kein OpenAI, kein US-Provider. StackIT / Schwarz IT KG ist ein deutscher Anbieter mit BSI C5 Type 2 Zertifizierung. |
| **Löschfristen** | `[LÖSCHKONZEPT -- VÖB-DSB]` Empfehlung (Compliance-Research): Konversationsdaten 12 Monate (Bankenkontext rechtfertigt längere Nachweisbarkeit). Branchenüblich: 90 Tage bis 12 Monate. Endgültige Frist durch VÖB festzulegen. |
| **TOMs** | Siehe Sicherheitskonzept v0.6, Abschnitte: Datenverschlüsselung (TLSv1.3 in Transit, AES-256 at Rest), Netzwerksicherheit (NetworkPolicies, PG ACL), API-Sicherheit (Pydantic Input-Validierung), Authentifizierung (aktuell Basic Auth, geplant Entra ID OIDC). |

**Datenfluss:**
```
Benutzer (Browser)
  → HTTPS/TLSv1.3 → NGINX Ingress
    → Onyx Web Server (Next.js)
      → Onyx API Server (FastAPI)
        → PostgreSQL (Konversation speichern)
        → Vespa (RAG-Kontext abrufen)
        → StackIT AI Model Serving (LLM-Prompt senden, Antwort empfangen)
        → PostgreSQL (Antwort speichern)
      ← Antwort an Benutzer (Streaming)
```

---

### 2.2 Token-Usage-Tracking (ext-token Modul)

| Feld | Inhalt |
|------|--------|
| **Bezeichnung** | LLM-Nutzungserfassung und Kostenkontrolle (ext-token) |
| **Zweck** | (1) Kostenkontrolle: Erfassung des LLM-Token-Verbrauchs (Input- und Output-Tokens) pro Anfrage zur Vermeidung unkontrollierter LLM-Kosten. (2) Quota-Management: Pre-Request-Prüfung von Nutzungslimits (Hard Stops bei Überschreitung). (3) Nutzungsübersicht: Aggregierte Statistiken (Timeline, Per-User, Per-Model) für Administratoren. |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an Kostenkontrolle und Missbrauchsprävention). `[KLÄRUNG -- VÖB-DSB]` Alternativ: Art. 6 Abs. 1 lit. f in Verbindung mit Betriebsvereinbarung (falls vorhanden). Hinweis: Token-Tracking dient der Kostenkontrolle, NICHT der Leistungsüberwachung von Mitarbeitern. |
| **Kategorien betroffener Personen** | VÖB-Mitarbeiter, die den Chatbot nutzen |
| **Kategorien personenbezogener Daten** | (1) **Nutzungsmetriken:** Anzahl Input-Tokens, Anzahl Output-Tokens pro Request. (2) **Zuordnungsdaten:** User-ID (E-Mail-Adresse, aufgelöst zu UUID), Modell-ID, Zeitstempel. (3) **Aggregierte Daten:** Gesamtverbrauch pro Benutzer, pro Modell, pro Zeitraum. |
| **Empfänger** | (1) Administratoren (CCJ, VÖB-Admins) über Admin-Dashboard (Usage-Übersicht). (2) System-intern: Pre-Request Quota-Prüfung. |
| **Drittlandübermittlung** | **NEIN.** Alle Daten verbleiben in PostgreSQL auf StackIT (EU01 Frankfurt). |
| **Löschfristen** | `[LÖSCHKONZEPT -- VÖB-DSB]` Empfehlung: Detaillierte Token-Logs 12 Monate (analog Konversationsdaten). Aggregierte Statistiken können länger aufbewahrt werden (kein Personenbezug nach Aggregation). |
| **TOMs** | Zugriffskontrolle: Admin-only Dashboard (`Depends(current_admin_user)`). Datenminimierung: Nur Token-Zähler, kein Inhalt der Nachrichten. Speicherung in PostgreSQL (verschlüsselt at Rest, AES-256). Siehe Sicherheitskonzept v0.6. |

**Hinweis Beschäftigtendatenschutz:** Per-User Token-Tracking kann als Beschäftigtenüberwachung interpretiert werden. Empfehlung: (1) Betriebsrat/Personalvertretung informieren (falls vorhanden), (2) Zweckbindung auf Kostenkontrolle dokumentieren, (3) Keine Verwendung für Leistungsbeurteilung. `[KLÄRUNG -- VÖB]`

---

### 2.3 Authentifizierung und Autorisierung

| Feld | Inhalt |
|------|--------|
| **Bezeichnung** | Benutzerauthentifizierung und Sitzungsverwaltung |
| **Zweck** | (1) Identifizierung und Authentifizierung der Benutzer für den Zugang zum Chatbot. (2) Sitzungsverwaltung (Session-Management) zur Aufrechterhaltung des Anmeldestatus. (3) Rollenbasierte Zugriffskontrolle (RBAC) zur Unterscheidung von Berechtigungsstufen (admin, basic, curator etc.). |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an der Sicherung des Systems gegen unbefugten Zugriff). `[KLÄRUNG -- VÖB-DSB]` |
| **Kategorien betroffener Personen** | VÖB-Mitarbeiter mit Chatbot-Zugang, Administratoren (CCJ, VÖB) |
| **Kategorien personenbezogener Daten** | (1) **Identitätsdaten:** Name, E-Mail-Adresse. (2) **Authentifizierungsdaten:** Passwort-Hash (aktuell, Basic Auth) bzw. OIDC-Token (geplant, Entra ID). (3) **Sitzungsdaten:** Session-Cookies (technisch notwendig, TDDDG Paragraph 25 -- keine Einwilligung erforderlich), Session-ID, Ablaufzeitpunkt. (4) **Autorisierungsdaten:** Zugewiesene Rolle (admin, basic, curator etc.), Berechtigungsprofil. (5) **Login-Metadaten:** Login-Zeitpunkt, IP-Adresse (in Server-Logs). |
| **Empfänger** | (1) Onyx-Backend (Authentifizierungsprüfung). (2) Microsoft Entra ID (geplant, Phase 3) -- OIDC Authorization Code Flow. (3) Administratoren (Benutzerverwaltung über Admin-UI). |
| **Drittlandübermittlung** | **NEIN.** Aktuell: Onyx-interne Authentifizierung (PostgreSQL auf StackIT EU01). Geplant: Microsoft Entra ID -- `[KLÄRUNG -- VÖB]` Standort des Entra ID Tenants prüfen. Microsoft betreibt Entra ID in EU-Rechenzentren (EU Data Boundary), dies muss im Rahmen der Entra-ID-Integration verifiziert werden. |
| **Löschfristen** | `[LÖSCHKONZEPT -- VÖB-DSB]` Empfehlung: Identitätsdaten (Accounts) -- Beschäftigungsdauer + 3 Jahre (Paragraph 195 BGB Verjährung). Sitzungsdaten -- 24h nach Session-Ende. Login-Logs -- 90 Tage (Standard) bzw. 6-12 Monate (Security-/Audit-Logs). Bei Mitarbeiter-Austritt: Account sofort deaktivieren, Löschung nach definierter Frist (Empfehlung: 30 Tage). |
| **TOMs** | Passwort-Hashing (bcrypt, Onyx-Standard), Session-Cookie-basierte Authentifizierung, HTTPS/TLSv1.3 für Credential-Übertragung, Rollenbasierte Zugriffskontrolle (7 Onyx-native Rollen), Geplant: Entra ID OIDC mit MFA. Siehe Sicherheitskonzept v0.6, Abschnitt Authentifizierung. |

---

### 2.4 System-Monitoring und Alerting

| Feld | Inhalt |
|------|--------|
| **Bezeichnung** | Infrastruktur-Monitoring, Metriken-Erfassung und Alerting |
| **Zweck** | (1) Sicherstellung der Systemverfügbarkeit durch kontinuierliche Überwachung aller Komponenten (API, Datenbank, Redis, Kubernetes). (2) Frühzeitige Erkennung von Störungen und Sicherheitsvorfällen. (3) Kapazitätsplanung und Performance-Optimierung. (4) Alerting an Betriebsteam bei Schwellenwertüberschreitungen. |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an der Aufrechterhaltung der IT-Sicherheit und Systemverfügbarkeit -- Erwägungsgrund 49 DSGVO). `[KLÄRUNG -- VÖB-DSB]` |
| **Kategorien betroffener Personen** | Indirekt: VÖB-Mitarbeiter (deren Nutzung sich in aggregierten Metriken widerspiegelt). Direkt: Betriebsteam (CCJ), das Alerts empfängt. |
| **Kategorien personenbezogener Daten** | (1) **Technische Metriken (kein direkter Personenbezug):** CPU-/RAM-Auslastung, Pod-Status, Datenbankverbindungen, Redis-Verbindungen, HTTP-Statuscodes, Antwortzeiten. (2) **Server-Logs (potenziell personenbezogen):** IP-Adressen in Access-Logs, Timestamps, Request-URLs (können User-IDs enthalten). (3) **Alert-Daten:** Schwellenwert-Überschreitungen, Fehlermeldungen -- an Microsoft Teams Webhook übermittelt. |
| **Empfänger** | (1) Prometheus (Metriken-Speicherung, in-cluster). (2) Grafana (Visualisierung, in-cluster). (3) AlertManager → Microsoft Teams (Alerts an Betriebsteam-Kanal). (4) Betriebsteam CCJ (Zugriff auf Grafana-Dashboards). |
| **Drittlandübermittlung** | **NEIN.** Prometheus, Grafana und AlertManager laufen in-cluster auf StackIT (EU01 Frankfurt). Microsoft Teams Webhook: `[KLÄRUNG -- VÖB]` Der Teams-Webhook-Endpunkt liegt in der Microsoft-Cloud. Alert-Nachrichten enthalten keine personenbezogenen Daten (nur technische Metriken und Schwellenwerte), daher kein DSGVO-relevanter Datentransfer. Dennoch: Standort des Teams-Tenants mit VÖB verifizieren (Microsoft EU Data Boundary). |
| **Löschfristen** | Metriken (Prometheus): 90 Tage Retention (DEV/TEST), 90 Tage (PROD, konfiguriert in values-monitoring-prod.yaml). Server-Logs: K8s-native Log-Rotation (Container-Lifetime). `[LÖSCHKONZEPT]` |
| **TOMs** | Monitoring-Namespace mit 7/8 NetworkPolicies (Zero-Trust), Zugriff auf Grafana nur über kubectl port-forward (kein externer Zugang), Metriken enthalten keine Chat-Inhalte, AlertManager-Webhook über HTTPS. Siehe Sicherheitskonzept v0.6 und Monitoring-Konzept (`docs/referenz/monitoring-konzept.md`). |

---

### 2.5 Dokumenten-Indexierung (RAG)

| Feld | Inhalt |
|------|--------|
| **Bezeichnung** | Dokumenten-Indexierung und Retrieval-Augmented Generation (RAG) |
| **Zweck** | (1) Indexierung von internen VÖB-Dokumenten für die wissensbasierte Suche. (2) Umwandlung von Dokumenten in Vektor-Embeddings für semantische Suche. (3) Bereitstellung relevanter Dokumentenausschnitte als Kontext für LLM-Antworten (RAG-Pipeline). |
| **Rechtsgrundlage** | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an effizientem internen Wissensmanagement). `[KLÄRUNG -- VÖB-DSB]` Falls Dokumente personenbezogene Daten enthalten (z.B. Mitarbeiterlisten, Organigramme), muss die Rechtsgrundlage für die Verarbeitung dieser Inhalte separat geprüft werden. |
| **Kategorien betroffener Personen** | (1) VÖB-Mitarbeiter, die Dokumente hochladen. (2) In Dokumenten genannte Personen (VÖB-Mitarbeiter, externe Kontakte) -- abhängig vom Dokumenteninhalt. `[KLÄRUNG -- VÖB]` Welche Dokumententypen werden indexiert? Enthalten diese personenbezogene Daten? |
| **Kategorien personenbezogener Daten** | (1) **Dokument-Metadaten:** Dateiname, Upload-Zeitpunkt, Uploader (User-ID), Quelle (Connector-Typ). (2) **Dokumenteninhalte:** Volltextinhalte der hochgeladenen/verbundenen Dokumente -- Personenbezug abhängig vom Inhalt. (3) **Vektor-Embeddings:** Mathematische Repräsentationen der Dokumenteninhalte (Qwen3-VL-Embedding 8B, 4096 Dimensionen). (4) **Chunk-Daten:** Aufgeteilte Textabschnitte mit Kontextinformationen. |
| **Empfänger** | (1) Onyx Model Server (Embedding-Berechnung, in-cluster). (2) Vespa (Vektor-Speicherung und -Suche, in-cluster). (3) StackIT Object Storage (Originaldateien, S3-Buckets: vob-dev, vob-test, vob-prod). (4) PostgreSQL (Dokument-Metadaten). |
| **Drittlandübermittlung** | **NEIN.** Embedding-Berechnung erfolgt durch den Onyx Model Server (in-cluster auf StackIT EU01). Vespa läuft in-cluster. Object Storage bei StackIT (EU01 Frankfurt). Kein externer Embedding-Service. |
| **Löschfristen** | `[LÖSCHKONZEPT -- VÖB-DSB]` Empfehlung: Quelldokument-Lebensdauer + 30 Tage (dann Löschung aus Vespa, Object Storage und PostgreSQL). Embedding + Quelldokument = eine Löscheinheit. Keine Re-Indexierung mit gelöschten Dokumenten. Gesetzliche Aufbewahrungspflichten (HGB Paragraph 257, AO Paragraph 147) gelten für Chatbot-Dokumente im Regelfall NICHT (kein Buchungsbeleg, kein Handelsbrief) -- Originale verbleiben im DMS. |
| **TOMs** | Zugriffssteuerung über Onyx-native Berechtigungen (Dokument-Sichtbarkeit), Verschlüsselung at Rest (StackIT AES-256 für Object Storage und PersistentVolumes), NetworkPolicies (Vespa nur cluster-intern erreichbar), Input-Validierung (Pydantic). Geplant: ext-access Modul für dokumentenbasierte Zugriffskontrolle (Phase 4g, blockiert durch Entra ID). Siehe Sicherheitskonzept v0.6. |

**Datenfluss (Indexierung):**
```
Dokument-Upload / Connector-Sync
  → Celery Worker (docfetching)
    → Celery Worker (docprocessing)
      → PostgreSQL (Dokument-Metadaten upsert)
      → Onyx Model Server (Embedding-Berechnung, in-cluster)
      → Vespa (Chunks + Embeddings speichern)
      → Object Storage (Originaldatei speichern)
```

**Datenfluss (RAG-Abfrage):**
```
Benutzer-Frage
  → Onyx API Server
    → Onyx Model Server (Query-Embedding berechnen)
    → Vespa (Semantische Suche, Top-K Chunks abrufen)
    → StackIT AI Model Serving (LLM-Prompt mit Kontext senden)
  ← Antwort mit Quellenverweisen
```

---

## 3. Auftragsverarbeiter (Art. 30 Abs. 1 S. 2 lit. d, Art. 28 DSGVO)

| Auftragsverarbeiter | Leistung | Standort | Verarbeitete Daten | AVV-Status |
|---------------------|----------|----------|-------------------|------------|
| **StackIT / Schwarz IT KG** | Cloud-Infrastruktur: Kubernetes (SKE), PostgreSQL Flex (Managed DB), Object Storage (S3), AI Model Serving (LLM-Inferenz) | EU01, Frankfurt am Main, Deutschland | Alle Datenkategorien (Identitäts-, Konversations-, Dokumentendaten, Metriken) | `[AVV -- Status klären mit VÖB]` Ein AVV nach Art. 28 DSGVO ist gesetzlich vorgeschrieben. StackIT besitzt BSI C5 Type 2 Zertifizierung. |
| **CCJ Development UG (COFFEESTUDIOS)** | Softwareentwicklung, Betrieb und Wartung des Chatbot-Systems (DevOps) | Deutschland | Alle Datenkategorien (Zugriff auf alle Systeme für Entwicklung und Betrieb) | `[AVV -- Status klären mit VÖB]` Ein AVV nach Art. 28 DSGVO ist gesetzlich vorgeschrieben. |

### Unterauftragsverarbeiter

| Unterauftragsverarbeiter | Beauftragt durch | Leistung | Standort |
|--------------------------|-----------------|----------|----------|
| StackIT / Schwarz IT KG | CCJ (im Auftrag von VÖB) | Cloud-Infrastruktur und LLM-Hosting | EU01, Frankfurt |

> **Hinweis:** Es besteht **kein** Vertragsverhältnis mit OpenAI, Google, Anthropic oder anderen externen LLM-Providern. Die gesamte KI-Verarbeitung erfolgt ausschließlich über StackIT AI Model Serving (self-hosted Modelle: GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, Llama 3.1 8B).

---

## 4. Drittlandübermittlung (Art. 30 Abs. 1 S. 2 lit. e, Art. 44-49 DSGVO)

**Ergebnis: KEINE Drittlandübermittlung.**

| Datenverarbeitung | Verarbeitungsort | Drittland? | Bewertung |
|-------------------|-----------------|------------|-----------|
| LLM-Inferenz (Chat) | StackIT AI Model Serving, EU01 Frankfurt | NEIN | Self-hosted Modelle, kein API-Call an US-Provider |
| Datenbank (PostgreSQL) | StackIT Managed PG Flex, EU01 Frankfurt | NEIN | Managed Service in Deutschland |
| Vektor-Suche (Vespa) | In-cluster, StackIT SKE, EU01 Frankfurt | NEIN | Läuft als Pod im Kubernetes-Cluster |
| Object Storage (S3) | StackIT Object Storage, EU01 Frankfurt | NEIN | Endpoint: `object.storage.eu01.onstackit.cloud` |
| Embedding-Berechnung | Onyx Model Server, in-cluster, StackIT SKE | NEIN | Lokale Berechnung, kein externer Service |
| Monitoring (Prometheus/Grafana) | In-cluster, StackIT SKE, EU01 Frankfurt | NEIN | Läuft als Pods im Kubernetes-Cluster |
| Alerting (Teams Webhook) | Microsoft Teams | `[KLÄRUNG]` | Alert-Nachrichten enthalten keine personenbezogenen Daten (nur technische Metriken). Microsoft EU Data Boundary prüfen. |
| Authentifizierung (geplant) | Microsoft Entra ID | `[KLÄRUNG]` | Phase 3 (noch nicht implementiert). EU Data Boundary für Entra ID Tenant verifizieren. |
| Container Images (Pull) | Docker Hub (Upstream Model Server) | Technisch JA | Nur Image-Download (keine personenbezogenen Daten). Docker Hub Standort: USA. Kein DSGVO-relevanter Transfer. |

**Zusammenfassung:** Alle personenbezogenen Daten werden ausschließlich innerhalb der EU (Deutschland, StackIT Region EU01 Frankfurt) verarbeitet und gespeichert. Kein Angemessenheitsbeschluss, keine SCCs und keine sonstigen Transfergarantien nach Art. 46 DSGVO erforderlich.

---

## 5. Technische und organisatorische Maßnahmen -- TOMs (Art. 30 Abs. 1 S. 2 lit. g i.V.m. Art. 32 DSGVO)

Die vollständige TOM-Dokumentation befindet sich im **Sicherheitskonzept v0.6** (`docs/sicherheitskonzept.md`). Nachfolgend eine Zusammenfassung der wesentlichen Maßnahmen:

### 5.1 Vertraulichkeit

| Maßnahme | Status | Details |
|----------|--------|---------|
| Verschlüsselung in Transit | IMPLEMENTIERT (DEV+TEST), AUSSTEHEND (PROD) | TLSv1.3, ECDSA P-384, HTTP/2 (BSI TR-02102-2 konform). PROD wartet auf DNS-Einträge. |
| Verschlüsselung at Rest | IMPLEMENTIERT | StackIT Default AES-256 für PostgreSQL, Object Storage und PersistentVolumes (SEC-07 verifiziert). |
| Zugriffskontrolle (Authentifizierung) | TEILWEISE | Onyx Basic Auth aktiv (DEV/TEST/PROD temporär). Entra ID OIDC geplant (Phase 3). |
| Netzwerk-Isolation | IMPLEMENTIERT (DEV+TEST), AUSSTEHEND (PROD) | Kubernetes NetworkPolicies (Zero-Trust): 5 Policies in App-NS, 8 Policies in Monitoring-NS. PROD App-NS ausstehend. |
| Datenbank-ACL | IMPLEMENTIERT | PostgreSQL-Zugriff auf Cluster-Egress-IP eingeschränkt (SEC-01). |
| Geheimnismanagement | IMPLEMENTIERT | Kubernetes Secrets + GitHub Actions Secrets (environment-getrennt). |
| Container-Härtung | IMPLEMENTIERT | `runAsNonRoot: true` auf allen Environments (SEC-06 Phase 2). Vespa = dokumentierte Ausnahme. |

### 5.2 Integrität

| Maßnahme | Status | Details |
|----------|--------|---------|
| Input-Validierung | IMPLEMENTIERT | Pydantic-Modelle für alle API-Endpunkte (FastAPI). |
| CI/CD Supply-Chain | IMPLEMENTIERT | SHA-gepinnte GitHub Actions, Branch Protection auf main, 3 Status Checks. |
| Datei-Upload-Validierung | IMPLEMENTIERT | Magic-Byte-Validierung (kein SVG/XSS), 2 MB Limit (ext-branding Logo). |
| Security-Header | IMPLEMENTIERT | X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS. |

### 5.3 Verfügbarkeit

| Maßnahme | Status | Details |
|----------|--------|---------|
| Hochverfügbarkeit | IMPLEMENTIERT (PROD) | 2x API HA, 2x Web HA, PG Flex 4.8 HA (3-Node). |
| Datenbank-Backup | IMPLEMENTIERT | Tägliches Backup (StackIT Managed), Point-in-Time Recovery (PROD). |
| Monitoring und Alerting | IMPLEMENTIERT | kube-prometheus-stack (alle Cluster), AlertManager → Teams. 20 Alert-Rules. |
| Health Probes | IMPLEMENTIERT | API httpGet `/health:8080`, Webserver tcpSocket `:3000`. |

### 5.4 Belastbarkeit und Wiederherstellbarkeit

| Maßnahme | Status | Details |
|----------|--------|---------|
| Incident-Response-Plan | IMPLEMENTIERT | 6-Phasen-Plan (Erkennung → Nachbereitung), Eskalationsstufen P1-P3. |
| Rollback-Verfahren | IMPLEMENTIERT | Helm Rollback, DB-Rollback dokumentiert. Runbook: `docs/runbooks/rollback-verfahren.md`. |
| Kubernetes Auto-Restart | IMPLEMENTIERT | Pod-Restart bei Crash, Recreate-Strategie für Deployments. |

> **Vollständige TOM-Dokumentation:** `docs/sicherheitskonzept.md` (Sicherheitskonzept v0.6)

---

## 6. Allgemeine Beschreibung der technischen und organisatorischen Sicherheitsmaßnahmen (Art. 30 Abs. 1 S. 2 lit. g)

### Infrastruktur-Sicherheit

- **Cloud-Provider:** StackIT / Schwarz IT KG (BSI C5 Type 2 zertifiziert)
- **Region:** EU01 Frankfurt am Main, Deutschland (Datensouveränität)
- **Kubernetes:** SKE (StackIT Kubernetes Engine), K8s v1.33.8/v1.33.9, Flatcar OS
- **Cluster-Trennung:** PROD auf eigenem Cluster (`vob-prod`), DEV/TEST auf shared Cluster (`vob-chatbot`)
- **NetworkPolicies:** Zero-Trust-Ansatz (Default-Deny + explizite Allow-Rules)
- **Container Security:** `runAsNonRoot: true`, keine privilegierten Container (Vespa = dokumentierte Ausnahme)

### Organisatorische Maßnahmen

- **Entwicklungsprozess:** Feature-Branch-Workflow, Branch Protection, CI/CD mit 3 Status Checks
- **Change Management:** Dokumentierte Checkliste vor jedem Commit, CHANGELOG-Pflicht
- **PROD-Deployment:** GitHub Environment Protection mit Required Reviewer
- **Dokumentation:** Sicherheitskonzept, Betriebskonzept, ADRs, Runbooks

---

## 7. Offene Punkte und nächste Schritte

| # | Punkt | Verantwortlich | Priorität |
|---|-------|---------------|-----------|
| 1 | VÖB-DSB benennen und in VVT eintragen | VÖB | HOCH |
| 2 | Rechtsgrundlage (Art. 6 Abs. 1 lit. f) durch VÖB-DSB bestätigen lassen | VÖB-DSB | HOCH |
| 3 | Aufbewahrungsfristen / Löschfristen final festlegen (Löschkonzept) | VÖB-DSB + CCJ | HOCH |
| 4 | AVV mit StackIT abschließen (Art. 28 DSGVO) | VÖB + StackIT | HOCH |
| 5 | AVV mit CCJ Development UG abschließen (Art. 28 DSGVO) | VÖB + CCJ | HOCH |
| 6 | Klären: Welche Dokumententypen werden indexiert? Enthalten diese PII? | VÖB | MITTEL |
| 7 | Klären: Microsoft Teams Webhook / Entra ID -- EU Data Boundary verifizieren | VÖB IT | MITTEL |
| 8 | Klären: Betriebsvereinbarung für Token-Usage-Tracking erforderlich? | VÖB (BR/PV) | MITTEL |
| 9 | VVT-Status in Sicherheitskonzept von GEPLANT auf ENTWURF aktualisieren | CCJ | NIEDRIG |
| 10 | VVT nach VÖB-Freigabe auf Version 1.0 heben | CCJ + VÖB | NACH FREIGABE |

---

## 8. Querverweise

| Dokument | Pfad | Relevanz |
|----------|------|----------|
| Sicherheitskonzept v0.6 | `docs/sicherheitskonzept.md` | TOMs, Datenschutz-Abschnitt, PII-Kategorien |
| Betriebskonzept v0.6 | `docs/betriebskonzept.md` | Systemarchitektur, Datenflüsse, Komponenten |
| Compliance-Research | `docs/referenz/compliance-research.md` | Regulatorische Einordnung, DSFA-Pflicht, Löschfristen |
| Monitoring-Konzept | `docs/referenz/monitoring-konzept.md` | Monitoring-Stack, Alerting, Metriken |
| RBAC-Rollenmodell | `docs/referenz/rbac-rollenmodell.md` | Geplantes Berechtigungskonzept |
| EE/FOSS-Abgrenzung | `docs/referenz/ee-foss-abgrenzung.md` | Lizenz-Abgrenzung, Extension-Module |

---

*Erstellt: 2026-03-14 | Autor: COFFEESTUDIOS (CCJ Development UG) | Basiert auf: Sicherheitskonzept v0.6, Betriebskonzept v0.6, Compliance-Research 2026-03-09*
