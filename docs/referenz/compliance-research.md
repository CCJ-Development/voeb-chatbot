# Compliance-Research — Vollständige Findings (2026-03-09)

Ergebnis einer Tiefenrecherche mit 5 parallelen Web-Recherche-Agenten.
Zweck: Validierung der geplanten Compliance-Dokumente vor Erstellung.

---

## Inhaltsverzeichnis

1. [Regulatorische Einordnung: Was gilt für VÖB?](#1-regulatorische-einordnung)
2. [BAIT-Compliance-Matrix: Korrekturen + vollständige Kapitelstruktur](#2-bait-compliance-matrix)
3. [BSI IT-Grundschutz: Korrektes Modul-Mapping](#3-bsi-it-grundschutz)
4. [DSFA: Struktur, Rechtsgrundlage, Risiken](#4-dsfa-datenschutz-folgenabschätzung)
5. [Löschkonzept: Fristen, Normen, Sonderfälle](#5-löschkonzept)
6. [EU AI Act: Bereits geltende Pflichten](#6-eu-ai-act)
7. [Fehlende Dokumente: Must-Have vs. Nice-to-Have](#7-fehlende-dokumente-must-have-vs-nice-to-have)
8. [Quellen](#8-quellen)

---

## 1. Regulatorische Einordnung

### VÖB ist KEIN Kreditinstitut

Der VÖB (Bundesverband Öffentlicher Banken Deutschlands **e.V.**) ist:
- Ein **eingetragener Verein** (Spitzenverband), KEIN Kreditinstitut i.S.d. §1 KWG
- **NICHT BaFin-beaufsichtigt** (seine 64 Mitgliedsinstitute sind es)
- **KEIN Finanzunternehmen** i.S.d. Art. 2 DORA
- **NICHT direkt BAIT/DORA-pflichtig**
- **KEIN GwG-Verpflichteter** (führt keine Finanzgeschäfte durch)

### Welche Gesetze gelten direkt?

| Regelwerk | Anwendbar? | Begründung |
|-----------|-----------|------------|
| **DSGVO** | **JA**, vollumfänglich | Gilt für jede Organisation die PII verarbeitet |
| **BDSG** | **JA** | Nationale Ergänzung zur DSGVO |
| **EU AI Act** | **JA** (Limited Risk) | VÖB ist "Deployer" eines KI-Systems. Art. 4 seit 02.02.2025 in Kraft |
| **HGB §257** | JA, für eigene Geschäftsunterlagen | Aufbewahrungspflichten (6/10 Jahre) |
| **AO §147** | JA, für steuerlich relevante Unterlagen | Aufbewahrungspflichten (8/10 Jahre) |
| **TDDDG §25** | JA, aber geringes Risiko | Session-Cookies = "technisch notwendig" → keine Einwilligung nötig |
| **BAIT** | **NEIN** (nicht direkt) | Kein KWG-Institut. Freiwillige Orientierung empfohlen |
| **DORA** | **NEIN** (nicht direkt) | Kein Finanzunternehmen i.S.d. Art. 2. Aber: Wenn Chatbot als Service für Mitgliedsbanken → ggf. IKT-Drittdienstleister prüfen |
| **MaRisk** | **NEIN** (nicht direkt) | Gilt für Institute, nicht Verbände |
| **NIS2** | **NEIN** | Finanzsektor von NIS2 ausgenommen (DORA-Vorrang). VÖB als e.V. erreicht zudem Schwellenwerte nicht (50+ MA oder 10M+ Umsatz) |
| **KWG** | **NEIN** | VÖB ist kein Institut |
| **GwG** | **NEIN** | VÖB ist kein Verpflichteter i.S.d. §2 GwG |
| **eIDAS 2.0** | **NEIN** (derzeit) | Akzeptanzpflicht für Private erst ~2027. Standard-OIDC mit Entra ID reicht |
| **HinSchG** | **NEIN** (nicht chatbot-relevant) | Organisatorische Pflicht für VÖB, aber unabhängig vom Chatbot |

### Warum trotzdem BAIT/DORA/BSI-Orientierung?

1. **Reputationsrisiko:** VÖB berät Banken in regulatorischen Fragen — eigenes IT-System muss mindestens den empfohlenen Standard erfüllen
2. **Vertragliche Flow-Down:** Mitgliedsbanken (Landesbanken, Förderbanken) sind DORA-pflichtig. Wenn sie den Chatbot nutzen, fließen Anforderungen indirekt über Verträge zurück
3. **Audit-Readiness:** Bei VÖB-Abnahme wird Branchenstandard erwartet
4. **DORA Kap. V (IKT-Drittdienstleister):** Falls Chatbot als Service für Mitgliedsbanken bereitgestellt wird, könnte VÖB als IKT-Drittdienstleister unter DORA fallen — **zu prüfen mit VÖB**

### Empfohlene Formulierung in Dokumenten

> "Der VÖB unterliegt als eingetragener Verein primär der DSGVO, dem BDSG und dem EU AI Act. Da der VÖB als Spitzenverband der öffentlichen Banken im regulatorischen Umfeld der Finanzbranche agiert, orientiert sich dieses Dokument darüber hinaus an den Anforderungen der BAIT/DORA sowie des BSI IT-Grundschutzes, um den Erwartungen der Mitgliedsinstitute und Aufsichtsbehörden zu entsprechen."

---

## 2. BAIT-Compliance-Matrix

### BAIT: Aktueller Stand

- **Rundschreiben 10/2017 (BA)**, Fassung vom **16. Dezember 2024**
- NICHT "BAIT 2022" — es gibt keine eigenständige 2022-Version
- Wesentliche Erweiterung am 16.08.2021: Kapitel 5, 10, 11 hinzugefügt
- Letzte Änderung 16.12.2024: Kapitel 11 aufgehoben (→ DORA)
- **BAIT wird vollständig aufgehoben am 31.12.2026** (DORA-Übergang)
- Seit 17.01.2025 gilt DORA für CRR-Institute; BAIT gilt noch für Restgruppe bis 01.01.2027

### Korrekte Kapitelstruktur (12 Kapitel, 11 aktiv)

| Kap. | Offizieller Titel | Relevanz für VÖB-Chatbot |
|------|-------------------|--------------------------|
| 1 | IT-Strategie | Mittel — ADR-001, Meilensteinplan zeigen strategische Planung |
| 2 | IT-Governance | Hoch — Change Management, 4-Augen-Prinzip, Branch Protection |
| 3 | Informationsrisikomanagement | Hoch — Cloud-Audit, SEC-01 bis SEC-07, DSFA |
| 4 | Informationssicherheitsmanagement | Hoch — Sicherheitskonzept, Verschlüsselung, NetworkPolicies |
| **5** | **Operative Informationssicherheit** | **Hoch — Schwachstellenscanning, Logging, Monitoring (hier große Lücken!)** |
| **6** | **Identitäts- und Rechtemanagement** | **Hoch — Entra ID, RBAC, ext-rbac (NICHT "Benutzerberechtigungsmanagement")** |
| 7 | IT-Projekte und Anwendungsentwicklung | Hoch — CI/CD, Testing, Code-Review, Branch Protection |
| 8 | IT-Betrieb (inkl. Datensicherung) | Hoch — Betriebskonzept, Helm, Backup, Rollback |
| 9 | Auslagerungen und sonstiger Fremdbezug von IT-Dienstleistungen | **Sehr hoch — CCJ als Dienstleister, StackIT als Unterauftragsverarbeiter** |
| **10** | **IT-Notfallmanagement** | **Hoch — Incident Response, Disaster Recovery (hier Lücken!)** |
| ~~11~~ | ~~Management der Beziehungen mit Zahlungsdienstnutzern~~ | ~~AUFGEHOBEN (16.12.2024, → DORA)~~ |
| **12** | **Kritische Infrastrukturen** | **Niedrig — VÖB ist kein KRITIS-Betreiber. Aber: Mitgliedsbanken ggf. schon** |

### BaFin KI-Orientierungshilfe (18.12.2025)

Aktuellste BaFin-Guidance für KI-Systeme — baut auf DORA auf (nicht BAIT). Nicht bindend, aber faktisch erwartungsbildend.

Kernanforderungen:
- KI in bestehendes IKT-Risikomanagement integrieren (nicht isoliert behandeln)
- **Lifecycle-Ansatz:** Datenakquise → Modellentwicklung → Betrieb → Stilllegung
- **Governance:** Leitungsorgane müssen KI/IKT-Wissen aufbauen (Modelldrift, Systemlimitationen)
- **Testing:** Versionskontrolle, Adversarial Testing, Stress Tests, statische Code-Analyse
- **Monitoring:** Concept Drift + Data Drift überwachen, automatisierte Alerts, detailliertes Logging
- **Cybersecurity:** Schutz gegen Model Extraction, Inversion, unautorisierter API-Zugriff
- **Shadow AI:** Alle KI-Systeme identifizieren inkl. Abteilungs-Tools

### Status-Labels für Compliance-Matrix

Empfohlener 6-Label-Satz:

| Label | Bedeutung |
|-------|-----------|
| ERFÜLLT | Anforderung vollständig umgesetzt |
| TEILWEISE ERFÜLLT | Teilweise umgesetzt, Restmaßnahmen identifiziert |
| IN UMSETZUNG | Aktiv in Bearbeitung |
| GEPLANT | Auf Roadmap, noch nicht begonnen |
| OFFEN | Noch nicht bewertet/bearbeitet |
| NICHT ANWENDBAR | Trifft auf System/Konstellation nicht zu |

---

## 3. BSI IT-Grundschutz

### Edition

**Edition 2023** (veröffentlicht 01.02.2023) ist aktuell. Keine 2024-Edition; BSI kommuniziert Änderungen via Errata. 111 Module über 10 Schichten.

### Vollständige Modulliste (validiert gegen Edition 2023)

#### MUSS-Module (14 Stück)

| # | Modul-ID | Name | Warum relevant |
|---|----------|------|----------------|
| 1 | **APP.4.4** | Kubernetes | SKE Cluster, Namespace-Isolation, RBAC, Pod Security |
| 2 | **SYS.1.6** | Containerisierung | SEC-06, Image-Provenance, keine Root-Container |
| 3 | **APP.4.3** | Relationale Datenbanken | PostgreSQL (StackIT PG Flex), SQL Injection, Encryption |
| 4 | **OPS.2.2** | Cloud-Nutzung | StackIT als Cloud-Provider, Shared Responsibility |
| 5 | **ORP.4** | Identitäts- und Berechtigungsmanagement | Entra ID, RBAC, ext-rbac |
| 6 | **CON.1** | Kryptokonzept | TLS (blockiert), Encryption at Rest (SEC-07) |
| 7 | **CON.3** | Datensicherungskonzept | PG PITR, Vespa, etcd, Object Storage Backup |
| 8 | **OPS.1.1.3** | Patch- und Änderungsmanagement | CI/CD, Branch Protection, Helm Upgrades |
| 9 | **OPS.1.1.5** | Protokollierung | Logging (aktuell: Pod-Logs, geplant: zentral) |
| 10 | **NET.1.1** | Netzarchitektur und -design | NetworkPolicies, PG ACL, LB-Isolation |
| 11 | **APP.3.1** | Webanwendungen und Webservices | FastAPI Backend + Next.js Frontend |
| 12 | **APP.3.2** | Webserver | NGINX Ingress Controller, Security-Header |
| 13 | **DER.1** | Detektion von sicherheitsrelevanten Ereignissen | Monitoring (aktuell: nur CI/CD Smoke Tests) |
| 14 | **DER.2.1** | Behandlung von Sicherheitsvorfällen | Incident Response Plan |

#### SOLL-Module (8 Stück)

| # | Modul-ID | Name | Warum relevant |
|---|----------|------|----------------|
| 15 | **INF.2** | Rechenzentrum sowie Serverraum | StackIT-Verantwortung (Shared Responsibility) |
| 16 | **CON.10** | Entwicklung von Webanwendungen | Onyx-Fork Entwicklung, ext/-Framework |
| 17 | **NET.3.2** | Firewall | NetworkPolicies als K8s-Firewall |
| 18 | **OPS.1.1.2** | Ordnungsgemäße IT-Administration | Admin-Prozesse, Privileged Access |
| 19 | **OPS.1.1.4** | Schutz vor Schadprogrammen | Container Image Scanning (aktuell: nicht implementiert) |
| 20 | **DER.4** | Notfallmanagement | Business Continuity, Disaster Recovery |
| 21 | **CON.8** | Software-Entwicklung | Custom Extension Development |
| 22 | **OPS.1.1.6** | Software-Tests und -Freigaben | CI/CD Pipeline, Testing-Strategie |

### Top-Anforderungen pro MUSS-Modul

#### APP.4.4 Kubernetes (21 Anforderungen)

Basis (MUSS):
- **A1** Planung der Separierung der Anwendungen — Namespace/Cluster/Netzwerk-Trennung nach Schutzbedarf
- **A3** Identitäts- und Berechtigungsmanagement — Alle Aktionen authentifiziert+autorisiert, Least Privilege
- **A4** Separierung von Pods — Kernel-Isolation (Namespaces, cgroups)
- **A5** Datensicherung im Cluster — Backup persistent volumes, K8s-Config, etcd

Standard (SOLL):
- **A7** Separierung der Netze — Getrennte Netze für Node-Admin, Control Plane, App-Services; Whitelist-Ansatz
- **A9** Nutzung von K8s Service-Accounts — Kein Default-SA; jede App eigener SA mit minimalen Rechten

#### SYS.1.6 Containerisierung (27 Anforderungen)

Basis (MUSS):
- **A1** Planung des Container-Einsatzes — Container-Strategie, erlaubte Base Images, Registry-Policies
- **A3** Sicherer Einsatz — Keine unnötigen Privilegien, Read-Only Filesystems wo möglich, keine Root-Container
- **A4** Planung der Image-Bereitstellung — Trusted Registry, Image Signing, Vulnerability Scanning

Standard (SOLL):
- **A7** Persistenz von Protokollierungsdaten — Container-Logs müssen Pod-Lifetime überleben
- **A8** Sichere Speicherung von Zugangsdaten — Secrets Management, keine Credentials in Images

#### APP.4.3 Relationale Datenbanken (25 Anforderungen)

Basis (MUSS):
- **A3** Minimalprivileg und Funktionstrennung — Least Privilege für DB-User
- **A5** Verschlüsselung von Verbindungen — TLS für alle DB-Verbindungen
- **A7** Schutz vor SQL-Injection — Input Validation, Parameterized Queries
- **A9** Datensicherung — Regelmäßige Backups, Transaction-Log-Backup

#### OPS.2.2 Cloud-Nutzung

Basis (MUSS):
- **A1** Cloud-Nutzungs-Strategie
- **A3** Service-Definition — Was liefert StackIT, SLAs, Verantwortlichkeiten
- **A4** Verantwortungsbereiche und Schnittstellen — Shared Responsibility Model dokumentieren

Standard (SOLL):
- **A8** Sorgfältige Auswahl Cloud-Diensteanbieters — Due Diligence (StackIT: BSI C5 Type 2)

#### ORP.4 Identitäts- und Berechtigungsmanagement

Basis (MUSS):
- **A1** Regelung für Einrichtung/Löschung von Benutzerkennungen
- **A2** Einrichtung, Änderung, Entzug von Berechtigungen
- **A3** Dokumentation der Benutzerkennungen und Rechteprofile
- **A6** Passwortrichtlinie

Standard (SOLL):
- **A14** Entwicklung eines Authentisierungskonzepts — Relevant für Entra ID OIDC

#### CON.1 Kryptokonzept

Basis (MUSS):
- **A1** Auswahl geeigneter kryptographischer Verfahren — BSI TR-02102
- **A2** Datensicherung kryptographischer Schlüssel
- **A4** Geeignetes Schlüsselmanagement

#### CON.3 Datensicherungskonzept

Basis (MUSS):
- **A1** Erhebung der Einflussfaktoren — Datenvolumen, Änderungsrate, Verfügbarkeitsanforderungen
- **A2** Festlegung der Verfahrensweise — Backup-Verfahren, Medien, Retention
- **A4** Erstellung von Datensicherungsplänen — Pro System dokumentiert
- **A5** Regelmäßige Datensicherung

#### OPS.1.1.5 Protokollierung

Basis (MUSS):
- **A1** Sicherheitsrichtlinie für Protokollierung
- **A3** Konfiguration — Alle sicherheitsrelevanten Ereignisse protokolliert
- **A4** Zeitsynchronisation — NTP für alle Systeme

Standard (SOLL):
- **A6** Zentrale Protokollierungsinfrastruktur — **Aktuell NICHT erfüllt** (nur Pod-Logs)

### BSI Grundschutz — Ist es Pflicht?

Nicht direkt Pflicht für VÖB (e.V.), aber de facto Standard:
- MaRisk AT 7.2 Tz. 2 nennt BSI IT-Grundschutz und ISO 27001 als "gängige Standards"
- BAIT referenziert BSI Grundschutz explizit
- DORA ersetzt BAIT, eliminiert aber NICHT den Bedarf an BSI Grundschutz
- StackIT hat **BSI C5 Type 2** — prominentes Audit-Asset, überall referenzieren

### Kein BSI-Modul für AI/ML

Stand Edition 2023: Kein dedizierter Baustein für KI/ML. BSI hat separate Publikationen (Whitepapers zu KI-Transparenz, Bias, Erklärbarkeit; QUAIDAL-Katalog). Empfehlung: KI-Risiken als "Ergänzende Sicherheitsanalyse" behandeln.

---

## 4. DSFA (Datenschutz-Folgenabschätzung)

### DSFA ist PFLICHT

Drei unabhängige Trigger:

1. **DSK Muss-Liste Nr. 10** (V1.1, 17.10.2018): "Einsatz von künstlicher Intelligenz zur Verarbeitung personenbezogener Daten zur Steuerung der Interaktion mit den Betroffenen" — trifft direkt auf KI-Chatbot zu
2. **Art. 35 Abs. 1 DSGVO**: "neue Technologien" — LLMs/Generative AI qualifizieren eindeutig
3. **EDPB/WP248 Kriterien** (mindestens 2 = DSFA nötig): (a) Innovative Technologie, (b) Systematisches Monitoring (Chat-Logging), (c) Machtgefälle (Arbeitgeber-Tool, eingeschränkte Verweigerungsmöglichkeit)

### Korrekte DSFA-Struktur (6-teilig, nach Art. 35 Abs. 7)

| # | Abschnitt | Art. 35 Abs. 7 | Inhalt |
|---|-----------|----------------|--------|
| 0 | **Schwellenwertanalyse** | — | Warum DSFA nötig: DSK Nr. 10, Art. 35 Abs. 1, WP248 |
| 1 | **Systematische Beschreibung** | lit. a | Datenkategorien, Datenflüsse, Systeme, Speicherorte, Betroffene, Aufbewahrungsfristen |
| 2 | **Rechtsgrundlagen-Prüfung** | lit. a (Teil) | Art. 6 Abs. 1 lit. f + Interessenabwägung |
| 3 | **Notwendigkeit und Verhältnismäßigkeit** | lit. b | Alternativen, Datenminimierung, Zweckbindung |
| 4 | **Risikobewertung** | lit. c | 13 Risiken (siehe unten), Severity x Likelihood Matrix |
| 5 | **Abhilfemaßnahmen** | lit. d | TOMs, Restrisiko, Monitoring |
| + | **Stellungnahme DSB** | Art. 35 Abs. 2 | VÖB-DSB muss WÄHREND der DSFA konsultiert werden |
| + | **Betroffenenrechte** | Art. 15-22 | Wie werden Auskunft, Löschung, etc. in Embeddings/Vespa erfüllt? |
| + | **Ergebnis und Freigabe** | — | VÖB-Freigabe |

### Rechtsgrundlage

**Korrekt: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse)**

Drei-Stufen-Test:
1. **Berechtigtes Interesse:** VÖB hat legitimes Interesse an KI-gestütztem Informationsabruf zur Effizienzsteigerung
2. **Erforderlichkeit:** Verarbeitung von Identität, Chat-Inhalt, Dokumenten ist für Chatbot-Service nötig
3. **Interessenabwägung:** Maßnahmen (Datenminimierung, Zugriffskontrolle, Löschfristen, kein Performance-Monitoring) kippen Abwägung zugunsten VÖB

**NICHT Art. 6 Abs. 1 lit. b** (Vertragserfüllung): KI-Chatbot ist freiwilliges Produktivitäts-Tool, nicht vertraglich zwingend. EDPB warnt vor Über-Berufung auf lit. b bei Arbeitgeber-Datenverarbeitung.

**NICHT Art. 6 Abs. 1 lit. e** (öffentliches Interesse): VÖB ist privatrechtlicher Verein (e.V.), keine Behörde.

**Paragraph 26 BDSG NICHT verwenden:** EuGH C-34/21 (30.03.2023) hat Paragraph 26 Abs. 1 S. 1 BDSG für **europarechtswidrig** erklärt.

### Vollständiger Risikokatalog (13 Risiken)

#### Vertraulichkeit
| ID | Risiko | Schwere | Quelle |
|----|--------|---------|--------|
| R1 | Unbefugter Zugriff auf Konversationsdaten | Hoch | Standard |
| R3 | Prompt Injection → Datenexfiltration | Hoch | heydata: meldepflichtige Datenschutzverletzung Art. 33 |
| R5 | Identitätsdiebstahl durch schwache Auth | Hoch | Standard (mitigiert durch Entra ID + MFA) |
| R9 | Unbeabsichtigte Offenlegung sensibler Daten im LLM-Output (Cross-Context Leakage) | Hoch | EDPB LLM Guidance |

#### Integrität
| ID | Risiko | Schwere | Quelle |
|----|--------|---------|--------|
| R2 | LLM-Halluzination / falsche Informationen | Hoch | Besonders relevant in Banking |
| R10 | Diskriminierung / Bias | Mittel | DSK Orientierungshilfe KI |

#### Verfügbarkeit
| ID | Risiko | Schwere | Quelle |
|----|--------|---------|--------|
| R4 | Verlust von Konversationsdaten | Mittel | Standard |

#### Zweckbindung / Datenminimierung
| ID | Risiko | Schwere | Quelle |
|----|--------|---------|--------|
| R6 | Profilbildung durch Nutzungsmetriken | Hoch | Beschäftigtendatenschutz |
| R7 | Verletzung der Zweckbindung | Hoch | ISiCO: "zweckoffen angelegte KI-Nutzung" = Kernrisiko |

#### Transparenz / Betroffenenrechte
| ID | Risiko | Schwere | Quelle |
|----|--------|---------|--------|
| R8 | Mangelnde Transparenz / Blackbox | Mittel | DSK OH KI |
| R12 | Verletzung von Betroffenenrechten (Art. 15/17 in Embeddings) | Hoch | EDPB, BfDI |

#### Organisatorisch
| ID | Risiko | Schwere | Quelle |
|----|--------|---------|--------|
| R11 | Schatten-KI / unkontrollierte Nutzung | Mittel | ISiCO |
| R13 | Übermittlung an Dritte | Niedrig | Verifiziert: StackIT = self-hosted |

### Risikogruppen nach Standard-Datenschutzmodell (SDM V3.1)

Die 7 SDM-Schutzziele:
1. **Datenminimierung** → R6, R7
2. **Verfügbarkeit** → R4
3. **Integrität** → R2, R10
4. **Vertraulichkeit** → R1, R3, R5, R9
5. **Nichtverkettung** → R6, R7 (Zweckbindung)
6. **Transparenz** → R8, R11
7. **Intervenierbarkeit** → R12 (Betroffenenrechte)

### DSFA-Templates und KI-Leitfäden

| Ressource | Herausgeber | Datum |
|-----------|-------------|-------|
| DSFA-Bericht-Vorlage (Word) | BayLfD | aktuell |
| DSK Kurzpapier Nr. 5 "DSFA" | DSK | aktuell |
| Standard-Datenschutzmodell (SDM) V3.1 | DSK | aktuell |
| **DSK Orientierungshilfe "KI und Datenschutz"** | DSK | **06.05.2024** |
| **BfDI Handreichung "KI in Behörden"** | BfDI | **22.12.2025** |
| **LfDI BW "Rechtsgrundlagen bei KI" V2.0** | LfDI Baden-Württemberg | **17.10.2024** |
| CNIL PIA Tool (Open Source, deutsch) | CNIL (Frankreich) | aktuell |
| **Bitkom Praxisleitfaden "KI und Datenschutz" V2.0** | Bitkom | **2025** |

---

## 5. Löschkonzept

### DIN-Norm-Status

- **DIN 66398:2016-05** wurde im **September 2025 zurückgezogen**
- Ersetzt durch **DIN EN ISO/IEC 27555:2025-09**
- Inhaltlich identisch, gleiche Vorgehensweise
- **Im Löschkonzept referenzieren:** "orientiert sich an DIN EN ISO/IEC 27555:2025-09 (vormals DIN 66398:2016-05)"

### Struktur nach DIN EN ISO/IEC 27555

1. **Datenarten (Datenobjekte)** — Kategorisierung nach Verarbeitungszweck
2. **Löschklassen** — Gruppierung mit identischen Fristen (z.B. LK-24H, LK-90D, LK-12M)
3. **Löschregeln** — Je Datenart: Startzeitpunkt (Trigger) + Regellöschfrist + Löschklasse
4. **Umsetzungsregeln** — Technische Zuordnung: System, Methode, Verantwortlich
5. **Nachweispflichten** — Löschprotokoll, Audit-Trail
6. **Ausnahmeregeln** — Gesetzliche Aufbewahrung, laufende Verfahren, Art. 17 Abs. 3

### Gesetzliche Aufbewahrungsfristen

| Gesetz | Frist | Gegenstand | VÖB-relevant? |
|--------|-------|-----------|----------------|
| HGB §257 | **10 Jahre** | Jahresabschlüsse, Buchungsbelege | Für eigene Geschäftsunterlagen, NICHT für Chatbot-Daten |
| HGB §257 | **6 Jahre** | Handelsbriefe (inkl. E-Mails) | Nur wenn Chats als Handelsbriefe qualifizieren (unwahrscheinlich) |
| AO §147 | **10 Jahre** | Buchungsbelege (BEG IV → 8 Jahre, SchwarzArbMoDiG Aug 2025 → zurück auf 10 für Banken) | Für steuerlich relevante Unterlagen, NICHT für Chatbot-Daten |
| AO §147 | **6 Jahre** | Sonstige aufbewahrungspflichtige Unterlagen | Analog |
| GwG §8 | **5 Jahre** (ab Ende Geschäftsbeziehung, max 10 Jahre dann vernichten) | Geldwäsche-Dokumentation | **NEIN** — VÖB ist kein GwG-Verpflichteter |
| DSGVO Art. 5(1)(e) | **So kurz wie möglich** | Speicherbegrenzungsgrundsatz | JA — Grundprinzip |
| DSGVO Art. 17 | **Ohne ungebührliche Verzögerung** | Recht auf Löschung | JA |
| BDSG §35 | Einschränkung statt Löschung wenn technisch unverhältnismäßig | Nationale Ergänzung | JA |

**Wichtig:** Chat-Konversationen sind im Regelfall KEINE Buchungsbelege oder Handelsbriefe. Sie fallen primär unter DSGVO (Zweckbindung, Speicherbegrenzung). HGB/AO-Mindestfristen greifen für Chatbot-Daten NICHT direkt.

### Bewertung der vorgeschlagenen Aufbewahrungsfristen

| Datenkategorie | Vorschlag | Bewertung | Empfehlung |
|----------------|-----------|-----------|------------|
| **Identitätsdaten (Accounts)** | [VÖB klären] | Korrekt | **Beschäftigungsdauer + 3 Jahre** (§195 BGB Verjährung). VÖB muss bestätigen. |
| **Konversationsdaten (Chats)** | 12 Monate | Konservativ, aber vertretbar. Branchenüblich: 90 Tage bis 12 Monate. | Bei 12 Monaten bleiben — Bankenkontext rechtfertigt längere Nachweisbarkeit. |
| **Dokumente / Embeddings** | Quelldauer + 30 Tage | Grundsätzlich richtig, aber differenzieren | (a) interne Wissensbasis = OK, (b) gesetzl. Aufbewahrungspflicht = Originale im DMS, nicht im Chatbot |
| **API-Logs** | 90 Tage | Zu pauschal | **Differenzieren:** Standard-Logs = 90 Tage. **Security-/Audit-Logs = 6-12 Monate** |
| **Session-Daten** | 24h nach Ende | Völlig angemessen | Beibehalten |

### Löschmethoden

| System | Methode | Ausreichend? |
|--------|---------|-------------|
| **PostgreSQL** | DELETE + Autovacuum + Encryption-at-Rest (StackIT AES-256) | **JA** für normalen Schutzbedarf. Kein VACUUM FULL nötig. |
| **Vespa** | `document.remove()` per Document API | **JA** — Embedding + Quelldokument = eine "Löscheinheit" |
| **S3 Object Storage** | Lifecycle Policies | **JA** — Kein Versioning ohne Ablauf-Policy |
| **Logs** | Standard Log-Rotation (K8s-nativ oder Loki Retention) | **JA** für normalen Schutzbedarf |

BSI CON.6 Schutzbedarf-Differenzierung:
- **Normal:** Logisches Löschen + Freigabe Speicherplatz = ausreichend (bei Encryption-at-Rest)
- **Hoch:** Überschreiben mit Zufallsdaten (1x reicht für SSDs)
- **Sehr hoch:** Physische Vernichtung oder kryptographisches Löschen

### Sonderfälle (vollständig)

| # | Sonderfall | Details |
|---|-----------|---------|
| 1 | **Mitarbeiter-Austritt** | Account sofort deaktivieren, löschen nach Frist (Empf.: 30 Tage). Chats: reguläre Frist abwarten |
| 2 | **Art. 17 DSGVO Löschanfrage** | Prozess mit Frist (1 Monat). Prüfung Art. 17 Abs. 3. Falls Aufbewahrungspflicht → Einschränkung statt Löschung |
| 3 | **Aufbewahrungspflichten** (§35 Abs. 3 BDSG) | Dokumentieren: welche Datensätze, warum gesperrt, bis wann |
| 4 | **Backup-Löschung** | EDSA Feb 2026: Physische Löschung in Backups NICHT zwingend, WENN bei Restore die Löschung wiederholt wird |
| 5 | **Behördenanfragen** | Löschstopp (Litigation Hold). Nach Verfahrensende: reguläre Löschung nachholen |
| 6 | **Insolvenz** | Aufbewahrungspflichten gelten weiter. Für VÖB: geringes Risiko |
| 7 | **Vektor-Embeddings** (AI-spezifisch) | Embedding + Quelldokument = eine Löscheinheit. Keine Re-Indexierung mit gelöschten Dokumenten |
| 8 | **Mandantenlöschung** (Vertragsende) | Gesamtlöschung aller Daten. Prozess + Frist definieren |
| 9 | **Widerruf der Einwilligung** | Falls Verarbeitungen auf Einwilligung basieren (derzeit nicht geplant) |
| 10 | **Zweckwegfall** | z.B. Pilotprojekt endet → alle Pilotdaten löschen |

---

## 6. EU AI Act

### Timeline

| Datum | Was gilt |
|-------|---------|
| 01.08.2024 | AI Act in Kraft |
| **02.02.2025** | **Art. 4 (KI-Kompetenz) BEREITS IN KRAFT** |
| **02.08.2026** | Art. 50 (Transparenzpflicht) + allgemeine Anwendung |
| 02.08.2027 | Hochrisiko-Systeme (Anhang I) |

### Risikoklassifizierung VÖB-Chatbot

**Limited Risk** (Art. 50 Transparenzpflichten). NICHT High-Risk, weil:
- Kein Kreditwürdigkeits-Assessment (Anhang III Nr. 5b)
- Kein Zugang zu Finanzdienstleistungen
- Kein automatisiertes Entscheidungssystem mit rechtlichen Auswirkungen
- Internes Wissensmanagement-Tool

**Caveat:** Wenn der Chatbot jemals für kreditbezogene Entscheidungen genutzt wird → sofortige Neubewertung nötig.

### Pflichten für VÖB als Deployer

| Artikel | Pflicht | Deadline | Status |
|---------|---------|----------|--------|
| **Art. 4** | **KI-Kompetenz / AI Literacy** — Mitarbeiter müssen ausreichendes KI-Verständnis haben | **BEREITS IN KRAFT** | Mit VÖB klären: Schulungsmaßnahmen dokumentieren |
| **Art. 50** | **Transparenzpflicht** — Nutzer müssen VOR Interaktion informiert werden, dass sie mit KI interagieren | 02.08.2026 | ext-branding Disclaimer muss explizit KI-Hinweis enthalten |
| **Art. 6 Abs. 3** | **Dokumentation der Risikoklassifizierung** | Laufend | Noch nicht dokumentiert → KI-Risikobewertung erstellen |

---

## 7. Fehlende Dokumente: Must-Have vs. Nice-to-Have

### MUST HAVE (gesetzlich vorgeschrieben oder für Abnahme zwingend)

| # | Dokument | Rechtsgrundlage | Wer erstellt | Ohne VÖB machbar? | Aufwand |
|---|----------|----------------|-------------|-------------------|---------|
| **M1** | **VVT** (Verzeichnis der Verarbeitungstätigkeiten) | **Art. 30 DSGVO** — gesetzliche Pflicht | CCJ (Grundstruktur) | Ja, VÖB bestätigt | 0,5 PT |
| **M2** | **DSFA** (Datenschutz-Folgenabschätzung) | **Art. 35 DSGVO** — Pflicht bei KI + PII | CCJ (Entwurf), VÖB-DSB konsultieren | ~80% | 2-3 PT |
| **M3** | **Löschkonzept** | **DSGVO Art. 5(1)(e), Art. 17** | CCJ (Entwurf), VÖB bestätigt Fristen | ~70% | 1 PT |
| **M4** | **AVV(s)** mit StackIT | **Art. 28 DSGVO** — gesetzliche Pflicht | VÖB + StackIT | **NEIN** — VÖB unterschreibt | 1 PT (Entwurf) |
| **M5** | **KI-Risikobewertung / AI Act Einordnung** | **EU AI Act Art. 4 + Art. 6 Abs. 3** | CCJ | Ja, komplett | 0,5 PT |
| **M6** | **Regulatorische Einordnung** | Audit-Readiness, DSGVO Art. 5 Abs. 2 | CCJ | Ja, komplett | 0,5 PT |
| **M7** | **BAIT/DORA-Compliance-Matrix** | Freiwillig, für Banking-Abnahme de facto Pflicht | CCJ | Ja, komplett | 1 PT |
| **M8** | **BSI IT-Grundschutz Modul-Mapping** | Freiwillig, de facto Standard | CCJ | Ja, komplett | 1 PT |

### SHOULD HAVE (empfohlen, stärkt Abnahme-Position)

| # | Dokument | Grund | Wer | Aufwand |
|---|----------|-------|-----|---------|
| **S1** | **TOM-Dokumentation** (Art. 32 DSGVO) | Teilweise im Sicherheitskonzept, nicht explizit Art. 32-strukturiert | CCJ (Anhang zur DSFA) | 0,5 PT |
| **S2** | **BaFin KI-Orientierungshilfe Mapping** (Dec 2025) | Aktuellste BaFin-Guidance, zeigt KI-IKT-Awareness | CCJ | 0,5 PT |
| **S3** | **Shared Responsibility Model** (StackIT) | Dokumentiert StackIT- vs. CCJ/VÖB-Verantwortung | CCJ | 0,5 PT |

### NICE TO HAVE

| # | Dokument | Grund | Aufwand |
|---|----------|-------|---------|
| **N1** | **Kryptokonzept** (BSI CON.1 dediziert) | Im Sicherheitskonzept verstreut. Eigenständig = sauberer | 0,5 PT |
| **N2** | **Datensicherungskonzept** (BSI CON.3 dediziert) | Im Betriebskonzept. Eigenes Dokument bei höherem Reifegrad | 0,5 PT |
| **N3** | **Protokollierungskonzept** (BSI OPS.1.1.5) | Erst relevant wenn zentrale Logging-Infrastruktur steht | 0,5 PT |

### NICHT JETZT (blockiert oder spätere Phasen)

| # | Dokument | Warum nicht jetzt | Wann |
|---|----------|------------------|------|
| **X1** | **AVV VÖB <-> CCJ** | VÖB Recht muss abschließen | Vor PROD |
| **X2** | **Datenschutzerklärung** | VÖB Recht liefert | Vor PROD |
| **X3** | **Pentest-Bericht** | Extern beauftragen, VÖB Budget | Vor PROD |
| **X4** | **SLA-Vereinbarung** | VÖB muss RTO/RPO festlegen | Vor PROD |
| **X5** | **DORA IKT-Drittdienstleister-Prüfung** | Nur falls Chatbot als Service für Mitgliedsbanken | Phase 5+ |

---

## 8. Quellen

### BaFin / BAIT / DORA
- BaFin BAIT Rundschreiben 10/2017 (Fassung 16.12.2024): https://www.bafin.de/SharedDocs/Downloads/DE/Rundschreiben/dl_rs_1710_ba_BAIT.html
- BaFin FAQ: Für wen gelten die BAIT seit 17.01.2025? https://www.bafin.de/SharedDocs/FAQs/DE/DORA/DORA_Landingpage/13.html
- BaFin: DORA kommt — Änderungen bei BAIT: https://www.bafin.de/SharedDocs/Veroeffentlichungen/DE/Meldung/2025/meldung_2025_01_09_DORA.html
- Bundesbank BAIT/DORA: https://www.bundesbank.de/de/aufgaben/bankenaufsicht/einzelaspekte/risikomanagement/bait-dora-598580
- BaFin Orientierungshilfe IKT-Risiken bei KI (18.12.2025): https://www.bafin.de/SharedDocs/Downloads/DE/Anlage/neu/dl_Anlage_orientierungshilfe_IKT_Risiken_bei_KI.html
- BaFin Prinzipienpapier Big Data / KI (2021): https://www.bafin.de/SharedDocs/Veroeffentlichungen/DE/Meldung/2021/meldung_210615_Prinzipienpapier_BD_KI.html

### BSI IT-Grundschutz
- BSI IT-Grundschutz-Kompendium: https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html
- BSI Bausteine Edition 2023 (Downloads): https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/IT-Grundschutz-Bausteine/Bausteine_Download_Edition_node.html
- StackIT BSI C5 Type 2: https://stackit.com/en/why-stackit/benefits/certificates

### DSGVO / DSFA
- DSK Muss-Liste V1.1 (17.10.2018): https://www.datenschutzkonferenz-online.de/media/ah/20181017_ah_DSK_DSFA_Muss-Liste_Version_1.1_Deutsch.pdf
- DSK Orientierungshilfe KI und Datenschutz (06.05.2024): https://www.datenschutzkonferenz-online.de/media/oh/20240506_DSK_Orientierungshilfe_KI_und_Datenschutz.pdf
- BfDI Handreichung "KI in Behörden" (22.12.2025): https://www.bfdi.bund.de/SharedDocs/Downloads/DE/DokumenteBfDI/Dokumente-allg/2025/Handreichung-KI.pdf
- LfDI BW Rechtsgrundlagen KI V2.0 (17.10.2024): https://www.baden-wuerttemberg.datenschutz.de/wp-content/uploads/2024/10/Rechtsgrundlagen-KI-v2.0.pdf
- BayLfD DSFA-Vorlage: https://www.datenschutz-bayern.de/dsfa/DSFA-Bericht-Vorlage.docx
- Standard-Datenschutzmodell SDM V3.1: https://www.datenschutzkonferenz-online.de/media/ah/SDM-Methode-V31.pdf
- DSK Kurzpapier Nr. 5 DSFA: https://www.datenschutzkonferenz-online.de/media/kp/dsk_kpnr_5.pdf
- EuGH C-34/21 (Paragraph 26 BDSG): https://www.activemind.legal/de/guides/urteil-eugh-paragraf-26-bdsg/

### Löschkonzept
- DIN EN ISO/IEC 27555:2025-09 (ersetzt DIN 66398): https://www.konicon.de/din-66398-zurueckgezogen-iso-iec-27555-ist-der-neue-massstab-fuer-loeschkonzepte/
- EDSA Feb 2026 Backup-Löschung: https://www.bits.gmbh/loeschung-von-personenbezogenen-daten-in-backups-das-ende-eines-jahrelangen-dsgvo-dilemmas/
- BankingHub Löschkonzept: https://bankinghub.de/innovation-digital/loeschkonzept-eu-dsgvo
- SchwarzArbMoDiG Aufbewahrungsfristen: https://www.ey.com/de_de/technical/steuernachrichten/laengere-aufbewahrungsfristen-bei-banken-versicherungen-und-wertpapierinstituten

### EU AI Act
- EU AI Act Zeitplan: https://www.alexanderthamm.com/de/blog/eu-ai-act-zeitplan/
- Art. 50 Transparenzpflichten: https://ai-act-law.eu/de/artikel/50/
- Art. 4 KI-Kompetenz: https://de.ecovis.com/unternehmensberatung/eu-ai-act-schulungspflicht-mitarbeiter-ki/
- Anhang III Hochrisiko: https://ai-act-law.eu/de/anhang/3/

### Sonstiges
- VÖB Lobbyregister: https://www.lobbyregister.bundestag.de/suche/R001169
- DORA Verordnung (EU) 2022/2554: https://eur-lex.europa.eu/eli/reg/2022/2554/oj?locale=de
- NIS2-Umsetzungsgesetz: https://www.openkritis.de/it-sicherheitsgesetz/nis2-umsetzung-gesetz-cybersicherheit.html
- Bitkom KI und Datenschutz V2.0: https://www.bitkom.org/sites/main/files/2025-08/bitkom-leitfaden-kuenstliche-intelligenz-und-datenschutz-auflage-2.pdf

---

## Bekannte Inkonsistenz im Sicherheitskonzept

Zeile 705: `BSI-Grundschutz | Verschlüsselung at-rest | OFFEN (SEC-07: nicht verifiziert)`
Widerspricht SEC-07 ERLEDIGT (2026-03-08, StackIT Default AES-256). **Muss korrigiert werden.**

---

*Erstellt: 2026-03-09 | Methode: 5 parallele Web-Recherche-Agenten | Validierungsstatus: Alle Aussagen mit Quellen belegt*
