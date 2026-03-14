# Abnahmeprotokoll M1: Infrastruktur + DEV/TEST Environment

**Dokumentstatus**: Vorbereitet (Abnahme ausstehend)
**Version**: 1.0
**Erstellt**: 2026-03-05

---

## Allgemeine Informationen

| Feld | Wert |
|------|------|
| **Projekt** | VÖB Service Chatbot |
| **Projektphase / Meilenstein** | M1: Infrastruktur + DEV/TEST Environment |
| **Abnahmedatum** | [TBD — VÖB Terminvorschlag] |
| **Ort** | Online (Microsoft Teams) |

---

## Teilnehmer

### Auftragnehmer

| Rolle | Name | Organisation | Unterschrift |
|-------|------|-------------|-------------|
| Tech Lead | Nikolaj Ivanov | CCJ / Coffee Studios | ____________ |

### Auftraggeber

| Rolle | Name | Abteilung | Unterschrift |
|-------|------|----------|-------------|
| Projektverantwortlicher | [TBD] | VÖB | ____________ |
| Technischer Reviewer | [TBD] | VÖB IT | ____________ |

---

## Pruefgegenstand

### Meilenstein M1: Infrastruktur + DEV/TEST Environment

**Geltungsumfang**:
- StackIT Kubernetes Cluster (SKE) mit 2 Nodes
- Managed Services: PostgreSQL Flex, Object Storage (DEV + TEST)
- In-Cluster Services: Vespa, Redis (DEV + TEST)
- LLM-Integration via StackIT AI Model Serving
- CI/CD Pipeline (GitHub Actions → StackIT Container Registry → Helm Deploy)
- DEV-Umgebung (`onyx-dev`, 16 Pods)
- TEST-Umgebung (`onyx-test`, 15 Pods)
- Infrastruktur-Dokumentation (Runbooks, ADRs, Implementierungsplan)

**Nicht im Umfang (folgt in spaeteren Meilensteinen)**:
- Authentifizierung via Entra ID / OIDC (M2)
- Custom Extension Module: Token Limits, RBAC (M3)
- Branding, Analytics, Custom Prompts (M4)
- Production Monitoring, Pentest, PROD-Cluster (M5)
- Production Go-Live (M6)

### Referenzmaterialien

| Dokument | Pfad |
|----------|------|
| Meilensteinplan | [meilensteinplan.md](./meilensteinplan.md) |
| Implementierungsplan | [stackit-implementierungsplan.md](../referenz/stackit-implementierungsplan.md) |
| Infrastruktur-Referenz | [stackit-infrastruktur.md](../referenz/stackit-infrastruktur.md) |
| Betriebskonzept | [betriebskonzept.md](../betriebskonzept.md) |
| Sicherheitskonzept | [sicherheitskonzept.md](../sicherheitskonzept.md) |
| Testkonzept | [testkonzept.md](../testkonzept.md) |
| ADR-001 bis ADR-005 | [adr/](../adr/) |
| Cloud-Infrastruktur-Audit | [cloud-infrastruktur-audit-2026-03-04.md](../audit/cloud-infrastruktur-audit-2026-03-04.md) |

---

## Abnahmekriterien

### Funktionale Abnahmekriterien

| Nr. | Kriterium | Soll-Zustand | Ist-Zustand | Erfuellt? | Bemerkung |
|-----|-----------|-------------|-------------|-----------|-----------|
| F-1 | Kubernetes Cluster | 2 Nodes (g1a.8d) Running | 2 Nodes Running, v1.33.8 | [x] Ja | Node Pool `devtest`, Flatcar OS. K8s Upgrade 2026-03-08 |
| F-2 | DEV: PostgreSQL | DB erreichbar, funktionsfaehig | PG Flex `vob-dev` (2 CPU, 4 GB, 20 GB SSD) | [x] Ja | Managed Service, taegliches Backup |
| F-3 | DEV: Vespa | Deployed und lauffaehig | StatefulSet `da-vespa` Running, 20 Gi PV | [x] Ja | In-Cluster, Headless Service |
| F-4 | DEV: Object Storage | Bucket funktioniert | Bucket `vob-dev`, S3-kompatibel | [x] Ja | StackIT Object Storage |
| F-5 | DEV: Pods Running | Alle Pods Running | 16/16 Pods Running in `onyx-dev` | [x] Ja | Standard Worker Mode (8 separate Celery-Worker) |
| F-6 | DEV: Health Check | API Health OK | `https://dev.chatbot.voeb-service.de/health` → 200 OK | [x] Ja | Seit 2026-02-27, HTTPS seit 2026-03-09 |
| F-7 | DEV: LLM antwortet | Chat-Modell antwortet korrekt | GPT-OSS 120B + Qwen3-VL 235B funktional | [x] Ja | StackIT AI Model Serving |
| F-8 | TEST: PostgreSQL | Eigene Instanz erreichbar | PG Flex `vob-test` (2 CPU, 4 GB, 20 GB SSD) | [x] Ja | Separate Instanz von DEV |
| F-9 | TEST: Object Storage | Eigener Bucket funktioniert | Bucket `vob-test`, eigene Credentials | [x] Ja | Enterprise-Trennung |
| F-10 | TEST: Pods + Health | Pods Running, Health OK | 15/15 Pods Running, `https://test.chatbot.voeb-service.de` OK | [x] Ja | Eigene IngressClass `nginx-test` |
| F-11 | CI/CD Pipeline | Build + Deploy funktioniert | Parallel-Build ~10 Min, SHA-gepinnte Actions | [x] Ja | Run #5 produktionsreif (2026-03-02) |
| F-12 | Runbooks | Alle vorhanden und verifiziert | 4 Runbooks + Implementierungsplan | [x] Ja | Projekt-Setup, PostgreSQL, Helm, CI/CD |

**Ergebnis: 12/12 funktionale Kriterien erfuellt.**

### Non-Funktionale Abnahmekriterien

| Nr. | Kriterium | Soll-Zustand | Ist-Zustand | Erfuellt? | Bemerkung |
|-----|-----------|-------------|-------------|-----------|-----------|
| NF-1 | Verfuegbarkeit DEV | Pods laufen stabil | 16 Pods Running, kein CrashLoop seit Go-Live | [x] Ja | Seit 2026-02-27, 16 Pods seit 2026-03-06 |
| NF-2 | Verfuegbarkeit TEST | Pods laufen stabil | 15 Pods Running seit Redeploy | [x] Ja | Seit 2026-03-03, 15 Pods seit 2026-03-06 |
| NF-3 | Backup | Taegliche PG Snapshots | StackIT Managed Backup aktiv (DEV 02:00, TEST 03:00 UTC) | [x] Ja | Managed Service |
| NF-4 | CI/CD Robustheit | Zuverlässiger Deploy mit Timeout | `--wait --timeout 15m` fuer alle Environments, Smoke Test nach Deploy, manueller Rollback bei Bedarf | [x] Ja | Concurrency Control aktiv |
| NF-5 | Umgebungstrennung | DEV und TEST isoliert | Separate Namespaces, PG-Instanzen, Buckets, Credentials | [x] Ja | ADR-004 dokumentiert |

**Ergebnis: 5/5 non-funktionale Kriterien erfuellt.**

### Sicherheits- und Compliance-Kriterien

| Nr. | Kriterium | Soll-Zustand | Ist-Zustand | Erfuellt? | Bemerkung |
|-----|-----------|-------------|-------------|-----------|-----------|
| S-1 | PostgreSQL ACL | Zugriff eingeschraenkt (nicht 0.0.0.0/0) | ACL auf `188.34.93.194/32` + Admin-IP | [x] Ja | SEC-01, Terraform enforced |
| S-2 | Secrets-Management | API Keys nicht im Code | GitHub Secrets + K8s Secrets, `.gitignore` | [x] Ja | Redis-PW, PG-PW, S3-Keys |
| S-3 | Supply-Chain-Schutz | GitHub Actions abgesichert | SHA-gepinnte Actions, Least-Privilege Permissions | [x] Ja | 6 Actions auf Commit-SHA |
| S-4 | Datensouveraenitaet | Alle Daten in Deutschland | StackIT Region EU01 Frankfurt | [x] Ja | Vertraglich + technisch |
| S-5 | TLS/HTTPS | HTTPS auf DEV + TEST | HTTPS aktiv — TLSv1.3, ECDSA P-384, Let's Encrypt | [x] Ja | Seit 2026-03-09. cert-manager DNS-01 via Cloudflare |

**Ergebnis: 5/5 Sicherheitskriterien erfuellt.**

### Zusaetzliche Sicherheitsmassnahmen (ueber M1-Anforderungen hinaus)

Die folgenden Massnahmen waren **nicht Teil der M1-Kriterien**, wurden aber im Rahmen eines Cloud-Infrastruktur-Audits (2026-03-04) zusaetzlich umgesetzt:

| Massnahme | Audit-ID | Status |
|-----------|----------|--------|
| NetworkPolicies: Namespace-Isolation DEV ↔ TEST | C5/SEC-03 | ✅ Applied (2026-03-05) |
| DB_READONLY_PASSWORD in K8s Secret | C6 | ✅ Deployed (2026-03-05) |
| Security-Header auf nginx (HSTS, CSP, X-Content-Type-Options) | H8 | ✅ Deployed (2026-03-05) |
| CI/CD Script-Injection-Fix | H11 | ✅ Deployed (2026-03-05) |

Vollstaendiger Audit-Report: [cloud-infrastruktur-audit-2026-03-04.md](../audit/cloud-infrastruktur-audit-2026-03-04.md)

---

## Bekannte Einschraenkungen / Offene Punkte

Diese Punkte sind bekannt und werden in nachfolgenden Meilensteinen adressiert:

| Nr. | Thema | Status | Geplant fuer |
|-----|-------|--------|-------------|
| N-1 | DNS-Eintraege (`dev.chatbot.voeb-service.de`) | Erledigt — A-Records gesetzt (2026-03-05) | ✅ |
| N-2 | TLS/HTTPS (cert-manager + Let's Encrypt) | ✅ Erledigt — HTTPS LIVE seit 2026-03-09 (ECDSA P-384, TLSv1.3) | ✅ |
| N-3 | Embedding-Modell Qwen3-VL-Embedding 8B | ✅ Aktiv auf DEV + TEST | Qwen3-VL-Embedding 8B aktiv (TEST seit 2026-03-08, DEV seit 2026-03-12) |
| N-4 | Authentifizierung (Entra ID / OIDC) | Blockiert — wartet auf VÖB Credentials | M2 |

**Hinweis:** N-1 (DNS), N-2 (TLS) und N-3 (Embedding) sind erledigt. Qwen3-VL-Embedding 8B ist auf DEV + TEST aktiv. Der einzige verbleibende offene Punkt (N-4: Entra ID) hat eine externe Abhaengigkeit (VÖB IT). Die Infrastruktur ist technisch vollstaendig und abgesichert.

---

## Festgestellte Maengel

### Maengelliste

| ID | Beschreibung | Schwere | Frist | Status | Verantwortlicher |
|----|-------------|--------|-------|--------|-----------------|
| — | Keine Maengel festgestellt | — | — | — | — |

---

## Abnahme-Ergebnis

### Empfehlung des Auftragnehmers

Basierend auf den Pruefergebnissen empfiehlt der Auftragnehmer:

- [ ] **Abnahme ohne Maengel**
  - 22/22 Kriterien erfuellt (100%)
  - Alle funktionalen (12/12), non-funktionalen (5/5) und Sicherheitskriterien (5/5) erfuellt
  - System ist funktional vollstaendig und produktiv nutzbar
  - TLS/HTTPS (S-5) seit 2026-03-09 LIVE — Auflage A-1 ist damit erfuellt

### Begruendung

Alle funktionalen (12/12), non-funktionalen (5/5) und Sicherheitskriterien (5/5) sind erfuellt. Die Infrastruktur laeuft stabil seit 2026-02-27 (DEV) bzw. 2026-03-03 (TEST). Die CI/CD-Pipeline ist produktionsreif. TLS/HTTPS wurde am 2026-03-09 aktiviert (Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2) — die urspruengliche Auflage A-1 ist damit erfuellt.

Zusaetzlich wurden im Rahmen eines proaktiven Security-Audits 4 Sicherheitsmassnahmen umgesetzt, die ueber die M1-Anforderungen hinausgehen (NetworkPolicies, Security-Header, Secrets-Haertung, CI/CD-Fix).

### Entscheidung des Auftraggebers

- [ ] Abnahme mit Auflagen erteilt
- [ ] Abnahme verweigert — Begruendung: _______________

---

## Unterschriften

### Auftragnehmer

**Name, Titel**: Nikolaj Ivanov, Tech Lead
**Organisation**: CCJ / Coffee Studios
**Unterschrift**: _________________________ **Datum**: __________

### Auftraggeber

**Name, Titel**: _________________________
**Organisation**: VÖB
**Unterschrift**: _________________________ **Datum**: __________

**Name, Titel**: _________________________ (optional: 2. Signatur)
**Organisation**: VÖB
**Unterschrift**: _________________________ **Datum**: __________

---

## Anlagen

| Anlage | Beschreibung |
|--------|-------------|
| A | [Meilensteinplan](./meilensteinplan.md) — M1 Liefergegenstaende + Akzeptanzkriterien |
| B | [Cloud-Infrastruktur-Audit](../audit/cloud-infrastruktur-audit-2026-03-04.md) — 60 Findings, 4 behoben |
| C | [NetworkPolicy-Analyse](../audit/networkpolicy-analyse.md) — Traffic-Matrix, Design-Entscheidungen |
| D | [Betriebskonzept](../betriebskonzept.md) — Systemuebersicht, Deployment, Backup |
| E | [Sicherheitskonzept](../sicherheitskonzept.md) — Schutzziele, Authentifizierung, Massnahmen |

---

**Protokoll-Version**: 1.0
**Erstellt**: 2026-03-05
**Status**: Vorbereitet — wartet auf Abnahmetermin mit VÖB
