# DATENSCHUTZ-FOLGENABSCHAETZUNG -- ENTWURF

## VÖB Service Chatbot (KI-gestützter Chatbot für interne Wissensbasis)

| Feld | Wert |
|------|------|
| **Version** | 0.1 |
| **Datum** | 2026-03-14 |
| **Status** | ENTWURF -- Freigabe durch VÖB-DSB ausstehend |
| **Verantwortlicher** | VÖB Service GmbH (Verantwortlicher i.S.d. Art. 4 Nr. 7 DSGVO) |
| **Erstellt durch** | CCJ Development UG (Coffee Studios), Nikolaj Ivanov |
| **Datenschutzbeauftragter** | [VÖB-DSB] |
| **Nächste Überprüfung** | [VÖB-DSB] -- spätestens 12 Monate nach Freigabe oder bei wesentlicher Systemänderung |
| **Rechtsgrundlage DSFA** | Art. 35 DSGVO |

---

## Änderungshistorie

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|------------|
| 0.1 | 2026-03-14 | Nikolaj Ivanov (CCJ) | Initialer Entwurf auf Basis Sicherheitskonzept v0.6, Betriebskonzept v0.6, Compliance-Research (2026-03-09) |

---

## 0. Schwellenwertanalyse (Vorabprüfung)

### Warum ist eine DSFA erforderlich?

Eine DSFA nach Art. 35 DSGVO ist für den VÖB Service Chatbot **gesetzlich vorgeschrieben**. Es liegen drei unabhängige Trigger vor:

**Trigger 1 -- DSK Muss-Liste Nr. 10** (V1.1, 17.10.2018):
> "Einsatz von künstlicher Intelligenz zur Verarbeitung personenbezogener Daten zur Steuerung der Interaktion mit den Betroffenen"

Der VÖB Service Chatbot ist ein KI-System (LLM-basiert), das personenbezogene Daten verarbeitet (Chat-Eingaben, Nutzungsprofile) und die Interaktion mit Betroffenen (VÖB-Mitarbeitern) steuert. Dieser Trigger ist direkt erfüllt.

**Trigger 2 -- Art. 35 Abs. 1 DSGVO ("neue Technologien"):**
Large Language Models (LLMs) und Generative AI qualifizieren als "neue Technologien" im Sinne des Art. 35 Abs. 1. Die systematische Verarbeitung von Chat-Konversationen durch KI-Modelle birgt spezifische Risiken für die Rechte und Freiheiten natürlicher Personen.

**Trigger 3 -- EDPB/WP248 Kriterien** (mindestens 2 von 9 = DSFA nötig):

| Kriterium | Erfüllt? | Begründung |
|-----------|----------|------------|
| (a) Innovative Technologie | Ja | LLM/Generative AI |
| (b) Systematisches Monitoring | Ja | Chat-Logging, Token-Tracking pro User |
| (c) Machtgefälle | Ja | Arbeitgeber-Tool, eingeschränkte Verweigerungsmöglichkeit für Mitarbeiter |

Drei von neun Kriterien sind erfüllt (Schwelle: 2). Die DSFA-Pflicht ist damit eindeutig gegeben.

**Hinweis:** Die ursprüngliche Kickoff-Einschätzung "DSFA nicht relevant" (2026-02) wurde durch den Dokumentations-Audit (2026-03-14) korrigiert.

---

## 1. Systematische Beschreibung der Verarbeitung (Art. 35 Abs. 7 lit. a)

### 1.1 Zweck der Verarbeitung

Der VÖB Service Chatbot ist ein KI-gestütztes Wissensmanagement-Tool für den internen Gebrauch des VÖB (Bundesverband Öffentlicher Banken Deutschlands e.V.). Der Chatbot ermöglicht VÖB-Mitarbeitern:

- **Abfrage interner Wissensbestände** mittels natürlichsprachlicher Eingaben (Retrieval-Augmented Generation / RAG)
- **Interaktion mit Large Language Models** zur Beantwortung fachlicher Fragen
- **Dokumentensuche und -zusammenfassung** über eine vektorbasierte Suchinfrastruktur (OpenSearch als primaerer Document Index, Vespa als Vektor-Backend)

Der Chatbot trifft **keine autonomen Entscheidungen** über Personen und wird **nicht** für Kreditwürdigkeitsprüfungen, Leistungsbewertungen oder andere Verarbeitungen mit rechtlicher Wirkung eingesetzt.

### 1.2 Kategorien betroffener Personen

| Kategorie | Anzahl (geschätzt) | Beschreibung |
|-----------|--------------------|-------------|
| VÖB-Mitarbeiter (Nutzer) | ~150 (davon ~30-40 gleichzeitig aktiv) | Primäre Nutzer des Chatbot-Systems |
| System-Administratoren | 1-2 | Tech Lead (CCJ) + ggf. VÖB IT |
| Personen in Dokumenten | Unbestimmt | Personen, deren Daten in indexierten Dokumenten vorkommen (indirekt betroffen) |

### 1.3 Kategorien personenbezogener Daten

| Datenkategorie | Beispiele | Sensibilität | Speicherort | Rechtsgrundlage |
|----------------|-----------|-------------|-------------|-----------------|
| **Identitätsdaten** | Name, E-Mail-Adresse | Hoch | PostgreSQL (StackIT Managed PG Flex) | Art. 6(1)(f) |
| **Authentifizierungsdaten** | Passwort-Hash, Session-Cookies, OIDC-Token (geplant) | Kritisch | PostgreSQL | Art. 6(1)(f) |
| **Konversationsdaten** | Chat-Eingaben, LLM-Antworten, Konversationshistorie | Hoch | PostgreSQL + OpenSearch/Vespa (in-cluster) | Art. 6(1)(f) |
| **Nutzungsmetriken (ext-token)** | Token-Verbrauch pro User, pro Modell, Timestamps, Request-Anzahl | Mittel | PostgreSQL (Tabelle `ext_token_usage`) | Art. 6(1)(f) |
| **Dokumente / Embeddings** | Hochgeladene Dateien, Vektor-Embeddings der Dokumenteninhalte | Mittel | Object Storage (StackIT S3) + OpenSearch/Vespa PersistentVolume | Art. 6(1)(f) |
| **IP-Adressen** | Client-IP in Webserver-/API-Logs | Niedrig | Kubernetes Pod-Logs (nicht persistent) | Art. 6(1)(f) |
| **Session-Daten** | Session-ID, Login-Zeitpunkt | Niedrig | Redis (in-cluster, Cache) | Art. 6(1)(f) |
| **API-Schlüssel** | StackIT AI Model Serving Token | Kritisch | PostgreSQL (Onyx-DB, Klartext) | Art. 6(1)(f) |

**Besondere Kategorien (Art. 9 DSGVO):** Es werden keine besonderen Kategorien personenbezogener Daten (Gesundheit, Religion, ethnische Herkunft etc.) gezielt erhoben. Es besteht jedoch das Risiko, dass Nutzer solche Daten in Chat-Eingaben eingeben oder dass indexierte Dokumente solche Daten enthalten. Maßnahmen: System Prompts (ext-prompts) weisen das LLM an, keine sensiblen personenbezogenen Daten zu verarbeiten oder auszugeben.

### 1.4 Datenflüsse

```
Nutzer (VÖB-Mitarbeiter)
  │
  │ HTTPS (TLSv1.3, ECDSA P-384)
  ↓
NGINX Ingress Controller (StackIT SKE Cluster, EU01 Frankfurt)
  │
  ├──→ Web Server (Next.js Frontend)
  │       Statische UI-Auslieferung, keine PII-Verarbeitung
  │
  └──→ API Server (FastAPI Backend)
          │
          ├──→ PostgreSQL (StackIT Managed PG Flex)
          │       Identitätsdaten, Konversationen, Token-Usage,
          │       Branding-Config, System Prompts, Session-State
          │       Verschlüsselung: AES-256 at-rest (StackIT Default)
          │
          ├──→ OpenSearch / Vespa (In-Cluster, PersistentVolume)
          │       Document Index, Vektor-Embeddings, Dokumenten-Chunks
          │       OpenSearch = primaerer Document Index, Vespa = Vektor-Backend
          │       Verschlüsselung: AES-256 at-rest (StackIT StorageClass)
          │
          ├──→ Redis (In-Cluster)
          │       Session-Cache, Celery Task Queue
          │       Passwort-geschützt, keine Persistenz
          │
          ├──→ StackIT AI Model Serving (LLM)
          │       HTTPS API-Aufrufe
          │       Chat-Prompts + Kontext → LLM-Antwort
          │       Region EU01 Frankfurt, kein Drittland-Transfer
          │       StackIT verarbeitet Daten nur zur Modell-Inferenz
          │
          ├──→ StackIT Object Storage (S3)
          │       Hochgeladene Dateien
          │       SSE-Verschlüsselung (StackIT Default)
          │
          └──→ Celery Worker (8 separate Worker im Cluster)
                  Asynchrone Dokumenten-Indexierung,
                  Embedding-Berechnung, Token-Tracking
```

### 1.5 Empfänger und Auftragsverarbeiter

| Empfänger | Rolle | Zweck | Rechtsgrundlage | AVV-Status |
|-----------|-------|-------|-----------------|------------|
| **StackIT (Schwarz IT KG)** | Auftragsverarbeiter | Cloud-Infrastruktur: Kubernetes, PostgreSQL, Object Storage, AI Model Serving | Art. 28 DSGVO | [AVV] -- AVV zwischen VÖB und StackIT muss geschlossen werden |
| **CCJ Development UG** | Auftragsverarbeiter | Entwicklung, Betrieb, Wartung des Chatbot-Systems | Art. 28 DSGVO | [AVV] -- AVV zwischen VÖB und CCJ muss geschlossen werden |
| **Let's Encrypt (ISRG)** | Kein Auftragsverarbeiter | TLS-Zertifikatsausstellung (nur Domain-Validierung, keine PII) | Berechtigtes Interesse | Nicht erforderlich |
| **Microsoft (Entra ID)** | Auftragsverarbeiter (geplant) | Authentifizierung via OIDC (Phase 3) | Art. 28 DSGVO | [AVV] -- Prüfung ob bestehender Microsoft-AVV des VÖB ausreicht |

**Drittland-Übermittlung:** Es findet **keine** Übermittlung personenbezogener Daten in Drittländer statt. Die gesamte Verarbeitung erfolgt auf StackIT-Infrastruktur in Frankfurt am Main (EU01). Es werden keine externen LLM-Provider (OpenAI, Google, Anthropic) eingesetzt. StackIT besitzt **BSI C5 Type 2** Zertifizierung.

### 1.6 Speicherdauer und Löschung

| Datenkategorie | Vorgesehene Speicherdauer | Löschmethode | Status |
|----------------|---------------------------|-------------|--------|
| **Identitätsdaten** | Beschäftigungsdauer + 3 Jahre (Paragraph 195 BGB Verjährung) | PostgreSQL DELETE + Autovacuum | [LÖSCHKONZEPT] -- VÖB muss Frist bestätigen |
| **Konversationsdaten** | [LÖSCHKONZEPT] -- Kickoff-Beschluss: 6 Monate Chat-Retention | PostgreSQL DELETE + Autovacuum | [LÖSCHKONZEPT] -- Frist definieren. Empfehlung Compliance-Research: 12 Monate (Banking-Kontext, Nachweisbarkeit) |
| **Token-Nutzungsmetriken** | [LÖSCHKONZEPT] -- analog Konversationsdaten | PostgreSQL DELETE + Autovacuum | [LÖSCHKONZEPT] |
| **Dokumente / Embeddings** | Quelldauer + 30 Tage nach Quelllöschung | Vespa `document.remove()` + S3 Lifecycle | [LÖSCHKONZEPT] |
| **Session-Daten** | 24h nach Session-Ende | Redis TTL (automatisch) | Angemessen, kein Handlungsbedarf |
| **API-Logs** | Standard: 90 Tage, Security-/Audit-Logs: 6-12 Monate | K8s Log-Rotation | [LÖSCHKONZEPT] -- Differenzierung erforderlich |
| **IP-Adressen (Logs)** | Kubernetes Pod-Lifecycle (nicht persistent) | Automatisch bei Pod-Restart | Akzeptabel für normalen Schutzbedarf |

**Löschkonzept:** Ein detailliertes Löschkonzept nach DIN EN ISO/IEC 27555:2025-09 (vormals DIN 66398:2016-05) ist noch zu erstellen. Es muss Löschklassen, Löschregeln mit Startzeitpunkt und Regelfrist, Umsetzungsregeln (technische Zuordnung) sowie Nachweispflichten (Löschprotokoll) enthalten.

**Sonderfälle:**
- **Mitarbeiter-Austritt:** Account sofort deaktivieren, löschen nach Frist (Empfehlung: 30 Tage). Chat-Daten: reguläre Löschfrist abwarten.
- **Art. 17 DSGVO Löschanfrage:** Prozess mit 1-Monats-Frist. Prüfung Art. 17 Abs. 3 (Aufbewahrungspflichten). Bei Aufbewahrungspflicht: Einschränkung statt Löschung (Paragraph 35 Abs. 3 BDSG).
- **Vektor-Embeddings:** Embedding + Quelldokument = eine Löscheinheit. Keine Re-Indexierung mit gelöschten Dokumenten.
- **Backup-Löschung:** Physische Löschung in Backups nicht zwingend, wenn bei Restore die Löschung wiederholt wird (EDSA Feb 2026).

### 1.7 Technische Systemübersicht

| Komponente | Technologie | Standort |
|-----------|------------|---------|
| Frontend | Next.js 16, React 19, TypeScript | StackIT SKE Cluster EU01 |
| Backend | Python 3.11, FastAPI 0.133.1, SQLAlchemy 2.0 | StackIT SKE Cluster EU01 |
| Datenbank | PostgreSQL 16 (StackIT Managed PG Flex) | StackIT EU01 Frankfurt |
| Document Index | OpenSearch (primaer) + Vespa (Vektor-Backend, In-Cluster StatefulSet) | StackIT SKE Cluster EU01 |
| Cache | Redis 7.0.15 (In-Cluster) | StackIT SKE Cluster EU01 |
| Objektspeicher | StackIT Object Storage (S3-kompatibel) | StackIT EU01 Frankfurt |
| LLM-Dienst | StackIT AI Model Serving (vLLM-Backend) | StackIT EU01 Frankfurt |
| Authentifizierung | Onyx Basic Auth (aktuell) / Microsoft Entra ID OIDC (geplant) | In-Cluster / Microsoft Azure |
| Monitoring | Prometheus, Grafana, AlertManager (In-Cluster) | StackIT SKE Cluster EU01 |

**Umgebungen:**

| Environment | Cluster | Status | URL |
|-------------|---------|--------|-----|
| DEV | `vob-chatbot` (Shared) | LIVE seit 2026-02-27 | `https://dev.chatbot.voeb-service.de` |
| TEST | `vob-chatbot` (Shared) | LIVE seit 2026-03-03 | `https://test.chatbot.voeb-service.de` |
| PROD | `vob-prod` (Eigener Cluster) | **HTTPS LIVE** seit 2026-03-17 | `https://chatbot.voeb-service.de` |

---

## 2. Rechtsgrundlagen-Prüfung (Art. 35 Abs. 7 lit. a, Teil)

### 2.1 Primäre Rechtsgrundlage

**Art. 6 Abs. 1 lit. f DSGVO (Berechtigtes Interesse)**

Der Drei-Stufen-Test nach Art. 6 Abs. 1 lit. f:

**Stufe 1 -- Berechtigtes Interesse:**
Der VÖB hat ein legitimes Interesse an der Einführung eines KI-gestützten Informationssystems zur Steigerung der Effizienz und Qualität der internen Wissensarbeit. Als Spitzenverband der öffentlichen Banken berät der VÖB seine 64 Mitgliedsinstitute in regulatorischen, wirtschaftlichen und technischen Fragen. Ein schneller, präziser Zugriff auf interne Wissensbestände ist für die Kernaufgabe des Verbandes erforderlich.

**Stufe 2 -- Erforderlichkeit:**
Die Verarbeitung von Identitätsdaten (Authentifizierung, Zugriffskontrolle), Chat-Inhalten (Beantwortung von Fragen) und Nutzungsmetriken (Kostenkontrolle, Missbrauchsprävention) ist für den bestimmungsgemäßen Betrieb des Chatbots erforderlich. Ohne diese Verarbeitungen kann der Dienst nicht erbracht werden.

**Stufe 3 -- Interessenabwägung:**

| Interesse des VÖB | Interesse der Betroffenen | Abwägung |
|--------------------|--------------------------|----------|
| Effizienzsteigerung der Wissensarbeit | Recht auf informationelle Selbstbestimmung | Mitigiert durch Datenminimierung, Zugriffskontrolle |
| Kostenkontrolle (Token-Tracking) | Schutz vor Leistungsüberwachung | Mitigiert: Aggregierte Metriken, kein inhaltliches Monitoring der Chat-Verläufe durch Vorgesetzte |
| Qualitätssicherung (System-Prompts) | Transparenz der KI-Steuerung | Mitigiert: System Prompts sind durch Admin konfigurierbar und dokumentiert |
| IT-Sicherheit (Logging) | Minimale Datenerhebung | Mitigiert: Logs nicht persistent (Pod-Lifecycle), keine zentrale Log-Aggregation |

**Ergebnis:** Die Abwägung fällt zugunsten des VÖB aus, sofern die unter Abschnitt 5 dokumentierten Maßnahmen umgesetzt sind.

### 2.2 Verworfene Rechtsgrundlagen

**NICHT Art. 6 Abs. 1 lit. b (Vertragserfüllung):**
Der KI-Chatbot ist ein freiwilliges Produktivitäts-Tool, keine vertraglich zwingende Leistung. Das EDPB warnt vor einer Über-Berufung auf lit. b bei Arbeitgeber-Datenverarbeitungen.

**NICHT Art. 6 Abs. 1 lit. e (Öffentliches Interesse):**
Der VÖB ist ein privatrechtlicher eingetragener Verein (e.V.), keine Behörde.

**NICHT Paragraph 26 BDSG (Beschäftigungsverhältnis):**
Der EuGH hat in C-34/21 (30.03.2023) Paragraph 26 Abs. 1 S. 1 BDSG für europarechtswidrig erklärt. Diese Rechtsgrundlage ist daher nicht heranzuziehen.

### 2.3 Entscheidung

[VÖB-DSB] -- Der VÖB-Datenschutzbeauftragte muss die Rechtsgrundlage bestätigen. Insbesondere ist zu prüfen, ob Art. 6(1)(f) ausreichend ist oder ob eine Betriebsvereinbarung (als Kollektivvereinbarung nach Art. 88 DSGVO i.V.m. Paragraph 26 Abs. 4 BDSG) angestrebt werden sollte, um die Verarbeitung auf eine breitere Grundlage zu stellen.

---

## 3. Notwendigkeit und Verhältnismäßigkeit (Art. 35 Abs. 7 lit. b)

### 3.1 Notwendigkeit der Verarbeitung

| Verarbeitungszweck | Warum notwendig? | Alternativen geprüft? |
|-------------------|------------------|----------------------|
| Identitätsdaten (E-Mail, Name) | Authentifizierung, Zugriffskontrolle, Audit-Trail | Anonyme Nutzung: Nicht möglich (Zugriffskontrolle, Compliance) |
| Chat-Konversationen | Kernfunktion des Systems (Frage-Antwort) | Stateless-Modus (kein Verlauf): Reduziert Nutzen erheblich, keine Kontextfortführung |
| Token-Usage-Tracking pro User | Kostenkontrolle, Quota-Management, Missbrauchsprävention | Aggregiertes Tracking (ohne User-Zuordnung): Unzureichend für Quota-Enforcement |
| Dokumente / Embeddings | RAG-Funktionalität (Wissenssuche) | Keine: RAG ist Kernfeature |
| Session-Daten | Login-State, Request-Routing | Keine: Technisch erforderlich |
| API-Logs (inkl. IP) | Fehleranalyse, Security-Monitoring | Log-Minimierung: Bereits gegeben (Pod-Lifecycle, keine zentrale Aggregation) |

### 3.2 Datenminimierung (Art. 5 Abs. 1 lit. c DSGVO)

| Maßnahme | Status |
|----------|--------|
| Nur authentifizierte Nutzer können den Chatbot verwenden | IMPLEMENTIERT |
| Token-Tracking erfasst Zähler und Zeitstempel, nicht Chat-Inhalte | IMPLEMENTIERT |
| System Prompts (ext-prompts) instruieren das LLM, keine sensiblen PII auszugeben | IMPLEMENTIERT |
| Keine automatische Erfassung von Standortdaten, Gerätekennung o.ä. | IMPLEMENTIERT |
| Session-Daten werden nach 24h automatisch gelöscht (Redis TTL) | IMPLEMENTIERT |
| Kubernetes Pod-Logs sind nicht persistent (gelöscht bei Pod-Restart) | IMPLEMENTIERT |
| Keine zentrale Log-Aggregation (reduziert Speicherdauer von Logs) | Aktueller Stand (geplante Einführung prüfen) |
| Löschkonzept mit definierten Aufbewahrungsfristen | [LÖSCHKONZEPT] |

### 3.3 Zweckbindung (Art. 5 Abs. 1 lit. b DSGVO)

Die erhobenen Daten werden ausschließlich für die in Abschnitt 1.1 definierten Zwecke verarbeitet:

- **Konversationsdaten:** Ausschließlich für Chatbot-Interaktion und Konversationshistorie. Keine Nutzung für Leistungsbewertung, Profiling oder sonstige Zwecke.
- **Token-Nutzungsmetriken:** Ausschließlich für Kostenkontrolle und Quota-Management. Keine Weitergabe an Vorgesetzte. Keine Korrelation mit Chat-Inhalten.
- **Dokumente:** Ausschließlich für RAG-basierte Wissenssuche. Keine Analyse von Dokumenteninhalten zu anderen Zwecken.

[KLÄRUNG] -- Mit VÖB klären: Werden Nutzungsstatistiken an Vorgesetzte oder HR weitergegeben? Falls ja, ist dies im Zweck zu dokumentieren und die Interessenabwägung anzupassen.

### 3.4 Speicherbegrenzung (Art. 5 Abs. 1 lit. e DSGVO)

Siehe Abschnitt 1.6 (Speicherdauer und Löschung). Die Umsetzung des Speicherbegrenzungsgrundsatzes hängt vom noch zu erstellenden Löschkonzept ab.

### 3.5 Verhältnismäßigkeit

Der Eingriff in die Rechte der Betroffenen ist **verhältnismäßig**, weil:

1. **Geeignetheit:** Der Chatbot ist geeignet, den Zweck der Effizienzsteigerung der internen Wissensarbeit zu erreichen.
2. **Erforderlichkeit:** Mildere Mittel (anonyme Nutzung, Stateless-Betrieb) würden den Zweck nicht in gleichem Maße erfüllen.
3. **Angemessenheit:** Die Verarbeitung beschränkt sich auf das für den Betrieb notwendige Minimum. Umfangreiche technische und organisatorische Maßnahmen schützen die Rechte der Betroffenen (siehe Abschnitt 5).

---

## 4. Risikobewertung (Art. 35 Abs. 7 lit. c)

### 4.1 Risikobewertungsmethodik

Die Risikobewertung folgt dem **Standard-Datenschutzmodell (SDM V3.1)** der Datenschutzkonferenz und berücksichtigt die 7 SDM-Schutzziele:

1. Datenminimierung
2. Verfügbarkeit
3. Integrität
4. Vertraulichkeit
5. Nichtverkettung (Zweckbindung)
6. Transparenz
7. Intervenierbarkeit (Betroffenenrechte)

**Risikomatrix:**

| | Schwere: Niedrig | Schwere: Mittel | Schwere: Hoch |
|---|---|---|---|
| **Eintritt: Hoch** | Mittel | Hoch | Sehr Hoch |
| **Eintritt: Mittel** | Niedrig | Mittel | Hoch |
| **Eintritt: Niedrig** | Niedrig | Niedrig | Mittel |

### 4.2 Risikokatalog

#### R1 -- Unbefugter Zugriff auf Konversationsdaten

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Vertraulichkeit |
| **Beschreibung** | Unbefugte Personen erlangen Zugriff auf Chat-Verläufe von VÖB-Mitarbeitern. Konversationen können sensible fachliche Inhalte (Regulatorik, Kreditentscheidungen, interne Strategien) enthalten. |
| **Eintrittswahrscheinlichkeit** | Niedrig |
| **Schwere** | Hoch |
| **Risikostufe** | **Mittel** |
| **Bestehende Maßnahmen** | Authentifizierung (Basic Auth, geplant: Entra ID OIDC + MFA); PostgreSQL ACL auf Cluster-Egress-IP beschränkt (SEC-01); NetworkPolicies mit Default-Deny (SEC-03 DEV/TEST); Encryption-at-Rest AES-256 (SEC-07); TLS 1.3 für Datenübertragung; Kubernetes Namespace-Isolation |
| **Restrisiko** | **Niedrig** -- Zugriffskontrolle mehrschichtig implementiert. Erhöhtes Risiko in PROD bis Entra ID aktiviert (Basic Auth bietet kein MFA). |
| **Offene Maßnahmen** | CORS-Einschränkung (SEC-08) |

#### R2 -- LLM-Halluzination / falsche Informationen

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Integrität |
| **Beschreibung** | Das LLM generiert faktisch falsche oder irreführende Antworten. Im Banking-Kontext besonders kritisch: falsche regulatorische Aussagen, fehlerhafte Interpretationen von BAIT/DORA/MaRisk. |
| **Eintrittswahrscheinlichkeit** | Hoch |
| **Schwere** | Hoch |
| **Risikostufe** | **Sehr Hoch** |
| **Bestehende Maßnahmen** | RAG-Architektur mit Quellenangabe (Onyx-nativ); System Prompts für Guardrails (ext-prompts); 4 verschiedene LLM-Modelle zur Auswahl; VÖB-spezifische Instruktionen via ext-prompts |
| **Restrisiko** | **Mittel** -- Halluzination ist ein inhärentes LLM-Risiko. Die RAG-Architektur reduziert das Risiko, eliminiert es aber nicht. |
| **Offene Maßnahmen** | Nutzer-Schulung (EU AI Act Art. 4 KI-Kompetenz); Disclaimer bei jeder Antwort; Output-Filterung evaluieren |

#### R3 -- Prompt Injection / Datenexfiltration

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Vertraulichkeit |
| **Beschreibung** | Bösartige Eingaben (Prompt Injection) manipulieren das LLM, um vertrauliche Daten aus dem Dokumenten-Index zu extrahieren oder Systemgrenzen zu umgehen. Meldepflicht nach Art. 33 DSGVO bei erfolgreicher Exfiltration personenbezogener Daten. |
| **Eintrittswahrscheinlichkeit** | Niedrig |
| **Schwere** | Hoch |
| **Risikostufe** | **Mittel** |
| **Bestehende Maßnahmen** | System Prompts werden vor User-Input platziert (Onyx-Standard); Input-Validierung über Pydantic-Modelle (Längenbegrenzung); ext-prompts ermöglicht VÖB-spezifische Guardrails; Authentifizierung (nur legitimierte Nutzer) |
| **Restrisiko** | **Mittel** -- Prompt Injection ist ein bekanntes, aber schwer vollständig lösbares Problem bei LLM-Systemen. Das Risiko ist durch die interne Nutzerschaft (keine öffentliche Exponierung) reduziert. |
| **Offene Maßnahmen** | Output-Filterung für sensible Daten (IBAN, Kreditkartennummern etc.); Adversarial Testing vor PROD Go-Live; Rate Limiting (SEC-09) |

#### R4 -- Verlust von Konversationsdaten

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Verfügbarkeit |
| **Beschreibung** | Konversationsdaten gehen durch technischen Fehler (Datenbankausfall, Backup-Fehler) oder unbeabsichtigte Löschung verloren. |
| **Eintrittswahrscheinlichkeit** | Niedrig |
| **Schwere** | Mittel |
| **Risikostufe** | **Niedrig** |
| **Bestehende Maßnahmen** | PostgreSQL Managed Backups (StackIT): täglich, Point-in-Time Recovery auf PROD (PG Flex 4.8 HA, 3-Node); `prevent_destroy = true` in Terraform; Vespa PersistentVolume (20 Gi); Git für Code und Konfiguration |
| **Restrisiko** | **Niedrig** -- StackIT Managed Backup + HA-Konfiguration bieten ausreichenden Schutz. |
| **Offene Maßnahmen** | RTO/RPO-Ziele mit VÖB definieren; Vespa-Backup-Strategie (aktuell kein separates Backup) |

#### R5 -- Identitätsdiebstahl durch schwache Authentifizierung

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Vertraulichkeit |
| **Beschreibung** | Angreifer übernimmt die Identität eines VÖB-Mitarbeiters durch schwache Authentifizierung (kein MFA, Credential Stuffing, Session Hijacking). |
| **Eintrittswahrscheinlichkeit** | Mittel (aktuell, mit Basic Auth) / Niedrig (nach Entra ID) |
| **Schwere** | Hoch |
| **Risikostufe** | **Hoch** (aktuell) / **Mittel** (nach Entra ID) |
| **Bestehende Maßnahmen** | Session-basierte Authentifizierung (Cookie); SameSite-Cookie-Attribut (CSRF-Schutz); TLS 1.3 (Session-Cookie-Schutz im Transit); Security-Header (X-Frame-Options: DENY, Clickjacking-Schutz) |
| **Restrisiko** | **Hoch** (aktuell) -- Basic Auth ohne MFA ist unzureichend für ein System mit potenziell sensiblen Banking-Informationen. Das Risiko sinkt signifikant mit Entra ID + MFA. |
| **Offene Maßnahmen** | Entra ID OIDC mit MFA: ✅ IMPLEMENTIERT (DEV + PROD seit 2026-03-24); CORS-Einschränkung auf Produktions-Domain (SEC-08) |

#### R6 -- Profilbildung durch Nutzungsmetriken

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Datenminimierung, Nichtverkettung |
| **Beschreibung** | Die per-User Token-Nutzungsmetriken (ext-token) ermöglichen eine Nachverfolgung des individuellen Nutzungsverhaltens. Im Arbeitgeberkontext besteht das Risiko der Leistungsüberwachung oder der Sanktionierung bei Unter-/Übernutzung. Beschäftigtendatenschutz-Relevanz. |
| **Eintrittswahrscheinlichkeit** | Mittel |
| **Schwere** | Hoch |
| **Risikostufe** | **Hoch** |
| **Bestehende Maßnahmen** | Token-Tracking erfasst nur Mengen und Zeitstempel, nicht Chat-Inhalte; Usage Dashboard nur für Admins zugänglich (`Depends(current_admin_user)`); Pre-Request Quota-Prüfung ohne Inhaltsanalyse |
| **Restrisiko** | **Mittel** -- Ohne klare organisatorische Regelung (z.B. Betriebsvereinbarung) besteht das Risiko der Zweckentfremdung der Nutzungsdaten. |
| **Offene Maßnahmen** | [VÖB-DSB] -- Organisatorische Regelung: Wer darf die per-User-Statistiken einsehen? Dürfen Vorgesetzte/HR Zugriff erhalten? Betriebsvereinbarung erforderlich? [KLÄRUNG] -- Möglichkeit der Anonymisierung/Aggregierung der Nutzungsstatistiken prüfen |

#### R7 -- Verletzung der Zweckbindung

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Nichtverkettung |
| **Beschreibung** | Chat-Daten oder Nutzungsmetriken werden für Zwecke verwendet, die über den definierten Verarbeitungszweck (Wissensmanagement, Kostenkontrolle) hinausgehen. ISiCO identifiziert "zweckoffen angelegte KI-Nutzung" als Kernrisiko. |
| **Eintrittswahrscheinlichkeit** | Mittel |
| **Schwere** | Hoch |
| **Risikostufe** | **Hoch** |
| **Bestehende Maßnahmen** | Verarbeitungszweck in dieser DSFA dokumentiert; Admin-Zugriff auf Usage-Dashboard eingeschränkt; Feature Flags ermöglichen gezielte Deaktivierung einzelner Tracking-Module |
| **Restrisiko** | **Mittel** -- Technisch ist eine Zweckänderung durch Admins möglich (SQL-Zugriff auf Datenbank). Organisatorische Maßnahmen (Richtlinien, Schulungen) sind erforderlich. |
| **Offene Maßnahmen** | VVT (Art. 30) erstellen mit klarer Zweckdefinition; Nutzungsrichtlinie für Admins; [VÖB-DSB] -- Prüfen ob Betriebsvereinbarung die Zwecke verbindlich festlegt |

#### R8 -- Mangelnde Transparenz / Blackbox

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Transparenz |
| **Beschreibung** | Betroffene verstehen nicht, wie ihre Daten im KI-System verarbeitet werden, welche Daten gespeichert werden oder wie das LLM Antworten generiert. DSK Orientierungshilfe KI (06.05.2024) identifiziert mangelnde Transparenz als zentrales KI-Risiko. |
| **Eintrittswahrscheinlichkeit** | Mittel |
| **Schwere** | Mittel |
| **Risikostufe** | **Mittel** |
| **Bestehende Maßnahmen** | ext-branding Disclaimer auf Login-Seite; RAG-Architektur mit Quellenangabe; Sicherheitskonzept und Betriebskonzept dokumentieren Datenflüsse |
| **Restrisiko** | **Mittel** -- Nutzer erhalten keine systematische Information über Datenverarbeitung im Chatbot. Datenschutzerklärung fehlt. |
| **Offene Maßnahmen** | EU AI Act Art. 50 Transparenzpflicht umsetzen (Deadline: 02.08.2026): Nutzer müssen vor Interaktion informiert werden, dass sie mit KI interagieren; Datenschutzerklärung erstellen (VÖB Recht); Informationspflichten Art. 13/14 DSGVO erfüllen |

#### R9 -- Cross-Context Leakage (unbeabsichtigte Offenlegung im LLM-Output)

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Vertraulichkeit |
| **Beschreibung** | Das LLM gibt in einer Antwort Informationen preis, die aus einem anderen Kontext stammen (z.B. Dokumente, auf die der anfragende Nutzer keinen Zugriff haben sollte). Besonders relevant bei RAG-Systemen, die auf einen gemeinsamen Dokumenten-Index zugreifen. EDPB LLM Guidance identifiziert dies als spezifisches KI-Risiko. |
| **Eintrittswahrscheinlichkeit** | Mittel |
| **Schwere** | Hoch |
| **Risikostufe** | **Hoch** |
| **Bestehende Maßnahmen** | Onyx Access Control (nativ): Dokumenten-Zugriff pro User/Gruppe steuerbar; ext-prompts: VÖB-spezifische Guardrails |
| **Restrisiko** | **Mittel** -- ext-rbac (Phase 4f, 2026-03-23) und ext-access (Phase 4g, 2026-03-25) sind implementiert. Granulare Zugriffskontrolle pro Gruppe ist technisch verfuegbar. Restrisiko bleibt bis VÖB Zugriffsmatrix fuer Dokumentkategorien definiert. |
| **Offene Maßnahmen** | Dokument-Level Access Control konfigurieren (ext-access auf PROD aktivieren); [KLÄRUNG] -- VÖB muss Zugriffsmatrix für Dokumentkategorien definieren |

#### R10 -- Diskriminierung / Bias

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Integrität |
| **Beschreibung** | Das LLM generiert diskriminierende, voreingenommene oder unangemessene Antworten (z.B. Bias in der Behandlung bestimmter Personengruppen, Regionen, Institute). DSK Orientierungshilfe KI (06.05.2024) adressiert dieses Risiko explizit. |
| **Eintrittswahrscheinlichkeit** | Niedrig |
| **Schwere** | Mittel |
| **Risikostufe** | **Niedrig** |
| **Bestehende Maßnahmen** | System Prompts (ext-prompts) mit Neutralitätsanweisungen; Intern genutztes Tool (kein Kundenkontakt); 4 verschiedene LLM-Modelle stehen zur Auswahl (Diversität) |
| **Restrisiko** | **Niedrig** -- Bei interner Nutzung für Wissensmanagement ist das Bias-Risiko geringer als bei kundenbezogenen Entscheidungssystemen. |
| **Offene Maßnahmen** | KI-Kompetenz-Schulung (EU AI Act Art. 4); Nutzungsleitfaden für Mitarbeiter |

#### R11 -- Schatten-KI / unkontrollierte Nutzung

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Transparenz |
| **Beschreibung** | Mitarbeiter nutzen neben dem offiziellen Chatbot unkontrolliert externe KI-Tools (ChatGPT, Gemini etc.) und laden dabei vertrauliche VÖB-Daten hoch. ISiCO identifiziert Schatten-KI als organisatorisches Risiko. |
| **Eintrittswahrscheinlichkeit** | Mittel |
| **Schwere** | Mittel |
| **Risikostufe** | **Mittel** |
| **Bestehende Maßnahmen** | Bereitstellung eines offiziellen, datensouveränen KI-Tools (VÖB Service Chatbot auf StackIT); StackIT AI Model Serving verarbeitet Daten ausschließlich in Deutschland |
| **Restrisiko** | **Mittel** -- Ohne organisatorische Richtlinie zur KI-Nutzung besteht das Risiko, dass Mitarbeiter externe KI-Tools parallel nutzen. |
| **Offene Maßnahmen** | KI-Nutzungsrichtlinie erstellen; KI-Kompetenz-Schulung (EU AI Act Art. 4); [KLÄRUNG] -- Hat VÖB bereits eine KI-Policy? Werden externe KI-Tools gesperrt? |

#### R12 -- Verletzung von Betroffenenrechten (Art. 15-22 DSGVO)

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Intervenierbarkeit |
| **Beschreibung** | Betroffenenrechte (insbesondere Auskunft Art. 15, Löschung Art. 17, Berichtigung Art. 16) können nicht oder nur unvollständig erfüllt werden. Besonders problematisch: Wie werden Lösch-/Auskunftsanfragen in Vektor-Embeddings umgesetzt? EDPB und BfDI identifizieren dies als spezifisches KI-Risiko. |
| **Eintrittswahrscheinlichkeit** | Mittel |
| **Schwere** | Hoch |
| **Risikostufe** | **Hoch** |
| **Bestehende Maßnahmen** | Onyx unterstützt User-Löschung nativ; Vespa bietet `document.remove()` API; PostgreSQL DELETE + Autovacuum |
| **Restrisiko** | **Hoch** -- Es fehlt ein dokumentierter Prozess für Betroffenenrechte. Insbesondere: (1) Wie wird ein Auskunftsersuchen (Art. 15) für Chat-Verläufe beantwortet? (2) Wie wird sichergestellt, dass Löschung in PostgreSQL UND Vespa UND Backups erfolgt? (3) Wie werden personenbezogene Daten in Embeddings identifiziert und gelöscht? |
| **Offene Maßnahmen** | **KRITISCH:** Prozess für Betroffenenrechte definieren und dokumentieren; [LÖSCHKONZEPT] -- Löschung als End-to-End-Prozess (PG + Vespa + S3 + Backups) spezifizieren; [VÖB-DSB] -- Zuständigkeiten für Betroffenenanfragen klären |

#### R13 -- Übermittlung an Dritte

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Vertraulichkeit |
| **Beschreibung** | Personenbezogene Daten werden unbeabsichtigt an Dritte übermittelt (externe LLM-Provider, Cloud-Dienste in Drittländern). |
| **Eintrittswahrscheinlichkeit** | Niedrig |
| **Schwere** | Niedrig |
| **Risikostufe** | **Niedrig** |
| **Bestehende Maßnahmen** | LLM-Verarbeitung ausschließlich auf StackIT (self-hosted, EU01 Frankfurt); Kein Vertrag mit OpenAI, Google, Anthropic; StackIT BSI C5 Type 2 zertifiziert; NetworkPolicies beschränken Egress-Traffic |
| **Restrisiko** | **Niedrig** -- Die Architektur ist gezielt darauf ausgelegt, keine Drittland-Übermittlung zu ermöglichen. |
| **Offene Maßnahmen** | Model Server Image Mirroring in StackIT Registry evaluieren (aktuell Pull von Docker Hub, aber nur Container-Image, keine Nutzerdaten) |

#### R14 -- Unzureichende Protokollierung sicherheitsrelevanter Ereignisse

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Transparenz, Integrität |
| **Beschreibung** | Sicherheitsrelevante Ereignisse (fehlgeschlagene Logins, unautorisierte Zugriffe, Konfigurationsänderungen) werden nicht oder nicht ausreichend lange protokolliert. Kubernetes Pod-Logs gehen bei Pod-Restart verloren. Kein zentralisiertes Log-Management. |
| **Eintrittswahrscheinlichkeit** | Mittel |
| **Schwere** | Mittel |
| **Risikostufe** | **Mittel** |
| **Bestehende Maßnahmen** | Prometheus + Grafana für Metriken (deployed alle Environments); AlertManager mit Teams-Integration; postgres_exporter + redis_exporter; API-Server-Logging (FastAPI, `LOG_LEVEL: INFO`) |
| **Restrisiko** | **Mittel** -- Metriken-Monitoring ist vorhanden, aber keine persistente Log-Aggregation. Bei einem Sicherheitsvorfall könnten forensische Informationen fehlen. |
| **Offene Maßnahmen** | Zentralisierte Log-Aggregation evaluieren (Loki); Security-/Audit-Logs mit längerer Retention (6-12 Monate) |

#### R15 -- Fehlende Rate Limits (DoS / LLM-Kosten-Missbrauch)

| Feld | Bewertung |
|------|-----------|
| **SDM-Schutzziel** | Verfügbarkeit |
| **Beschreibung** | Ohne Rate Limiting können einzelne Nutzer oder automatisierte Angriffe das System überlasten (Denial of Service) oder unkontrollierte LLM-Kosten verursachen. |
| **Eintrittswahrscheinlichkeit** | Niedrig (internes Tool) |
| **Schwere** | Mittel |
| **Risikostufe** | **Niedrig** |
| **Bestehende Maßnahmen** | ext-token: Per-User Quotas mit Hard Stops (HTTP 429); StackIT-seitige Rate Limits (200K TPM, 30-600 RPM); Authentifizierungspflicht (kein öffentlicher Zugang) |
| **Restrisiko** | **Niedrig** -- ext-token Quotas und StackIT Rate Limits bieten doppelten Schutz. Kein öffentlicher Zugang reduziert DoS-Risiko. |
| **Offene Maßnahmen** | NGINX Ingress Rate Limiting evaluieren (SEC-09); WAF evaluieren |

### 4.3 Risiko-Übersicht

| ID | Risiko | Risikostufe | Restrisiko |
|----|--------|-------------|-----------|
| R2 | LLM-Halluzination | **Sehr Hoch** | Mittel |
| R5 | Identitätsdiebstahl (schwache Auth) | **Hoch** | Hoch (aktuell) |
| R6 | Profilbildung durch Nutzungsmetriken | **Hoch** | Mittel |
| R7 | Verletzung der Zweckbindung | **Hoch** | Mittel |
| R9 | Cross-Context Leakage | **Hoch** | Hoch |
| R12 | Verletzung Betroffenenrechte | **Hoch** | Hoch |
| R1 | Unbefugter Zugriff auf Konversationen | **Mittel** | Niedrig |
| R3 | Prompt Injection / Datenexfiltration | **Mittel** | Mittel |
| R8 | Mangelnde Transparenz | **Mittel** | Mittel |
| R11 | Schatten-KI | **Mittel** | Mittel |
| R14 | Unzureichende Protokollierung | **Mittel** | Mittel |
| R4 | Verlust von Konversationsdaten | **Niedrig** | Niedrig |
| R10 | Diskriminierung / Bias | **Niedrig** | Niedrig |
| R13 | Übermittlung an Dritte | **Niedrig** | Niedrig |
| R15 | Fehlende Rate Limits | **Niedrig** | Niedrig |

### 4.4 Bewertung der Gesamtrisikosituation

Die Risikobewertung identifiziert:
- **1 "Sehr Hoch"-Risiko** (R2 Halluzination) -- inhärentes LLM-Risiko, nicht vollständig eliminierbar
- **5 "Hoch"-Risiken** (R5, R6, R7, R9, R12) -- davon 3 mit hohem Restrisiko (R5, R9, R12)
- **5 "Mittel"-Risiken** (R1, R3, R8, R11, R14)
- **4 "Niedrig"-Risiken** (R4, R10, R13, R15)

Das hohe Restrisiko bei R5 (Identitätsdiebstahl) wurde durch Entra ID OIDC (Phase 3, live seit 2026-03-24) signifikant gesenkt. R9 (Cross-Context Leakage) wurde durch ext-rbac (2026-03-23) und ext-access (2026-03-25) auf Mittel gesenkt -- granulare Zugriffskontrolle ist technisch verfuegbar, Aktivierung auf PROD steht aus.

Das hohe Restrisiko bei R12 (Betroffenenrechte) erfordert die zeitnahe Erstellung eines Löschkonzepts und eines Prozesses für Betroffenenanfragen -- beides ist unabhängig von Entra ID umsetzbar.

---

## 5. Abhilfemaßnahmen (Art. 35 Abs. 7 lit. d)

### 5.1 Implementierte technische Maßnahmen (TOMs)

Die nachfolgende Tabelle fasst die im Sicherheitskonzept (v0.6) dokumentierten und verifizierten Maßnahmen zusammen.

#### Verschlüsselung

| Maßnahme | Status | Referenz |
|----------|--------|----------|
| TLS 1.3 (ECDSA P-384) für Datenübertragung | IMPLEMENTIERT (alle Environments) | Sicherheitskonzept: Datenverschlüsselung. PROD HTTPS LIVE seit 2026-03-17. |
| Encryption-at-Rest AES-256 (PostgreSQL, Vespa, S3) | IMPLEMENTIERT | SEC-07, StackIT Default |
| HSTS (HTTP Strict Transport Security) | IMPLEMENTIERT | DEV/TEST: max-age=3600, PROD: max-age=31536000 |
| LLM-API über HTTPS | IMPLEMENTIERT | StackIT AI Model Serving |

#### Zugriffskontrolle

| Maßnahme | Status | Referenz |
|----------|--------|----------|
| Authentifizierung (Basic Auth) | IMPLEMENTIERT (temporär) | Sicherheitskonzept: Auth |
| Entra ID OIDC mit MFA | IMPLEMENTIERT (DEV + PROD, seit 2026-03-24) | Phase 3 abgeschlossen |
| PostgreSQL ACL (Netzwerk-Einschränkung) | IMPLEMENTIERT (SEC-01) | Alle Environments |
| Kubernetes Namespace-Isolation | IMPLEMENTIERT | Separate Namespaces pro Environment |
| RBAC-Rollen (Onyx-nativ) | IMPLEMENTIERT (Basic) | admin, basic, curator, limited |
| Admin-Only Zugriff auf Usage-Dashboard | IMPLEMENTIERT | ext-token: `Depends(current_admin_user)` |
| Container SecurityContext (runAsNonRoot) | IMPLEMENTIERT (SEC-06 Phase 2) | Alle Environments, Vespa = Ausnahme |

#### Netzwerksicherheit

| Maßnahme | Status | Referenz |
|----------|--------|----------|
| NetworkPolicies (Default-Deny) | IMPLEMENTIERT (DEV+TEST App-NS) | SEC-03, 5 Policies pro Namespace |
| NetworkPolicies (Monitoring-NS) | IMPLEMENTIERT (alle Cluster) | 8 Policies inkl. AlertManager-Webhook-Egress |
| NetworkPolicies (PROD App-NS) | IMPLEMENTIERT (seit 2026-03-24) | 7 Policies (Zero-Trust: Default-Deny + explizite Allow-Rules) |
| Security-Header (X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) | IMPLEMENTIERT | H8 |
| SSL-Redirect | IMPLEMENTIERT (DEV+TEST) | NGINX Ingress |

#### Datenintegrität

| Maßnahme | Status | Referenz |
|----------|--------|----------|
| Input-Validierung (Pydantic) | IMPLEMENTIERT | Onyx-nativ, alle API-Endpunkte |
| Logo-Upload: Magic-Byte-Validierung | IMPLEMENTIERT | ext-branding, kein SVG (XSS-Prävention) |
| SHA-gepinnte GitHub Actions | IMPLEMENTIERT | Supply-Chain-Sicherheit |
| CI/CD Input-Sanitierung (H11) | IMPLEMENTIERT | Docker-Tag-Regex + set -euo pipefail |

#### Verfügbarkeit

| Maßnahme | Status | Referenz |
|----------|--------|----------|
| Kubernetes Pod-Restart (automatisch) | IMPLEMENTIERT | Liveness/Readiness Probes |
| PostgreSQL HA (PROD: 3-Node Cluster + PITR) | IMPLEMENTIERT | StackIT Managed |
| API + Web Server HA (PROD: je 2 Replicas) | IMPLEMENTIERT | values-prod.yaml |
| Monitoring + Alerting (Prometheus, Grafana, AlertManager) | IMPLEMENTIERT | Alle Environments |
| Token Quotas mit Hard Stops | IMPLEMENTIERT | ext-token (HTTP 429) |

#### KI-spezifische Maßnahmen

| Maßnahme | Status | Referenz |
|----------|--------|----------|
| RAG-Architektur mit Quellenangabe | IMPLEMENTIERT | Onyx-nativ |
| Custom System Prompts (ext-prompts) | IMPLEMENTIERT | CORE #7, VÖB-spezifische Guardrails |
| Token-Tracking pro User/Modell (ext-token) | IMPLEMENTIERT | CORE #2, Kostenkontrolle |
| Datensouveränität (LLM auf StackIT) | IMPLEMENTIERT | Kein Drittland-Transfer |
| Whitelabel-Branding (ext-branding) | IMPLEMENTIERT | Vertrauensbildung, KI-Disclaimer |

### 5.2 Fehlende Maßnahmen (Handlungsbedarf)

| # | Maßnahme | Risikobezug | Priorität | Verantwortlich | Abhängigkeit |
|---|----------|-------------|-----------|---------------|-------------|
| M1 | **Entra ID OIDC + MFA aktivieren** | R5, R9 | KRITISCH | VÖB IT + CCJ | Entra ID Zugangsdaten von VÖB |
| M2 | **Löschkonzept erstellen** (DIN EN ISO/IEC 27555) | R12, R7 | HOCH | CCJ (Entwurf) + VÖB-DSB | VÖB muss Fristen bestätigen |
| M3 | **Prozess für Betroffenenrechte definieren** (Art. 15-22) | R12 | HOCH | CCJ + VÖB-DSB | Löschkonzept |
| M4 | **VVT erstellen** (Art. 30 DSGVO) | R7 | HOCH | CCJ (Entwurf) + VÖB | Keine |
| M5 | **AVV(s) abschließen** (VÖB-StackIT, VÖB-CCJ) | R13 | HOCH | VÖB + StackIT / CCJ | [AVV] VÖB Recht |
| M6 | **ext-rbac + ext-access implementieren** | R9 | HOCH | CCJ | ✅ IMPLEMENTIERT (ext-rbac 2026-03-23, ext-access 2026-03-25) |
| M7 | **NetworkPolicies PROD (App-NS)** | R1 | HOCH | CCJ | DNS/TLS PROD |
| M8 | **Datenschutzerklärung erstellen** | R8 | HOCH | VÖB Recht | Keine |
| M9 | **KI-Nutzungsrichtlinie erstellen** | R11, R7 | MITTEL | VÖB | Keine |
| M10 | **KI-Kompetenz-Schulung** (EU AI Act Art. 4) | R2, R10, R11 | MITTEL | VÖB | Art. 4 seit 02.02.2025 in Kraft |
| M11 | **Organisatorische Regelung Token-Tracking** | R6 | MITTEL | VÖB-DSB + VÖB HR | Keine |
| M12 | **TLS PROD aktivieren** | R1, R5 | HOCH | CCJ + GlobVill (DNS) | DNS-Einträge |
| M13 | **Zentralisierte Log-Aggregation** | R14 | MITTEL | CCJ | Keine |
| M14 | **Output-Filterung (PII in LLM-Antworten)** | R3, R9 | MITTEL | CCJ | Keine |
| M15 | **KI-Risikobewertung dokumentieren** (EU AI Act Art. 6 Abs. 3) | R8 | MITTEL | CCJ | Keine |
| M16 | **EU AI Act Art. 50 Transparenzhinweis** | R8 | MITTEL | CCJ | Deadline: 02.08.2026 |
| M17 | **CORS-Einschränkung (SEC-08)** | R5 | NIEDRIG | CCJ | Evaluierung Seiteneffekte |
| M18 | **Rate Limiting (SEC-09)** | R15 | NIEDRIG | CCJ | Keine |

### 5.3 Maßnahmenpriorisierung

**Vor PROD Go-Live (Pflicht):**
- M1: Entra ID — ✅ IMPLEMENTIERT (DEV + PROD seit 2026-03-24)
- M5: AVVs (blockiert durch VÖB Recht)
- M7: NetworkPolicies PROD — ✅ IMPLEMENTIERT (7 Policies onyx-prod seit 2026-03-24)
- M12: TLS PROD — ✅ IMPLEMENTIERT (HTTPS LIVE seit 2026-03-17)

**Innerhalb 3 Monaten nach PROD Go-Live:**
- M2: Löschkonzept
- M3: Prozess Betroffenenrechte
- M4: VVT
- M6: ext-rbac + ext-access — ✅ IMPLEMENTIERT (ext-rbac 2026-03-23, ext-access 2026-03-25)
- M8: Datenschutzerklärung

**Innerhalb 6 Monaten:**
- M9-M16: Organisatorische und Transparenzmaßnahmen

---

## 6. Betroffenenrechte (Art. 15-22 DSGVO)

### 6.1 Übersicht

| Recht | Artikel | Umsetzbarkeit | Status |
|-------|---------|---------------|--------|
| **Auskunft** | Art. 15 | Technisch möglich: Konversationen, Token-Usage, Identitätsdaten aus PostgreSQL exportierbar | Prozess nicht definiert |
| **Berichtigung** | Art. 16 | Technisch möglich: Name/E-Mail in PostgreSQL änderbar | Prozess nicht definiert |
| **Löschung** | Art. 17 | Technisch möglich: Onyx User-Löschung + Vespa `document.remove()`. Herausforderung: Embeddings, die auf Nutzerdaten basieren | [LÖSCHKONZEPT] |
| **Einschränkung** | Art. 18 | Technisch: User-Account deaktivieren (Onyx-nativ) | Prozess nicht definiert |
| **Datenübertragbarkeit** | Art. 20 | Eingeschränkt anwendbar: Art. 6(1)(f) als Rechtsgrundlage schließt Art. 20 nicht aus, aber Export-Format nicht standardisiert | Nicht implementiert |
| **Widerspruch** | Art. 21 | Anwendbar bei Art. 6(1)(f): Nutzer kann der Verarbeitung widersprechen. VÖB muss zwingende schutzwürdige Gründe nachweisen. | Prozess nicht definiert |
| **Automatisierte Entscheidung** | Art. 22 | Nicht anwendbar: Chatbot trifft keine automatisierten Entscheidungen mit rechtlicher Wirkung | Kein Handlungsbedarf |

### 6.2 Spezifische Herausforderungen bei KI-Systemen

**Embeddings und Löschung (Art. 17):**
Vektor-Embeddings kodieren Dokumenteninhalte in hochdimensionale numerische Vektoren. Eine gezielte Löschung einzelner personenbezogener Daten innerhalb eines Embeddings ist technisch nicht möglich. Stattdessen muss das gesamte Embedding gelöscht und ggf. ohne die betroffenen Daten neu erstellt werden. Vespa bietet hierfür die `document.remove()` API -- Embedding und Quelldokument werden als eine Löscheinheit behandelt.

**Auskunft und LLM-Verarbeitung (Art. 15):**
Chat-Eingaben werden an das LLM gesendet und verarbeitet. StackIT AI Model Serving speichert keine Nutzer-Prompts nach der Inferenz. Die Auskunftspflicht bezieht sich daher auf die in PostgreSQL gespeicherten Konversationsdaten, nicht auf die LLM-Verarbeitung selbst.

---

## 7. Stellungnahme des Datenschutzbeauftragten (Art. 35 Abs. 2)

[VÖB-DSB] -- Dieser Abschnitt ist vom VÖB-Datenschutzbeauftragten auszufüllen.

Gemäß Art. 35 Abs. 2 DSGVO ist der Datenschutzbeauftragte **während** der Durchführung der DSFA zu konsultieren. Die Stellungnahme des DSB sollte umfassen:

1. Bewertung der Rechtsgrundlage (Art. 6(1)(f) oder Alternative)
2. Bewertung der Risikobewertung (Abschnitt 4)
3. Bewertung der Maßnahmen (Abschnitt 5) -- insbesondere ob die Restrisiken akzeptabel sind
4. Empfehlung zur Freigabe oder zu zusätzlichen Maßnahmen
5. Stellungnahme zur Notwendigkeit einer Konsultation der Aufsichtsbehörde (Art. 36 DSGVO) -- insbesondere bei den hohen Restrisiken R5, R9, R12

**DSB-Stellungnahme:**

| Feld | Eingabe |
|------|---------|
| Name des DSB | [VÖB-DSB] |
| Datum der Konsultation | [VÖB-DSB] |
| Bewertung | [VÖB-DSB] |
| Empfehlung | [VÖB-DSB] |
| Unterschrift | [VÖB-DSB] |

---

## 8. Ergebnis und Empfehlung

### 8.1 Zusammenfassung

Die DSFA identifiziert **15 Risiken** für die Rechte und Freiheiten der betroffenen Personen. Davon sind:

- 1 Risiko mit Stufe "Sehr Hoch" (R2: LLM-Halluzination -- inhärentes KI-Risiko)
- 5 Risiken mit Stufe "Hoch" (R5, R6, R7, R9, R12)
- 5 Risiken mit Stufe "Mittel" (R1, R3, R8, R11, R14)
- 4 Risiken mit Stufe "Niedrig" (R4, R10, R13, R15)

Die Gesamtrisikosituation ist **beherrschbar**, sofern die unter Abschnitt 5.2 identifizierten fehlenden Maßnahmen umgesetzt werden. Die drei Risiken mit hohem Restrisiko (R5, R9, R12) erfordern vorrangige Aufmerksamkeit.

### 8.2 Voraussetzungen für PROD Go-Live

Aus datenschutzrechtlicher Sicht sollten folgende Maßnahmen **vor** dem produktiven Einsatz (PROD Go-Live mit echten Nutzerdaten) abgeschlossen sein:

| # | Maßnahme | Status |
|---|----------|--------|
| 1 | Entra ID OIDC + MFA (R5) | ✅ IMPLEMENTIERT (DEV + PROD seit 2026-03-24) |
| 2 | AVV VÖB-StackIT (Art. 28) | [AVV] |
| 3 | AVV VÖB-CCJ (Art. 28) | [AVV] |
| 4 | TLS PROD (Verschlüsselung im Transit) | ✅ IMPLEMENTIERT (HTTPS LIVE seit 2026-03-17) |
| 5 | NetworkPolicies PROD (App-NS) | ✅ IMPLEMENTIERT (7 Policies onyx-prod seit 2026-03-24) |
| 6 | Löschkonzept (Entwurf, VÖB-Bestätigung) | [LÖSCHKONZEPT] |
| 7 | Datenschutzerklärung (Informationspflichten Art. 13) | VÖB Recht |
| 8 | Freigabe dieser DSFA durch VÖB-DSB | [VÖB-DSB] |

### 8.3 Empfehlung

**Empfehlung des Erstellers (CCJ):**

1. **Freigabe durch VÖB-DSB einholen** -- Diese DSFA ist ein Entwurf. Der VÖB-DSB muss gemäß Art. 35 Abs. 2 konsultiert werden und die DSFA freigeben.

2. **Konsultation der Aufsichtsbehörde (Art. 36 DSGVO)** -- Bei drei hohen Restrisiken (R5, R9, R12) muss der VÖB-DSB prüfen, ob eine vorherige Konsultation der zuständigen Aufsichtsbehörde erforderlich ist. Art. 36 Abs. 1: "Der Verantwortliche konsultiert [...] die Aufsichtsbehörde, sofern aus der [DSFA] hervorgeht, dass die Verarbeitung ein hohes Risiko zur Folge hätte, sofern der Verantwortliche keine Maßnahmen zur Eindämmung des Risikos trifft."
   - [VÖB-DSB] -- Diese Bewertung obliegt dem DSB. Die hohen Restrisiken bei R5 und R9 werden durch die Aktivierung von Entra ID (Phase 3) signifikant reduziert. R12 erfordert das Löschkonzept und den Betroffenenrechte-Prozess.

3. **DSFA regelmäßig überprüfen** -- Art. 35 Abs. 11 DSGVO verlangt eine regelmäßige Überprüfung. Empfohlen: mindestens jährlich oder bei wesentlichen Systemänderungen (neues LLM-Modell, neue Datenkategorien, Erweiterung des Nutzerkreises).

4. **Maßnahmenplan umsetzen** -- Die 18 identifizierten Maßnahmen (Abschnitt 5.2) nach der Priorisierung in Abschnitt 5.3 umsetzen. Kritisch: M1 (Entra ID), M2 (Löschkonzept), M3 (Betroffenenrechte), M5 (AVVs).

### 8.4 Freigabe

| Feld | Eingabe |
|------|---------|
| Ersteller (CCJ) | Nikolaj Ivanov, CCJ Development UG |
| Datum | 2026-03-14 |
| Freigabe VÖB-DSB | [VÖB-DSB] |
| Datum Freigabe | [VÖB-DSB] |
| Nächste Überprüfung | [VÖB-DSB] |

---

## Anhang A: Referenzen

| Dokument | Fundstelle |
|----------|-----------|
| Sicherheitskonzept v0.6 | `docs/sicherheitskonzept.md` |
| Betriebskonzept v0.6 | `docs/betriebskonzept.md` |
| Compliance-Research (2026-03-09) | `docs/referenz/compliance-research.md` |
| Monitoring-Konzept | `docs/referenz/monitoring-konzept.md` |
| Extension-Entwicklungsplan | `docs/referenz/ext-entwicklungsplan.md` |
| RBAC-Rollenmodell | `docs/referenz/rbac-rollenmodell.md` |
| DNS/TLS-Runbook | `docs/runbooks/dns-tls-setup.md` |

## Anhang B: Regulatorische Grundlagen

| Regelwerk | Fundstelle |
|-----------|-----------|
| DSGVO (Datenschutz-Grundverordnung) | Verordnung (EU) 2016/679 |
| BDSG (Bundesdatenschutzgesetz) | BGBl. I 2017, S. 2097 |
| EU AI Act | Verordnung (EU) 2024/1689 |
| DSK Muss-Liste DSFA V1.1 | 17.10.2018, Nr. 10 |
| DSK Orientierungshilfe KI und Datenschutz | 06.05.2024 |
| BfDI Handreichung "KI in Behörden" | 22.12.2025 |
| LfDI BW "Rechtsgrundlagen bei KI" V2.0 | 17.10.2024 |
| Standard-Datenschutzmodell (SDM) V3.1 | DSK |
| DSK Kurzpapier Nr. 5 "DSFA" | DSK |
| DIN EN ISO/IEC 27555:2025-09 | Vormals DIN 66398:2016-05 |
| EuGH C-34/21 | 30.03.2023 (Paragraph 26 BDSG) |
| EDPB/WP248 | Leitlinien zur DSFA |
| BSI C5 Type 2 (StackIT) | Zertifizierung |

## Anhang C: Offene Marker

| Marker | Anzahl | Beschreibung |
|--------|--------|-------------|
| `[VÖB-DSB]` | 14 | Input oder Freigabe durch den VÖB-Datenschutzbeauftragten erforderlich |
| `[KLÄRUNG]` | 4 | Fachliche Klärung mit VÖB erforderlich |
| `[LÖSCHKONZEPT]` | 8 | Abhängig vom noch zu erstellenden Löschkonzept |
| `[AVV]` | 4 | Abhängig vom AVV-Status (Art. 28 DSGVO) |
