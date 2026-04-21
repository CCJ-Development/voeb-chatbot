# Kosten-Kalkulation für neuen Kunden

**Zielgruppe:** Tech Lead / Sales im Kunden-Erstgespräch
**Dauer:** 30 min
**Phase:** 0 (Angebotsphase, vor Projektstart)

Dieses Runbook ist ein Kalkulations-Template, das die laufenden StackIT-Kosten für einen neuen Kunden auf Basis dessen Dimensionierungs-Bedarfs ermittelt. Grundlage: StackIT Preisliste v1.0.36 (03.03.2026).

---

## 1. Dimensionierungs-Fragen an den Kunden

Vor der Kalkulation: Eckdaten klären.

| Frage | Typische Antwort | Implikation |
|---|---|---|
| **Erwartete gleichzeitige User?** | 50 / 150 / 500 | Node-Größe |
| **Dokumentenmenge initial?** | < 1.000 / 1.000–10.000 / > 10.000 | OpenSearch-Storage, Indexierungs-Zeit |
| **Wachstum Dokumente/Monat?** | < 100 / 100–1.000 / > 1.000 | PG Storage, LLM-Token-Verbrauch |
| **HA notwendig?** | DEV + PROD oder nur PROD mit HA? | PG Flex 2.4 Single vs. 4.8 HA |
| **TEST-Umgebung gewünscht?** | Ja / Nein | +115 EUR/Mo |
| **Backup-Retention?** | 30d (Default) oder länger? | Backup-Storage-Kosten |
| **Kommunikations-Kanal?** | Teams / Slack / E-Mail | Monitoring-Alert-Konfiguration |
| **Datenschutz-Anforderungen?** | Standard / Banking / öffentlich | Wahl EE-Features (bei uns: ext-Module) |

---

## 2. Tarif-Bausteine (StackIT Preisliste v1.0.36)

Alle Preise **netto, zzgl. MwSt.**

| Ressource | Konfig | EUR/Monat |
|---|---|---|
| **SKE Cluster Management** | 1 Cluster (Control Plane) | 71,71 |
| **Worker Node c1a.4d** | 4 vCPU, 8 GB RAM | 134,67 |
| **Worker Node c1a.8d** | 8 vCPU, 16 GB RAM | 269,34 |
| **Worker Node c1a.16d** | 16 vCPU, 32 GB RAM | 538,69 |
| (Legacy `g1a.*`-Namen werden ggf. weiter verwendet; Preise identisch bis zur Umstellung) | | |
| **PostgreSQL Flex 2.4 Single** | 2 vCPU, 4 GB RAM, ohne HA | 90,71 |
| **PostgreSQL Flex 4.8 Single** | 4 vCPU, 8 GB RAM, ohne HA | 181,42 |
| **PostgreSQL Flex 4.8 HA Replica** | 4 vCPU, 8 GB RAM, 3 Nodes | 271,75 |
| **Object Storage Premium EU01** | pro GB/Monat | 0,027 |
| **Load Balancer Essential-10** | 1 IP, bis 10 Gbps | 9,39 |
| **AI Model Serving** | pro verbrauchtem Token (Chat + Embedding) | variabel |
| **Container Registry** | inkl. bei Plattform-Nutzung | 0 |

---

## 3. Rechen-Szenarien

### 3.1 Szenario A: „Klein" (50 User, wenige Dokumente)

**Dimensionierung:**
- 1 SKE-Cluster für DEV, 1 für PROD (2 Cluster total)
- Worker Nodes: 2× c1a.4d pro Cluster
- PG: Flex 2.4 Single für beide
- Object Storage: ~10 GB initial

| Posten | DEV | PROD | Summe |
|---|---|---|---|
| SKE Management | 71,71 | 71,71 | 143,42 |
| 2× Worker c1a.4d | 269,34 | 269,34 | 538,68 |
| PG Flex 2.4 Single | 90,71 | 90,71 | 181,42 |
| Object Storage (~10 GB) | 0,27 | 0,27 | 0,54 |
| Load Balancer | 9,39 | 9,39 | 18,78 |
| **Summe** | **441,42** | **441,42** | **882,84** |

Plus LLM-Serving: bei 50 User × 30 Tagen × 5 Queries × 10.000 Token/Query ≈ **75 Mio. Tokens/Monat**. Preis je nach Modell (StackIT AI Model Serving) variabel — für GPT-OSS 120B grob 50–100 EUR/Monat.

**Total Szenario A: ca. 950–1.000 EUR/Monat.**

### 3.2 Szenario B: „Mittel" (150 User, PROD mit HA)

**Dimensionierung (wie VÖB):**
- 2 Cluster (DEV + PROD dedicated)
- DEV: 2× c1a.4d, PG Flex 2.4 Single
- PROD: 2× c1a.8d, PG Flex 4.8 HA Replica

| Posten | DEV | PROD | Summe |
|---|---|---|---|
| SKE Management | 71,71 | 71,71 | 143,42 |
| Worker Nodes | 269,34 (2× c1a.4d) | 538,68 (2× c1a.8d) | 808,02 |
| PG | 90,71 (Flex 2.4) | 271,75 (Flex 4.8 HA) | 362,46 |
| Object Storage (~20 GB PROD) | 0,27 | 0,54 | 0,81 |
| Load Balancer | 9,39 | 9,39 | 18,78 |
| **Summe** | **441,42** | **892,07** | **1.333,49** |

Plus LLM: 150 User × 30 × 5 × 10.000 ≈ 225 Mio. Tokens/Monat → ca. 150–300 EUR/Monat.

**Total Szenario B: ca. 1.500–1.650 EUR/Monat.**

### 3.3 Szenario C: „Groß" (500 User, HA, 3-Node-PG)

**Dimensionierung:**
- 2 Cluster
- DEV: 2× c1a.4d (wie klein)
- PROD: 3× c1a.16d oder 2× c1a.16d + Bursting, PG Flex 4.8 HA Replica + größeres Storage

| Posten | DEV | PROD | Summe |
|---|---|---|---|
| SKE Management | 71,71 | 71,71 | 143,42 |
| Worker Nodes | 269,34 | 1.077,38 (2× c1a.16d) | 1.346,72 |
| PG | 90,71 | 271,75 (oder mehr bei größeren Flavors) | 362,46 |
| Object Storage (~100 GB) | 0,27 | 2,70 | 2,97 |
| Load Balancer | 9,39 | 9,39 | 18,78 |
| **Summe** | **441,42** | **1.432,93** | **1.874,35** |

Plus LLM: 500 User × 30 × 5 × 10.000 ≈ 750 Mio. Tokens/Monat → ca. 500–900 EUR/Monat.

**Total Szenario C: ca. 2.400–2.800 EUR/Monat.**

---

## 4. Optionale Posten

### 4.1 TEST-Umgebung

Wenn gewünscht:
- PG Flex 2.4 Single: 90,71 EUR
- Object Storage: ~0,27 EUR
- Load Balancer: 9,39 EUR (oder shared mit DEV-Cluster)
- **Summe TEST:** ~100–115 EUR/Monat

TEST teilt den DEV-Cluster (Node Pool `devtest`), deshalb keine zusätzlichen Compute-Kosten.

### 4.2 Eigene Monitoring-Cluster

Bei strikter Trennung: separate kube-prometheus-stack-Installation auf eigenem Nano-Cluster. Praktisch nicht empfohlen — Ressourcen auf DEV/PROD-Cluster sind ausreichend. Wenn doch: +ca. 200–300 EUR/Monat.

### 4.3 Loki (Log-Aggregation)

Läuft im Monitoring-Namespace, nutzt PVC (Block Storage Premium). 20 GiB bei 30-Tage-Retention: ca. 2 EUR/Monat Storage, keine Lizenzkosten.

### 4.4 DNS + TLS

- Let's Encrypt: **kostenlos**
- Cloudflare DNS-only: **kostenlos** (Free Tier reicht)
- Domain-Registrar-Kosten: Kunden-seitig

### 4.5 Backup-Zusatzkosten

- **Bei unter 100 GB PG-DB:** StackIT Backup-Kosten ~5–10 EUR/Monat inkludiert
- **Bei größerer DB:** pro GB/h zusätzlich

---

## 5. CCJ-Leistungen (Service-Kosten)

**Nicht StackIT, sondern CCJ-seitig:**

| Leistung | Aufwand | Einmalig / laufend |
|---|---|---|
| **Erst-Setup (12-15 h nach Master-Playbook)** | ~2 Personentage | einmalig |
| **Initial-Konfiguration + 1. Rollout** | ~3-5 Personentage | einmalig |
| **Kunden-Onboarding + Schulung** | ~1-2 Personentage | einmalig |
| **Betrieb (Upstream-Sync, Rollback, Monitoring)** | ~1-3 Personentage/Monat | laufend |
| **Incident-Response 24/7** | separat kalkulieren | optional |

Typisches Projekt: **5-10 PT einmalig** + **1-3 PT/Monat laufend**.

---

## 6. Kalkulations-Template für Kundengespräch

```
───────────────────────────────────────────────────────────
KUNDE: <CUSTOMER_NAME>
SZENARIO: <Klein / Mittel / Groß>
HA-PROD: <Ja/Nein>
USERS: <N>
───────────────────────────────────────────────────────────

StackIT Infrastruktur (monatlich, netto):
  DEV:         ___,__ EUR
  PROD:        ___,__ EUR
  Optional: TEST  ___,__ EUR
  ─────────────────────
  Summe Infra: ___,__ EUR/Monat

StackIT AI Model Serving (geschätzt, verbrauchsabhängig):
  Chat:         ___ Mio Tokens × Preis = ___,__ EUR
  Embedding:    ___ Mio Tokens × Preis = ___,__ EUR
  ─────────────────────
  Summe LLM:   ___,__ EUR/Monat

GESAMT STACKIT: ___,__ EUR/Monat (netto)

CCJ Einmal-Kosten:
  Setup + Rollout + Onboarding: ___ PT × ___ EUR/PT = ___,__ EUR

CCJ Laufend:
  Betrieb:     ___ PT/Monat × ___ EUR/PT = ___,__ EUR/Monat

───────────────────────────────────────────────────────────
ZUSAMMENFASSUNG
───────────────────────────────────────────────────────────
Einmalig (CCJ):      ___,__ EUR
Monatlich (StackIT): ___,__ EUR
Monatlich (CCJ):     ___,__ EUR
─────────────────────
MONATLICH GESAMT:    ___,__ EUR
───────────────────────────────────────────────────────────
```

---

## 7. Skalierungs-Hinweise

### 7.1 Vertikal hoch

Bei steigenden Anforderungen:
- Worker: c1a.4d → c1a.8d → c1a.16d (Terraform `machine_type`-Variable ändern, `apply`)
- PG: Flex 2.4 → 4.8 → 8.8 (Terraform `pg_flavor`)
- PG → HA: `pg_replicas = 3` + `pg_flavor.cpu >= 4`

### 7.2 Horizontal (mehr Replicas)

- API-Server: `values-prod.yaml` → `api.replicaCount: 3`
- Web-Server: analog
- Celery-Worker: einzeln skalierbar pro Worker-Typ

### 7.3 Storage

- PG: `pg_storage_size` in Terraform (aktuell 20 GB)
- OpenSearch: PVC im Helm-Chart (aktuell 30 GB) — **Achtung:** PVC ist im StatefulSet immutable, Vergrößerung erfordert StatefulSet + PVC manuell recreaten.
- Object Storage: skalt automatisch

### 7.4 Kostenoptimierung

- TEST abschalten (wie VÖB): -115 EUR/Monat
- Node-Downgrade bei niedriger Auslastung: -140 EUR pro Node-Stufe
- OpenSearch-Retention kürzen: weniger PVC-Storage

---

## 8. Typische Erwartungen im Kundengespräch

**Frage:** „Was kostet das genau?"
**Antwort:** Je nach Dimensionierung 900–2.800 EUR StackIT + CCJ-Leistungen. Detailkalkulation nach Klärung der Dimensionierung.

**Frage:** „Können wir klein anfangen und wachsen?"
**Antwort:** Ja. Start mit Flex 2.4 Single und c1a.4d (Szenario A), Upgrade per Terraform-Variable ohne Downtime (Flavor-Change ist eine StackIT-Wartungsoperation, ca. 30 Min Wartung).

**Frage:** „Sind die Kosten planbar?"
**Antwort:** Fixkosten (>99 %) sind planbar. Variabel: nur AI Model Serving (Token-abhängig). Mit ext-token setzen wir Per-User-Limits — damit sind auch die LLM-Kosten deckelbar.

**Frage:** „Gibt es Skaleneffekte?"
**Antwort:** StackIT hat keine öffentlichen Rabatte, aber bei Großprojekten und Pilotkunden sind Verhandlungen möglich.

---

## 9. Lessons Learned (aus VÖB-Projekt)

### 9.1 Node-Downgrade als Kostensparer

VÖB startete mit g1a.8d, wurde 2026-03-16 auf g1a.4d downgegradet (DEV+TEST) = -283 EUR/Monat. PROD behielt g1a.8d wegen HA-Bedarf, steht aber ebenfalls zur Downgrade-Diskussion (Auslastung nur ~15–20 % CPU).

**Lesson:** Nach 1-2 Monaten Live-Betrieb Prometheus-Auslastung anschauen — oft sind Nodes überdimensioniert.

### 9.2 TEST als kostenpflichtige Reserve

VÖB hatte TEST für 3 Monate heruntergefahren (0 Pods), aber PG + Bucket + LB liefen weiter → 115 EUR/Monat ohne Nutzen. Am 2026-04-21 komplett abgebaut.

**Lesson:** Scale-to-Zero reicht nicht. Für echte Kostenersparnis: TEST-Infrastruktur abbauen (nicht nur Pods).

### 9.3 Monitoring-Cluster auf eigenen Resources

Anfangs Überlegung, Monitoring auf separatem Cluster zu betreiben → Kosten + Komplexität zu hoch. Jetzt laufen 9 Monitoring-Pods im gleichen Cluster wie Workloads (Namespace-Trennung). 

**Lesson:** Bei <5000 Pods: gleicher Cluster reicht. Separate Cluster erst bei Enterprise-Scale oder strikter Blast-Radius-Trennung.

---

## 10. Checkliste

Vor dem Kundengespräch:
- [ ] Dimensionierungs-Fragen geklärt
- [ ] Szenario (A/B/C) vorgeschlagen
- [ ] Preisliste-Stand geprüft (StackIT-Portal / Release-Notes)
- [ ] Kalkulationstemplate ausgefüllt
- [ ] Einmal-Kosten + laufende Kosten getrennt ausgewiesen
- [ ] Skalierungs-Option erwähnt (Upgrade ohne Downtime)
- [ ] ext-token für Kosten-Cap erwähnt

---

## 11. Referenzen

- **Aktuelle Kosten im VÖB-Projekt:** `docs/referenz/technische-parameter.md` §7
- **Node-Kostenvergleich:** `docs/referenz/kostenvergleich-node-upgrade.md`
- **Kostenoptimierung DEV/TEST:** `docs/referenz/kostenoptimierung-dev-test.md`
- **StackIT Preisliste:** https://stackit.com/en/asset/download/.../STACKIT_price_list.pdf
- **AI Model Serving Pricing:** https://docs.stackit.cloud/products/data-and-ai/ai-model-serving/
