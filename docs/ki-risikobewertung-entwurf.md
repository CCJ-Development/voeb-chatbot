# KI-RISIKOBEWERTUNG NACH EU AI ACT -- ENTWURF

**Status:** ENTWURF -- Abstimmung mit VÖB ausstehend
**Version:** 0.1
**Datum:** 2026-03-14
**Autor:** Nikolaj Ivanov (CCJ / Coffee Studios)
**Rechtsgrundlage:** Verordnung (EU) 2024/1689 (AI Act), in Kraft seit 01.08.2024
**Nächste Überprüfung:** Bei Änderung der Einsatzzwecke oder LLM-Modellwechsel

---

## Änderungshistorie

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|------------|
| 0.1 | 2026-03-14 | Nikolaj Ivanov | Initialer Entwurf |

---

## 1. Systemidentifikation

| Feld | Wert |
|------|------|
| Systemname | VÖB Chatbot |
| Systembeschreibung | RAG-basierter KI-Chatbot für internes Wissensmanagement |
| KI-Komponenten | 4 LLM-Modelle (Chat), 1 Embedding-Modell (RAG-Retrieval) |
| Deployer (Art. 3 Nr. 4) | VÖB Service GmbH / Bundesverband Öffentlicher Banken Deutschlands e.V. |
| Provider der LLM-Modelle (Art. 3 Nr. 3) | StackIT (Schwarz IT KG) -- EU-Infrastruktur, Region EU01 Frankfurt |
| Modell-Hosting | Self-hosted auf StackIT AI Model Serving (vLLM-Backend). Kein Datenabfluss an OpenAI, Google oder andere externe Provider |
| Entwickler des Systems | CCJ Development UG (haftungsbeschränkt) |
| Basis-Software | Onyx FOSS (MIT-Lizenz) -- Enterprise-Fork mit Custom Extension Layer |
| Intended Purpose | Interne Wissenssuche und Fragebeantwortung für VÖB-Mitarbeiter auf Basis organisationsinterner Dokumente |
| Betroffene Personen | ~150 VÖB-Mitarbeiter (Endnutzer), VÖB-Administratoren |
| Einsatzumgebung | Internes Tool -- kein Einsatz gegenüber Externen, keine Kundeninteraktion, keine öffentliche Zugänglichkeit |
| Betrieb seit | DEV: 2026-02-27, TEST: 2026-03-03, PROD: 2026-03-11 (DNS/TLS ausstehend) |

### 1.1 KI-Modelle im Einsatz

| Modell | Typ | Modell-ID | Kontext | Einsatz |
|--------|-----|-----------|---------|---------|
| GPT-OSS 120B | Chat (LLM) | `openai/gpt-oss-120b` | 131K Token | Primäres Chat-Modell |
| Qwen3-VL 235B | Chat (LLM) | `Qwen/Qwen3-VL-235B-A22B-Instruct-FP8` | 218K Token | Alternatives Chat-Modell |
| Llama 3.3 70B | Chat (LLM) | `cortecs/Llama-3.3-70B-Instruct-FP8-Dynamic` | Standard | Alternatives Chat-Modell |
| Llama 3.1 8B | Chat (LLM) | `neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8` | Standard | Leichtgewichtiges Chat-Modell |
| Qwen3-VL-Embedding 8B | Embedding | `Qwen/Qwen3-VL-Embedding-8B` | 4096 Dim | RAG-Retrieval (Dokumenten-Indexierung und -Suche) |

### 1.2 Datenfluss

```
Benutzer (VÖB-Mitarbeiter)
    │
    ↓ HTTPS (TLSv1.3, ECDSA P-384)
    │
Onyx Web UI (Next.js) → Onyx API (FastAPI)
    │                        │
    │                        ├─→ Vespa (RAG: Embedding-Suche nach relevanten Dokumenten)
    │                        │
    │                        ├─→ StackIT AI Model Serving (LLM-Anfrage + Kontext)
    │                        │      ↓
    │                        │   LLM generiert Antwort basierend auf:
    │                        │   - System Prompt (inkl. ext-prompts Custom Prompts)
    │                        │   - Relevante Dokumenten-Chunks (RAG)
    │                        │   - Benutzer-Nachricht
    │                        │
    │                        ├─→ PostgreSQL (Chat-History, User-Daten, Token-Tracking)
    │                        │
    │                        └─→ ext-token Hook (Usage-Tracking pro Request)
    │
    ↓
Antwort an Benutzer (mit Quellenangaben aus RAG)
```

---

## 2. Risikoklassifizierung nach AI Act

### 2.1 Prüfung auf verbotene Praktiken (Art. 5)

Art. 5 AI Act verbietet bestimmte KI-Praktiken. Systematische Prüfung:

| Art. 5 Abs. | Verbotene Praktik | Zutreffend? | Begründung |
|-------------|-------------------|-------------|------------|
| 1 (a) | Unterschwellige Beeinflussung (Subliminal Techniques) | NEIN | System gibt explizite Textantworten auf Nutzerfragen. Keine verdeckte Beeinflussung. |
| 1 (b) | Ausnutzung von Vulnerabilitäten (Alter, Behinderung) | NEIN | Internes Tool für Mitarbeiter im Berufskontext. Keine gezielten Nutzergruppen mit besonderen Vulnerabilitäten. |
| 1 (c) | Social Scoring | NEIN | Kein Scoring oder Bewertung von Personen. Token-Tracking dient der Kostenkontrolle, nicht der Verhaltensbeurteilung. |
| 1 (d) | Bewertung kriminellen Risikos (Predictive Policing) | NEIN | Kein Einsatz im Bereich Strafverfolgung oder Kriminalitätsprognose. |
| 1 (e) | Ungezielte Gesichtserkennung (Scraping) | NEIN | Kein Einsatz biometrischer Daten. Textbasiertes System. |
| 1 (f) | Emotionserkennung (Arbeitsplatz/Bildung) | NEIN | Keine Analyse von Emotionen, Stimmungen oder psychologischen Zuständen der Nutzer. |
| 1 (g) | Biometrische Kategorisierung (Rasse, Religion etc.) | NEIN | Keine biometrische Datenverarbeitung. |
| 1 (h) | Echtzeit-Fernidentifizierung in öffentlichen Räumen | NEIN | Textbasiertes internes System, keine Videoüberwachung. |

**Ergebnis: Keine verbotene Praktik nach Art. 5 zutreffend.**

### 2.2 Prüfung auf Hochrisiko-Einstufung (Art. 6, Anhang III)

Art. 6 i.V.m. Anhang III definiert Hochrisiko-KI-Systeme. Systematische Prüfung aller Anhang-III-Kategorien:

| Anhang III Nr. | Kategorie | Zutreffend? | Begründung |
|----------------|-----------|-------------|------------|
| 1 | Biometrie und Identifizierung | NEIN | Kein Einsatz biometrischer Daten. Authentifizierung über Entra ID (OIDC), nicht über KI. |
| 2 | Kritische Infrastruktur | NEIN | VÖB ist kein KRITIS-Betreiber. Chatbot ist ein internes Produktivitäts-Tool, kein Teil kritischer Infrastruktur. |
| 3 | Allgemeine und berufliche Bildung | NEIN | Kein Einsatz für Prüfungen, Zulassungsentscheidungen oder adaptive Lernsysteme. |
| 4 | Beschäftigung und Personalmanagement | NEIN | Kein Einsatz für Einstellung, Beförderung, Kündigung, Aufgabenzuweisung, Leistungsbewertung oder Überwachung von Mitarbeitern. Das System ist ein Wissensmanagement-Tool, kein HR-Tool. |
| 5 (a) | Zugang zu essenziellen privaten Dienstleistungen | NEIN | Internes Tool, kein Kundenzugang. |
| **5 (b)** | **Kreditwürdigkeitsprüfung / Kreditscoring** | **NEIN** | **Kein Einsatz für Kreditentscheidungen.** Chatbot durchsucht interne Wissensdokumente und beantwortet Fragen. Keine automatisierten Finanzentscheidungen. |
| 5 (c) | Risikobewertung Lebens-/Krankenversicherung | NEIN | Kein Einsatz im Versicherungsbereich. |
| 5 (d) | Risikobewertung Gesundheit/Leben/Eigentum | NEIN | Kein Einsatz für Notfall-/Sicherheitsbewertungen. |
| 6 | Strafverfolgung | NEIN | Kein Einsatz im Bereich Strafverfolgung. |
| 7 | Migration, Asyl, Grenzkontrollen | NEIN | Kein Einsatz in diesem Bereich. |
| 8 | Justiz und demokratische Prozesse | NEIN | Kein Einsatz in der Justiz oder für Wahlbeeinflussung. |

**Ergebnis: Keine Anhang-III-Kategorie zutreffend. Das System ist KEIN Hochrisiko-System.**

> **CAVEAT (Art. 6 Abs. 3):** Falls der Chatbot in Zukunft für kreditbezogene Entscheidungen, Personalmanagement oder andere Anhang-III-Zwecke eingesetzt wird, ist eine sofortige Neubewertung erforderlich. Dies würde die Einstufung auf "Hochrisiko" ändern und erhebliche zusätzliche Pflichten auslösen (Art. 8-15: Risikomanagementsystem, Datengovernance, technische Dokumentation, Aufzeichnungspflichten, Transparenz, menschliche Aufsicht, Genauigkeit/Robustheit/Cybersicherheit).

### 2.3 Ergebnis: Limited Risk (Art. 50)

**Das VÖB-Chatbot-System wird als Limited-Risk-KI-System eingestuft.** Begründung:

1. **Keine verbotene Praktik** (Art. 5) -- alle 8 Verbotstatbestände geprüft und verneint.
2. **Kein Hochrisiko-System** (Art. 6, Anhang III) -- alle 8 Kategorien geprüft und verneint. Insbesondere: kein Kreditscoring (Nr. 5b), kein Personalmanagement (Nr. 4), keine kritische Infrastruktur (Nr. 2).
3. **KI-System mit direkter Nutzerinteraktion** -- Art. 50 Abs. 1: Personen, die mit einem KI-System interagieren, müssen darüber informiert werden.

**Rechtsfolge:** Es gelten die Transparenzpflichten nach Art. 50 sowie die allgemeine KI-Kompetenzpflicht nach Art. 4.

---

## 3. Transparenzpflichten (Art. 50)

**Deadline: 02.08.2026** (allgemeine Anwendbarkeit Art. 50)

### 3.1 Pflicht: KI-Kennzeichnung (Art. 50 Abs. 1)

> *"Anbieter stellen sicher, dass KI-Systeme, die für die direkte Interaktion mit natürlichen Personen bestimmt sind, so konzipiert und entwickelt werden, dass die betreffenden natürlichen Personen darüber informiert werden, dass sie mit einem KI-System interagieren [...]."*

| Aspekt | Status | Details |
|--------|--------|---------|
| KI-Kennzeichnung im UI | TEILWEISE ERFÜLLT | ext-branding bietet konfigurierbaren Disclaimer (`custom_lower_disclaimer_content`, max. 200 Zeichen), der unterhalb des Chat-Eingabefelds angezeigt wird. Aktuell muss der Text explizit auf "KI" hinweisen. |
| Kennzeichnung vor Interaktion | TEILWEISE ERFÜLLT | ext-branding bietet First-Visit-Popup (`custom_popup_content`, max. 500 Zeichen) und Consent-Screen (`enable_consent_screen`, `consent_screen_prompt`). Beide können für KI-Hinweis konfiguriert werden. |
| Kennzeichnung in Antworten | NICHT ERFÜLLT | Einzelne Chat-Antworten enthalten keinen expliziten Marker "Diese Antwort wurde von KI generiert". |

**[EMPFEHLUNG] Maßnahmen bis 02.08.2026:**

1. Disclaimer-Text konfigurieren, der explizit auf KI-Interaktion hinweist (z.B. "Antworten werden von einem KI-System generiert und können Fehler enthalten. Prüfen Sie wichtige Informationen anhand der angegebenen Quellen.").
2. First-Visit-Popup aktivieren mit KI-Transparenzhinweis.
3. Consent-Screen aktivieren, der Nutzer explizit bestätigen lässt, dass sie die KI-Natur des Systems verstanden haben.

### 3.2 Pflicht: Offenlegung bei generierten Inhalten (Art. 50 Abs. 2)

> *"Anbieter von KI-Systemen, einschließlich KI-Systemen mit allgemeinem Verwendungszweck, die synthetische Audio-, Bild-, Video- oder Textinhalte erzeugen, stellen sicher, dass die Ausgaben des KI-Systems in einem maschinenlesbaren Format gekennzeichnet werden [...]."*

| Aspekt | Status | Details |
|--------|--------|---------|
| Maschinenlesbare Kennzeichnung (Metadata) | NICHT ERFÜLLT | Chat-Antworten enthalten kein maschinenlesbares Kennzeichen (z.B. `X-AI-Generated: true` Header oder Metadaten). |
| Textkennzeichnung | NICHT ERFÜLLT | Generierte Texte sind nicht als KI-generiert markiert. |

**[EMPFEHLUNG] Bewertung:**
Art. 50 Abs. 2 betrifft primär Deepfakes und synthetische Medien. Für rein textbasierte interne Chat-Systeme ist die Maschinenlesbarkeits-Anforderung weniger klar geregelt. Die KI-Kennzeichnung im UI (Abs. 1) hat höhere Priorität. Dennoch empfohlen: HTTP-Header `X-AI-Generated: true` in API-Responses des Chat-Endpunkts.

### 3.3 Ausnahmen nach Art. 50 Abs. 4

Art. 50 Abs. 4 sieht Erleichterungen vor, wenn die KI-Nutzung "aus dem Zusammenhang offensichtlich" ist. Da der VÖB-Chatbot als dediziertes KI-Tool erkennbar ist (eigene URL, eigenes Branding, Chat-Interface), greift diese Erleichterung teilweise. Trotzdem empfohlen: explizite Kennzeichnung als Best Practice im Banking-Umfeld.

---

## 4. KI-Kompetenz (Art. 4) -- SEIT 02.02.2025 IN KRAFT

### 4.1 Anforderungen

Art. 4 verpflichtet Deployer (VÖB), sicherzustellen, dass Personal, das KI-Systeme betreibt oder nutzt, über ein "ausreichendes Maß an KI-Kompetenz" verfügt. Die Kompetenz muss dem Kontext, dem technischen Wissen und der Erfahrung der Personen sowie dem Einsatzkontext des KI-Systems angemessen sein.

Betroffene Personengruppen:

| Gruppe | Anzahl (ca.) | Erforderliche Kompetenz |
|--------|-------------|------------------------|
| Endnutzer (VÖB-Mitarbeiter) | ~150 | Verständnis: KI-generierte Antworten können fehlerhaft sein (Halluzinationen), Quellen prüfen, keine blinde Übernahme für kritische Entscheidungen |
| Administratoren (VÖB IT) | 2-5 | Verständnis: Modell-Konfiguration, System-Prompt-Auswirkungen, Token-Limits, Monitoring-Interpretation |
| Entscheidungsträger (Management) | 3-5 | Verständnis: KI-Risiken, regulatorische Anforderungen, Grenzen des Systems, Haftungsfragen |

### 4.2 Status

**[KLÄRUNG] Hat VÖB KI-Kompetenz-Schulungen durchgeführt?**

Art. 4 ist seit 02.02.2025 in Kraft. Stand 2026-03-14 ist unklar, ob VÖB:
- Schulungsmaßnahmen für Mitarbeiter durchgeführt hat
- Eine KI-Nutzungsrichtlinie erstellt hat
- Die KI-Kompetenz dokumentiert hat

Dies ist eine **VÖB-Verantwortung als Deployer**, nicht eine Entwickler-Verantwortung (CCJ). CCJ kann unterstützen (Schulungsmaterial, Nutzerleitfaden), aber die Durchführung und Dokumentation liegt bei VÖB.

### 4.3 Empfohlene Maßnahmen

**[EMPFEHLUNG] Folgende Maßnahmen sollten vor PROD Go-Live umgesetzt werden:**

| # | Maßnahme | Verantwortlich | Aufwand | Priorität |
|---|----------|---------------|---------|-----------|
| K1 | **Endnutzer-Schulung** erstellen: Umgang mit KI-Antworten, Erkennen von Halluzinationen, Quellen prüfen, keine Übernahme für rechtsverbindliche Aussagen | CCJ (Material), VÖB (Durchführung) | 1 PT | HOCH |
| K2 | **Admin-Schulung** erstellen: Prompt-Engineering, Modell-Konfiguration, Token-Limits, Monitoring-Dashboards | CCJ | 0,5 PT | MITTEL |
| K3 | **KI-Nutzungsrichtlinie** erstellen: Dos/Don'ts, zugelassene Einsatzzwecke, verbotene Einsatzzwecke (kein Kreditscoring, keine HR-Entscheidungen) | VÖB (Inhalt), CCJ (Entwurf) | 0,5 PT | HOCH |
| K4 | **Dokumentation der Schulungsteilnahme**: Nachweis, dass alle Nutzer geschult wurden (Datum, Teilnehmer, Inhalt) | VÖB | 0,25 PT | MITTEL |
| K5 | **Jährliche Auffrischung**: Regelmäßige Wiederholung bei Modellwechsel oder Funktionserweiterungen | VÖB | laufend | NIEDRIG |

---

## 5. Risikobewertung (auch wenn nicht High-Risk)

Obwohl das System als Limited Risk eingestuft wird, ist eine Risikobewertung aus den folgenden Gründen angemessen:
- VÖB agiert im regulierten Banking-Umfeld (Reputationsrisiko)
- Personenbezogene Daten werden verarbeitet (DSGVO-Pflicht)
- BSI IT-Grundschutz empfiehlt ergänzende Sicherheitsanalyse für KI-Systeme

### 5.1 Technische Risiken

| ID | Risiko | Beschreibung | Eintrittswahrscheinlichkeit | Schwere | Implementierte Maßnahmen | Restrisiko |
|----|--------|-------------|---------------------------|---------|-------------------------|------------|
| T1 | **Halluzinationen / falsche Antworten** | LLM generiert plausibel klingende, aber inhaltlich falsche Informationen | HOCH (inhärent bei LLMs) | HOCH (besonders im Banking-Kontext: falsche regulatorische Auskünfte) | RAG mit Quellenangaben (Nutzer kann Quellen prüfen), System-Prompt-Guardrails via ext-prompts, Disclaimer im UI (ext-branding) | MITTEL -- Halluzinationen sind bei aktuellen LLMs nicht vollständig eliminierbar |
| T2 | **Bias in LLM-Antworten** | Modelle reproduzieren oder verstärken gesellschaftliche Vorurteile (Gender, Herkunft etc.) | MITTEL | MITTEL (internes Tool, keine Kundeninteraktion, keine Entscheidungsautomatisierung) | Kein automatisiertes Entscheidungssystem; Antworten sind informativ, nicht handlungsanweisend. System-Prompts können Anti-Bias-Anweisungen enthalten (ext-prompts). Mehrere Modelle zur Auswahl. | NIEDRIG -- Risiko durch internen Einsatz und menschliche Aufsicht begrenzt |
| T3 | **Prompt Injection** | Angreifer manipuliert über speziell gestaltete Eingaben das Systemverhalten, z.B. Exfiltration von Dokumenten oder Umgehung von Guardrails | MITTEL | HOCH (potenziell meldepflichtige Datenschutzverletzung Art. 33 DSGVO) | System-Prompt vor User-Input (Onyx-Standard), Input-Validierung (Pydantic, Längenbegrenzung), ext-prompts Custom Guardrails, NetworkPolicies (Daten-Egress eingeschränkt) | MITTEL -- Prompt Injection ist ein aktives Forschungsgebiet; vollständiger Schutz nicht möglich |
| T4 | **Datenleck über LLM-Kontext** | LLM gibt in Antworten Informationen preis, auf die der Nutzer keinen Zugriff haben sollte (Cross-Context Leakage) | MITTEL (abhängig von Dokumenten-Zugriffssteuerung) | HOCH | Namespace-basierte Dokumenten-Isolation (geplant: ext-access, Phase 4g), RAG beschränkt Kontext auf relevante Dokumente, kein globaler Zugriff auf alle Dokumente | MITTEL -- ext-access (Zugriffssteuerung) ist noch blockiert (Entra ID ausstehend) |
| T5 | **Übervertrauen in KI-Antworten (Automation Bias)** | Mitarbeiter übernehmen KI-Antworten unkritisch für wichtige Entscheidungen | HOCH (psychologischer Effekt, verstärkt durch professionelle UI) | HOCH (im Banking: falsche regulatorische Interpretation kann rechtliche Konsequenzen haben) | Disclaimer im UI, Quellenangaben (RAG), KI-Kompetenz-Schulung (Art. 4), System-Prompt-Hinweis "Antworten prüfen" | MITTEL -- technische Maßnahmen können Automation Bias nur begrenzt adressieren; Schulung ist entscheidend |
| T6 | **Unbeabsichtigte Verarbeitung personenbezogener Daten im Prompt** | Nutzer geben personenbezogene Daten (Namen, Kontodaten, Gehälter) als Teil ihrer Frage ein, die vom LLM verarbeitet werden | HOCH (Nutzer kontrollieren Eingaben) | MITTEL (Daten bleiben auf StackIT, keine Drittlandübermittlung) | StackIT-Hosting (EU, kein Datenabfluss), Token-Tracking ohne Prompt-Inhalt (nur Zählung), ext-prompts Guardrails, KI-Nutzungsrichtlinie (geplant) | NIEDRIG -- Datensouveränität durch StackIT gewährleistet; Restrisiko durch Nutzerverhalten |

### 5.2 Organisatorische Risiken

| ID | Risiko | Beschreibung | Eintrittswahrscheinlichkeit | Schwere | Implementierte Maßnahmen | Restrisiko |
|----|--------|-------------|---------------------------|---------|-------------------------|------------|
| O1 | **Fehlende KI-Kompetenz der Nutzer** | Mitarbeiter verstehen die Grenzen des KI-Systems nicht (Halluzinationen, Aktualität, Kontextabhängigkeit) | HOCH (bei fehlender Schulung) | HOCH (Fehlentscheidungen auf Basis von KI-Output) | Art. 4 KI-Kompetenz (Pflicht seit 02.02.2025), Schulungskonzept geplant (K1-K5), Disclaimer im UI | MITTEL -- abhängig von Umsetzung der Schulungsmaßnahmen durch VÖB |
| O2 | **Fehlende Aufsicht über KI-generierte Inhalte** | Niemand prüft systematisch, ob KI-Antworten korrekt sind oder problematische Inhalte enthalten | MITTEL | MITTEL | ext-token Usage-Dashboard (Monitoring der Nutzung), Chat-History in DB (nachträgliche Prüfung möglich), Admin-Zugang zu allen Konversationen | NIEDRIG -- Monitoring-Infrastruktur vorhanden; systematische Qualitätsprüfung noch nicht formalisiert |
| O3 | **Unklare Verantwortlichkeit bei Fehlentscheidungen** | Wenn eine auf KI-Output basierende Entscheidung sich als falsch erweist: Wer haftet? | MITTEL | HOCH (im Banking-Kontext: regulatorische und haftungsrechtliche Konsequenzen) | KI-Nutzungsrichtlinie (geplant), Disclaimer ("KI-Antworten sind informativ, nicht rechtsverbindlich"), Schulung | MITTEL -- [KLÄRUNG] VÖB muss Haftungsregelung für KI-gestützte Entscheidungen intern klären |
| O4 | **Schatten-KI / unkontrollierte Nutzung** | Mitarbeiter nutzen zusätzlich nicht genehmigte KI-Tools (ChatGPT, Copilot etc.) und geben dort sensible VÖB-Daten ein | HOCH (branchenübergreifend beobachtet) | HOCH (Datenabfluss an US-Provider, DSGVO-Verstoß) | VÖB-Chatbot als genehmigtes KI-Tool positionieren, KI-Nutzungsrichtlinie (geplant), StackIT-Hosting als Datenschutz-Argument | MITTEL -- [EMPFEHLUNG] VÖB sollte KI-Nutzungsrichtlinie erstellen, die Schatten-KI adressiert |

### 5.3 Risikomatrix (Gesamtübersicht)

```
                    SCHWERE
              Niedrig    Mittel     Hoch
         ┌──────────┬──────────┬──────────┐
  Hoch   │          │   T6     │ T1, T5,  │
         │          │          │ O1, O4   │
         ├──────────┼──────────┼──────────┤
  Mittel │          │   T2     │ T3, T4,  │
  E.W.   │          │          │ O3       │
         ├──────────┼──────────┼──────────┤
  Niedrig│          │   O2     │          │
         │          │          │          │
         └──────────┴──────────┴──────────┘

E.W. = Eintrittswahrscheinlichkeit
```

---

## 6. Maßnahmen und Compliance-Status

| # | Anforderung | Quelle | Status | Maßnahme | Verantwortlich |
|---|------------|--------|--------|----------|----------------|
| 1 | KI-Kompetenz sicherstellen | Art. 4 AI Act | **[KLÄRUNG]** -- Pflicht seit 02.02.2025. Status VÖB-seitig unklar. | Schulungskonzept K1-K5 (siehe Abschnitt 4.3) | VÖB (Deployer) |
| 2 | Transparenz: KI-Kennzeichnung | Art. 50 Abs. 1 AI Act | TEILWEISE ERFÜLLT | ext-branding Disclaimer + Popup + Consent-Screen konfigurieren | CCJ (Technik), VÖB (Text) |
| 3 | Transparenz: Maschinenlesbare Kennzeichnung | Art. 50 Abs. 2 AI Act | NICHT ERFÜLLT | [EMPFEHLUNG] HTTP-Header `X-AI-Generated: true` in Chat-API-Responses | CCJ |
| 4 | Risikoklassifizierung dokumentieren | Art. 6 Abs. 3 AI Act | ERFÜLLT | Dieses Dokument | CCJ |
| 5 | Datensouveränität (kein Drittland-Transfer) | DSGVO Art. 44 ff. | ERFÜLLT | StackIT EU01 Frankfurt, kein Datenabfluss an externe LLM-Provider | CCJ |
| 6 | DSFA durchführen | Art. 35 DSGVO | IN ARBEIT | docs/dsfa-entwurf.md erstellt (2026-03-14), VÖB-DSB-Konsultation ausstehend | CCJ (Entwurf), VÖB (DSB) |
| 7 | VVT führen | Art. 30 DSGVO | IN ARBEIT | docs/vvt-entwurf.md erstellt (2026-03-14), VÖB-Bestätigung ausstehend | CCJ (Entwurf), VÖB |
| 8 | Löschkonzept | Art. 5(1)(e), Art. 17 DSGVO | IN ARBEIT | docs/loeschkonzept-entwurf.md erstellt (2026-03-14), Fristen-Abstimmung ausstehend | CCJ (Entwurf), VÖB |
| 9 | Prompt-Injection-Schutz | BSI, BaFin KI-OH | TEILWEISE ERFÜLLT | System-Prompt vor User-Input, Input-Validierung, ext-prompts Guardrails. Output-Filterung (PII) geplant. | CCJ |
| 10 | Halluzinations-Mitigation | BaFin KI-OH, Best Practice | TEILWEISE ERFÜLLT | RAG mit Quellenangaben, Disclaimer, Schulung | CCJ (Technik), VÖB (Schulung) |
| 11 | Token-/Kosten-Kontrolle | Best Practice, BAIT Kap. 8 | ERFÜLLT | ext-token: Per-User/Per-Model Tracking, Quotas, Hard Stops (HTTP 429) | CCJ |
| 12 | Monitoring und Alerting | BSI DER.1, BAIT Kap. 5 | ERFÜLLT | kube-prometheus-stack auf allen Environments, Teams-Alerting, 20+ Alert-Rules | CCJ |
| 13 | Zugriffssteuerung | BSI ORP.4, BAIT Kap. 6 | TEILWEISE ERFÜLLT | Onyx-RBAC nativ (admin/basic). ext-rbac (Gruppen, Entra ID) blockiert durch VÖB IT. | CCJ (Technik), VÖB (Entra ID) |
| 14 | KI-Nutzungsrichtlinie | Art. 4 AI Act, Best Practice | NICHT ERFÜLLT | [EMPFEHLUNG] VÖB erstellt interne KI-Nutzungsrichtlinie | VÖB |
| 15 | AVV mit StackIT | Art. 28 DSGVO | NICHT ERFÜLLT | [KLÄRUNG] Existiert bereits ein AVV zwischen VÖB und StackIT? | VÖB |

---

## 7. General-Purpose AI (GPAI) Transparenz (Art. 53)

### 7.1 Einordnung

Die im VÖB-Chatbot eingesetzten LLM-Modelle (GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, Llama 3.1 8B) sind General-Purpose AI (GPAI) Modelle im Sinne von Art. 3 Nr. 63 AI Act. Art. 53 definiert Pflichten für **Provider** (nicht Deployer) dieser Modelle.

### 7.2 Pflichten des GPAI-Providers (NICHT VÖB)

Die folgenden Pflichten treffen die **Modell-Provider** (Meta, Alibaba/Qwen, StackIT als Hoster), nicht VÖB als Deployer:

| Pflicht (Art. 53) | Provider | Status |
|-------------------|----------|--------|
| Technische Dokumentation erstellen und pflegen | Meta (Llama), Alibaba (Qwen), Modell-Provider (GPT-OSS) | Außerhalb VÖB-Verantwortung |
| Informationen für Downstream-Provider bereitstellen | StackIT (als Intermediär) | [KLÄRUNG] Hat StackIT Modell-Dokumentation bereitgestellt? |
| Urheberrechtliche Compliance (Trainingsdaten) | Meta, Alibaba, Modell-Provider | Außerhalb VÖB-Verantwortung |
| Zusammenfassung der Trainingsdaten veröffentlichen | Meta, Alibaba, Modell-Provider | Meta: Model Card veröffentlicht. Qwen: Model Card veröffentlicht. |

### 7.3 VÖB-Verantwortung als Deployer

VÖB muss als Deployer sicherstellen, dass:
1. Die eingesetzten Modelle in der EU verfügbar und dokumentiert sind (erfüllt: Open-Source-Modelle mit Model Cards).
2. Keine verbotenen Modelle eingesetzt werden (erfüllt: alle Modelle sind frei verfügbar und nicht gelistet).
3. Bei Systemrisiko (Art. 51) zusätzliche Pflichten gelten -- derzeit nicht zutreffend (kein Modell mit "systemic risk").

---

## 8. Empfehlungen

### 8.1 Vor PROD Go-Live (DRINGEND)

| # | Empfehlung | Aufwand | Verantwortlich |
|---|-----------|---------|----------------|
| E1 | **KI-Transparenz-Texte konfigurieren**: Disclaimer, First-Visit-Popup, Consent-Screen in ext-branding mit explizitem KI-Hinweis befüllen | 0,25 PT | CCJ + VÖB |
| E2 | **KI-Nutzungsrichtlinie erstellen**: Zugelassene/verbotene Einsatzzwecke, Umgang mit Halluzinationen, Verantwortlichkeiten | 0,5 PT | VÖB (Inhalt), CCJ (Entwurf) |
| E3 | **AVV-Status mit StackIT klären**: Art. 28 DSGVO Pflicht. Falls kein AVV existiert: Entwurf erstellen und abschließen | 1 PT | VÖB |
| E4 | **KI-Kompetenz-Status klären**: Art. 4 seit 02.02.2025 in Kraft. Schulungsnachweis dokumentieren | 0,25 PT | VÖB |

### 8.2 Innerhalb 3 Monaten nach PROD Go-Live

| # | Empfehlung | Aufwand | Verantwortlich |
|---|-----------|---------|----------------|
| E5 | **Endnutzer-Schulung durchführen**: KI-Kompetenz für alle ~150 Mitarbeiter (Halluzinationen, Quellen prüfen, kein blindes Vertrauen) | 1 PT | VÖB (Durchführung), CCJ (Material) |
| E6 | **DSFA finalisieren**: VÖB-DSB konsultieren, Restrisiken bewerten, Freigabe einholen | 1 PT | CCJ + VÖB-DSB |
| E7 | **Output-Filterung evaluieren**: PII-Detection in LLM-Antworten (IBAN, Kreditkartennummern, Personaldaten) | 1 PT | CCJ |
| E8 | **Regelmäßige Risikoüberprüfung etablieren**: Halbjährliche Überprüfung dieser Risikobewertung, insbesondere bei Modellwechsel oder Einsatzerweiterung | 0,25 PT | CCJ + VÖB |

### 8.3 Langfristig (6-12 Monate)

| # | Empfehlung | Aufwand | Verantwortlich |
|---|-----------|---------|----------------|
| E9 | **Zugriffssteuerung (ext-access)**: Dokumenten-Isolation per Gruppe/Abteilung -- reduziert T4 (Datenleck über LLM-Kontext) | 3 PT | CCJ (blockiert: Entra ID) |
| E10 | **Adversarial Testing**: Gezieltes Prompt-Injection-Testing durch Sicherheitsexperten | 2 PT | Extern |
| E11 | **Bias-Monitoring**: Stichprobenartige Analyse von LLM-Antworten auf systematische Verzerrungen | 0,5 PT | VÖB + CCJ |
| E12 | **BaFin KI-Orientierungshilfe Mapping** (18.12.2025): Systematischer Abgleich mit BaFin-Erwartungen für KI-IKT-Risiken | 0,5 PT | CCJ |

---

## 9. Offene Punkte

| # | Offener Punkt | Typ | Wer muss klären | Auswirkung auf Risikobewertung |
|---|--------------|-----|-----------------|-------------------------------|
| OP1 | Hat VÖB KI-Kompetenz-Schulungen für Mitarbeiter durchgeführt (Art. 4, seit 02.02.2025 Pflicht)? | [KLÄRUNG] | VÖB | Gesetzliche Pflicht -- bei Nicht-Erfüllung: Verstoß gegen Art. 4 AI Act |
| OP2 | Existiert ein AVV zwischen VÖB und StackIT (Art. 28 DSGVO)? | [KLÄRUNG] | VÖB | Gesetzliche Pflicht -- ohne AVV: DSGVO-Verstoß |
| OP3 | Wer ist der VÖB-Datenschutzbeauftragte? (wird für DSFA-Konsultation Art. 35 Abs. 2 benötigt) | [KLÄRUNG] | VÖB | DSFA kann ohne DSB-Konsultation nicht finalisiert werden |
| OP4 | Soll der Chatbot zukünftig auch Mitgliedsbanken zur Verfügung gestellt werden? | [KLÄRUNG] | VÖB | Falls ja: DORA Kap. V (IKT-Drittdienstleister) prüfen, ggf. Neubewertung |
| OP5 | Gibt es VÖB-interne Richtlinien zur Nutzung von KI-Tools (KI-Nutzungsrichtlinie)? | [KLÄRUNG] | VÖB | Adressiert O4 (Schatten-KI) und O1 (KI-Kompetenz) |
| OP6 | Welche Texte sollen für KI-Transparenz im UI angezeigt werden (Disclaimer, Popup, Consent)? | [KLÄRUNG] | VÖB | Art. 50 Compliance bis 02.08.2026 |
| OP7 | Hat StackIT Modell-Dokumentation für die gehosteten GPAI-Modelle bereitgestellt (Art. 53)? | [KLÄRUNG] | VÖB / CCJ | Downstream-Dokumentationspflicht |
| OP8 | Haftungsregelung bei Fehlentscheidungen auf Basis von KI-Output | [KLÄRUNG] | VÖB (Rechtsabteilung) | Adressiert O3 (unklare Verantwortlichkeit) |

---

## 10. Querverweise

| Dokument | Pfad | Relevanz |
|----------|------|----------|
| Compliance-Research | `docs/referenz/compliance-research.md` | EU AI Act Einordnung, Risikoklassen, Timeline, DSFA |
| Sicherheitskonzept | `docs/sicherheitskonzept.md` | TOMs, LLM-Sicherheit, Netzwerksicherheit, DSGVO |
| Betriebskonzept | `docs/betriebskonzept.md` | Systemarchitektur, LLM-Konfiguration, Extensions |
| DSFA-Entwurf | `docs/dsfa-entwurf.md` | Datenschutz-Folgenabschätzung (13 Risiken) |
| VVT-Entwurf | `docs/vvt-entwurf.md` | Verzeichnis der Verarbeitungstätigkeiten |
| Löschkonzept-Entwurf | `docs/loeschkonzept-entwurf.md` | Löschfristen und -prozesse |
| ext-branding Modulspezifikation | `docs/technisches-feinkonzept/ext-branding.md` | Disclaimer, Popup, Consent-Screen |
| ext-token Modulspezifikation | `docs/technisches-feinkonzept/ext-token.md` | Token-Tracking, Quotas |
| ext-prompts Modulspezifikation | `docs/technisches-feinkonzept/ext-prompts.md` | Custom System Prompts, Guardrails |
| Technische Parameter (SSOT) | `docs/referenz/technische-parameter.md` | Zentrale Faktenreferenz |
| ADR-003 StackIT als Cloud-Provider | `docs/adr/adr-003-stackit-als-cloud-provider.md` | Datensouveränität, BSI C5 Type 2 |

---

*Erstellt: 2026-03-14 | Rechtsstand: AI Act (EU) 2024/1689, DSGVO, BDSG | Nächste Überprüfung: Bei Einsatzerweiterung, Modellwechsel oder regulatorischer Änderung*
