# Phase 5: Dokumentation vs. Realitaet Abgleich

**Audit-Datum:** 2026-03-24
**Verglichene Dokumente:** technische-parameter.md, sicherheitskonzept.md, betriebskonzept.md, backup-recovery-konzept.md, monitoring-konzept.md, ADR-001 bis ADR-006, secret-rotation.md

---

## 1. Technische Parameter SSOT (technische-parameter.md)

**Letzte Aktualisierung laut Datei: 2026-03-19**

| Zeile | Dokumentiert | Realitaet (2026-03-24) | Gap? |
|---|---|---|---|
| 14 | K8s DEV: v1.33.8 | Cluster: v1.33.9 (beide Nodes) | **JA — Version veraltet** |
| 19 | PROD Pods: 19 | Projekt-Status sagt 20 (OpenSearch) | **JA — 20 Pods** |
| 25 | DEV HTTPS: "TEMPORAER DEAKTIVIERT" | DEV HTTPS LIVE seit 2026-03-22 | **JA — veraltet** |
| 26 | Auth: "basic" fuer alle Envs | DEV ist jetzt `oidc` (seit 2026-03-23) | **JA — Auth aktualisieren** |
| 42 | LB DEV: "DNS-Update pending" | DNS korrekt seit 2026-03-22 | **JA — Kommentar entfernen** |
| 58 | HSTS DEV: "Deaktiviert" | Sollte reaktiviert sein (HTTPS live) | **JA — pruefen + aktualisieren** |
| 62 | NP DEV: "5 Policies" | Cluster: 7 Policies | **JA — 7 Policies** |
| 63 | NP PROD: "Offen" | Bestaetigt offen (Phase 4 HIGH) | Korrekt dokumentiert |
| 64 | NP Monitoring: "7 Policies pro Cluster" | DEV: 7 (2 fehlen von 9 im Repo) | **JA — korrigieren** |
| 370-375 | Kubeconfig PROD: gueltig bis 2026-06-09 | PROD Kubeconfig expired/unauthorized | **JA — KRITISCH** |

---

## 2. Sicherheitskonzept (sicherheitskonzept.md, v0.8)

| Abschnitt | Dokumentiert | Realitaet | Gap? |
|---|---|---|---|
| Zeile 49 | TEST: "LIVE seit 2026-03-03" | TEST heruntergefahren seit 2026-03-19 | **JA** |
| Zeile 50 | PROD Auth: "Temporaer basic" | PROD noch basic, aber DEV jetzt OIDC | **JA — DEV-Aenderung fehlt** |
| Zeile 136 | Entra ID: "BLOCKIERT" | DEV Login funktioniert (2026-03-23) | **JA — aktualisieren** |
| Zeile 163-168 | Entra ID Infos: "AUSSTEHEND" | Tenant ID, Client ID+Secret, Redirect URI — alle erhalten | **JA — 6 Items aktualisieren** |
| Zeile 336 | OpenSearch DEV Passwort: "OnyxDev1!" | Bestaetigt — Chart-Default aktiv auf DEV | Korrekt (aber Risiko beachten) |
| NP-Abschnitt | "5 Policies DEV" | 7 Policies deployed | **JA** |
| SEC-03 | NP PROD: offen | Bestaetigt | Korrekt |

---

## 3. Betriebskonzept (betriebskonzept.md, v0.8)

| Abschnitt | Gap? | Details |
|---|---|---|
| Architektur-Diagramm | **JA** | DEV zeigt 17 Pods — korrekt. PROD zeigt 20 Pods inkl. OpenSearch — korrekt. Aber: TEST-Status koennte deutlicher sein. |
| Auth-Beschreibung | **JA** | Zeigt AUTH_TYPE: basic fuer alle — DEV ist jetzt OIDC |
| Deploy-Pipeline | OK | Korrekt beschrieben |

---

## 4. Backup-Recovery-Konzept (v0.2)

| Abschnitt | Gap? | Details |
|---|---|---|
| Terraform State | Korrekt dokumentiert | "Lokale Datei + .tfstate.backup" — Risiko anerkannt |
| PG Backup-Schedule | OK | DEV 02:00, TEST 03:00, PROD 01:00 — korrekt |
| OpenSearch-Backup | OK | "Kein dediziertes Backup, rekonstruierbar" — korrekt |
| Restore-Test | OK | Letzter Test 2026-03-15, naechster 2026-06-15 |

---

## 5. ADR-Status

| ADR | Dokumentierter Status | Realer Status | Gap? |
|---|---|---|---|
| ADR-001 | Akzeptiert | Korrekt | Nein |
| ADR-002 | Akzeptiert | Korrekt | Nein |
| ADR-003 | Akzeptiert (v1.2) | Korrekt. Nachtrag zu Sealed Secrets korrekt ("nicht implementiert, akzeptiertes Risiko") | Nein |
| ADR-004 | Akzeptiert (v1.0) | **Veraltet** — Keine Erwaehnung von TEST-Shutdown (seit 2026-03-19) | **JA** |
| ADR-005 | Akzeptiert (v1.0) | Korrekt — Addendum fuer g1a.4d-Downgrade vorhanden | Nein |
| ADR-006 | **Proposed** | OIDC ist auf DEV implementiert — ADR sollte "Akzeptiert" sein | **JA** |

**Fehlende ADRs:**
- OIDC-Implementierungsentscheidungen (PKCE deaktiviert, VALID_EMAIL_DOMAINS leer) nicht als ADR dokumentiert. Relevant fuer Audit-Nachvollziehbarkeit.

---

## 6. Monitoring-Konzept

| Abschnitt | Gap? | Details |
|---|---|---|
| Deployment-Status | OK | "Deployed 2026-03-10" korrekt |
| Pods | **JA** | Dokument sagt "11 Pods DEV Monitoring" — Cluster hat tatsaechlich 11 (7 Basis + 4 Exporter inkl. TEST-Exporter) |
| NetworkPolicies | **JA** | "7 Policies" — aber 2 aus dem Repo (08, 09) fehlen im Cluster |
| Alert-Rules | Nicht verifiziert | Dokument sagt 20 DEV / 22 PROD — nicht gegen Cluster geprueft |

---

## 7. Secret-Rotation Runbook

| Abschnitt | Gap? | Details |
|---|---|---|
| Prozeduren | OK | Ausfuehrlich dokumentiert fuer alle 7 Secret-Typen |
| **Schedule** | **FEHLEND** | Kein Rotation-Schedule (wann wird was rotiert?) |
| **Entra ID Secret** | **FEHLEND** | Kein Monitoring fuer Secret-Ablauf |
| Kubeconfig | **JA** | "Naechste Expiration PROD: 2026-06-09" — aber PROD Kubeconfig ist JETZT expired |

---

## 8. Zusammenfassung der Gaps

### Kritisch (sofort korrigieren)

| # | Dokument | Gap |
|---|---|---|
| G-01 | technische-parameter.md | PROD Kubeconfig als gueltig dokumentiert — tatsaechlich expired |
| G-02 | technische-parameter.md | DEV HTTPS als "DEAKTIVIERT" — ist LIVE |
| G-03 | sicherheitskonzept.md | Entra ID als "BLOCKIERT" — DEV Login funktioniert |
| G-04 | secret-rotation.md | PROD Kubeconfig Ablauf falsch / nicht aktuell |

### Wichtig (innerhalb 1 Woche)

| # | Dokument | Gap |
|---|---|---|
| G-05 | technische-parameter.md | K8s Version, Pod-Count, Auth, NP-Count, HSTS — 8 veraltete Eintraege |
| G-06 | sicherheitskonzept.md | TEST-Status, Auth-Status, Entra-ID-Status — 6 veraltete Abschnitte |
| G-07 | ADR-006 | Status "Proposed" → "Akzeptiert" (OIDC implementiert) |
| G-08 | ADR-004 | TEST-Shutdown nicht dokumentiert |

### Nice-to-Have

| # | Dokument | Gap |
|---|---|---|
| G-09 | monitoring-konzept.md | NP-Count korrigieren (7 statt 9) |
| G-10 | betriebskonzept.md | Auth-Typ fuer DEV aktualisieren |
| G-11 | Fehlend | ADR fuer OIDC-Implementierung (PKCE-Entscheidung, Email-Domain) |
| G-12 | secret-rotation.md | Rotation-Schedule ergaenzen |
