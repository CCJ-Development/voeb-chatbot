# ADR-005: Node-Upgrade g1a.4d → g1a.8d

**Status**: Akzeptiert
**Datum**: 2026-03-06
**Entscheider**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Bezug**: ADR-004 (Umgebungstrennung), Upstream PR #9014 (Lightweight Mode entfernt)

---

## Kontext

Upstream Onyx hat mit PR #9014 den Lightweight Background Worker Mode entfernt. Statt eines konsolidierten Workers werden jetzt 8 separate Celery-Deployments benoetigt:

1. celery-beat (Scheduler)
2. celery-worker-primary (Koordination)
3. celery-worker-light (Vespa-Ops, Permissions)
4. celery-worker-heavy (Pruning)
5. celery-worker-docfetching (Connector-Daten)
6. celery-worker-docprocessing (Indexing Pipeline)
7. celery-worker-monitoring (Health, Metrics)
8. celery-worker-user-file-processing (User-Uploads)

Mit dem bisherigen g1a.4d Node-Typ (4 vCPU, 16 GB RAM, 50 GB Disk) reichen die Ressourcen nicht fuer 16 Pods (DEV) bzw. 15 Pods (TEST) pro Environment.

## Entscheidung

**Upgrade von g1a.4d auf g1a.8d** (8 vCPU, 32 GB RAM, 100 GB Disk) fuer den bestehenden Node Pool `devtest` (2 Nodes).

## Alternativen

| Alternative | vCPU | RAM | Nodes | Gesamt CPU | Gesamt RAM | Kosten/Mo |
|-------------|------|-----|-------|-----------|-----------|-----------|
| **A: 2x g1a.4d (Status quo)** | 4 | 16 GB | 2 | ~7 CPU | ~31 GB | ~426 EUR |
| **B: 3x g1a.4d** | 4 | 16 GB | 3 | ~10.5 CPU | ~46 GB | ~568 EUR |
| **C: 2x g1a.8d (gewaehlt)** | 8 | 32 GB | 2 | ~15.8 CPU | ~56.6 GB | ~868 EUR |

## Begruendung

- **Alternative A** scheidet aus: Nicht genug CPU/RAM fuer 8 Celery-Worker pro Environment
- **Alternative B** waere moeglich, aber: 3 Nodes = hoehere Management-Komplexitaet, Node-Affinity-Probleme (welcher Pod auf welchem Node?), kein klarer Vorteil gegenueber C
- **Alternative C** gewaehlt:
  - Einfachste Loesung: 1 Node pro Environment, klare Zuordnung
  - CPU-Auslastung nach Upgrade: ~5% (813m/15.820m) — massig Headroom
  - RAM-Auslastung nach Upgrade: ~28% (16.345 Mi/56.6 Gi)
  - PROD-Sizing: 2x g1a.8d reicht fuer ~150 gleichzeitige User (~40% CPU, ~25% RAM)
  - Disk: 100 GB loest FreeDiskSpaceFailed-Warning (vorher 50 GB)

## Kosten-Impact

| Umgebung | Vorher (g1a.4d) | Nachher (g1a.8d) | Delta |
|----------|-----------------|-------------------|-------|
| DEV+TEST | ~426 EUR/Mo | ~868 EUR/Mo | +442 EUR/Mo |
| PROD (geplant) | ~426 EUR/Mo | ~964 EUR/Mo | +538 EUR/Mo |

## Umsetzung

- Terraform: `deployment/terraform/environments/dev/main.tf` → `machine_type = "g1a.8d"`, `volume_size = 100`
- Terraform apply: 10m11s, 0 added, 1 changed, 0 destroyed
- Helm: 8 Celery-Worker in values-dev.yaml und values-test.yaml aktiviert
- Verifiziert: DEV 16/16 Pods Running, TEST 15/15 Pods Running, 0 Restarts, Health OK

## Konsequenzen

- ~~K8s v1.32.12 ist laut StackIT deprecated — Update auf v1.33+ einplanen~~ → ✅ Erledigt: K8s v1.33.8 (2026-03-08)
- Recreate-Strategie beibehalten — Grund ist DB Connection Pool Exhaustion bei RollingUpdate (alte + neue Pods erschoepfen max_connections), nicht CPU-Mangel. Wird auf allen Environments (DEV, TEST, PROD) aktiv erzwungen.
- PROD-Sizing steht fest: 2x g1a.8d (eigener Cluster, ADR-004)

---

## Addendum: Downgrade auf g1a.4d (2026-03-16)

**Die Annahme, dass g1a.4d nicht ausreicht (Alternative A), wurde revidiert.** Nach Analyse der tatsaechlichen Ressourcennutzung (CPU Actual: 5,8% bei g1a.8d) wurden die Resource Requests fuer DEV/TEST um 40-80% gesenkt. Damit passen alle Workloads wieder auf 2x g1a.4d.

- **Terraform:** `machine_type = "g1a.4d"` in `environments/dev/main.tf` (2026-03-16)
- **Einsparung:** 283,18 EUR/Mo (DEV+TEST: 868 → 585 EUR/Mo)
- **Auslastung:** Node 1: 94% CPU Requests, Node 2: 92% (eng aber stabil)
- **PROD bleibt g1a.8d** (eigener Cluster, unveraendert)
- **Rollback:** `machine_type = "g1a.8d"` + `terraform apply` (~10 Min)
- **Details:** `audit-output/kostenoptimierung-ergebnis.md`, `docs/infrastruktur-review.md`

---

## Addendum 2: PROD-Downgrade auf g1a.4d (2026-04-26)

**PROD ebenfalls auf g1a.4d herabgestuft.** Voraussetzungen waren erfuellt durch zwei vorhergehende Optimierungen:

1. **Vespa-Disable** (2026-04-25): Mit Sync #6 (Upstream PR #10330) ist `ONYX_DISABLE_VESPA=true` verfuegbar. Vespa-Pod entfernt (vorher Zombie-Mode 100m/512Mi/4Gi-Limit), PVCs (DEV 20 GiB + PROD 50 GiB) geloescht.
2. **Worker-Resource-Rebalance** (2026-04-25/26): Resource Requests aller Onyx-Komponenten nach 30-Tage-Prometheus-Werktagsdaten neu dimensioniert (PROD: 97 User, 1.476 Sessions/30d, 10.165 Messages/30d). Cluster-CPU-Requests Onyx-Komponenten 8.450m → 2.350m. OpenSearch RAM-Limit 4 → 5 GiB (30d-Peak 3.469 Mi). Plus Monitoring-Tuning (Prometheus, Loki, redis-operator).

**Terraform:** `machine_type = "g1a.4d"` in `environments/prod/main.tf` (2026-04-26). `terraform apply` 12m1s, 0 added, 1 changed, 0 destroyed. Rolling Node-Replacement, keine Pending Pods.

**Auslastung nach Downgrade (Live, Werktag-Avg):** ca. 4–8 % CPU, 30–60 % RAM (entspannt, nicht eng wie auf DEV). Cluster-CPU-Requests 5.824m / 7.900m allocatable = **74 %**, Werktagsspitze (p99) 1.573m = 20 % der Allocatable.

**Einsparung:** 283,18 EUR/Mo (PROD Worker Nodes 566,36 → 283,18 EUR/Mo). Total beider Environments: 1.434 → 1.151 EUR/Mo (−20 %).

**Rollback:** `machine_type = "g1a.8d"` + `terraform apply` (~10 Min Rolling Update).

**Details:** `docs/CHANGELOG.md` Eintraege 2026-04-25 + 2026-04-26, `.claude/rules/voeb-projekt-status.md`, `.claude/rules/fork-management.md` Sync #6 PROD-Section.

---

## Approval & Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author (CCJ) | Nikolaj Ivanov | 2026-03-06 | [x] |
| Auftraggeber (VÖB) | [TBD] | [TBD] | [ ] |

**Version:** 1.0
