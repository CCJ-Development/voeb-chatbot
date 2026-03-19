# Analyse: OpenSearch vs. Vespa im Onyx-Oekosystem

**Datum:** 2026-03-19
**Autor:** Claude Code (Opus 4.6 Max) im Auftrag von Nikolaj Ivanov
**Kontext:** VoeB Chatbot Fork — Auswirkungsanalyse fuer Upstream-Sync-Strategie
**Klassifikation:** Intern / Entscheidungsgrundlage

---

## 1. Zusammenfassung

**Onyx migriert aktiv von Vespa zu OpenSearch. Dies ist keine optionale Ergaenzung, sondern ein vollstaendiger Backend-Wechsel.** Die Migration begann im Dezember 2025, wurde in v2.8.0 (Januar 2026) offiziell angekuendigt, und ist seit v3.0.0 (Maerz 2026) der Default. In v4.0.0 wird Vespa vollstaendig entfernt — der Zeitpunkt ist unklar, aber Onyx hat angedeutet dass "nicht viele Minor-Versionen von v3 vor v4 erwartet werden".

Fuer unseren Fork bedeutet das: **Wir koennen bei Vespa bleiben solange wir auf v3.x synchen, muessen aber mittelfristig (geschaetzt Q2-Q3 2026) auf OpenSearch wechseln oder den Fork einfrieren.** Die gute Nachricht: OpenSearch braucht weniger Ressourcen als Vespa und passt auf unsere Infrastruktur.

---

## 2. Upstream-Strategie

### 2.1 Zeitachse: Von Vespa-Begeisterung zum Wechsel

| Datum | Event | Quelle |
|-------|-------|--------|
| Sep 2024 | Vespa-Blog: "Why Danswer uses Vespa" — Lobeshymne, Migration von Dual-Engine zu Vespa-Only | [Vespa Blog](https://blog.vespa.ai/why-danswer-users-vespa/) |
| Sep 2025 | Vespa-Blog: "Onyx optimizes costs on Vespa Cloud" — 120 Nodes, 960 vCPUs, $114/h | [Vespa Blog](https://blog.vespa.ai/using-vespa-cloud-resource-suggestions-to-optimize-costs/) |
| **29 Dez 2025** | **Erster OpenSearch-Commit**: `opensearch-py 3.0.0` hinzugefuegt (PR #7103) | Git-History |
| 30 Dez - 12 Jan | OpenSearch Schema, Client, Queries, Document Index Interface + Feature Parity (PRs #7110-#7372) | Git-History |
| **13 Jan 2026** | **v2.8.0: Offizielle Ankuendigung** der Migration Vespa → OpenSearch | [Onyx Changelog](https://docs.onyx.app/changelog) |
| Jan-Feb 2026 | Migration-Tasks, DB-Tabellen, Admin UI, Progress-Anzeige (PRs #8013-#8575) | Git-History |
| **18 Feb 2026** | **v2.11.0**: Migration macht Fortschritt, ~200k Chunks/Stunde | [Onyx Changelog](https://docs.onyx.app/changelog) |
| **01 Maerz 2026** | **v2.12.0**: Onyx Cloud wird auf OpenSearch migriert, "progressing smoothly" | [Onyx Changelog](https://docs.onyx.app/changelog) |
| **09 Maerz 2026** | **`feat(opensearch): Enable by default`** (PR #9211) — OpenSearch wird Default | Git-History: `8c848da73` |
| **10 Maerz 2026** | **v3.0.0 Release (stable)**: OpenSearch-Migration offiziell stabil | [GitHub Releases](https://github.com/onyx-dot-app/onyx/releases) |
| 13 Maerz 2026 | v3.0.2: `LICENSE_ENFORCEMENT_ENABLED` default=true | [GitHub Releases](https://github.com/onyx-dot-app/onyx/releases) |
| **17 Maerz 2026** | **Unser Upstream-Sync #3**: OpenSearch-Defaults kommen rein, wir setzen alles auf false | Commit `5f7dc40e1` |
| 19 Maerz 2026 | v3.0.3 (aktuellste Version): Improved migration tasks | [GitHub Releases](https://github.com/onyx-dot-app/onyx/releases) |

**Bemerkenswert:** Noch im September 2025 bewirtschaftete Onyx einen 120-Node Vespa Cloud Cluster. Drei Monate spaeter begann die Migration weg von Vespa. Der Wechsel kam ueberraschend schnell.

### 2.2 Offizielle Begruendung (v2.8.0 Changelog)

> "OpenSearch is a FOSS fork of ElasticSearch, expected to be easier to develop with, provide equal if not better search performance, and importantly **have a smaller memory footprint**."

Die drei Hauptgruende laut Onyx:
1. **Einfachere Entwicklung** — OpenSearch hat eine breitere Entwickler-Community und bessere Tooling-Unterstuetzung
2. **Gleiche oder bessere Suchperformance** — Hybride Suche (Vektor + BM25) funktioniert in beiden
3. **Kleinerer Memory-Footprint** — Onyxs eigener Benchmark: 128 GB Vespa vs. 8 GB OpenSearch (Faktor 16x)

### 2.3 Upgrade-Pfad und Vespa-Removal

Onyx hat einen **Pflicht-Upgrade-Pfad** definiert:

```
v2.x → v3.x (Dual-Write, Migration) → v4.0.0 (Vespa entfernt)
```

**Wer v3 ueberspringt, verliert ALLE indizierten Daten.** v3.x ist die Uebergangsphase in der beide Engines parallel laufen und die Migration stattfindet.

Zitat aus dem Changelog: *"We do not anticipate many minor versions of v3 before moving to v4."* — Das deutet auf wenige Wochen bis Monate hin.

### 2.4 Vespa-Probleme die den Wechsel motivierten

Aus GitHub Issues:
- **AVX2-Pflicht** ([#697](https://github.com/onyx-dot-app/onyx/issues/697)): Vespa braucht AVX2 CPU-Instruktionen (ab Intel Haswell 2013). Aeltere Server crashen mit "ILLEGAL INSTRUCTION"
- **Hoher RAM-Verbrauch** ([#3427](https://github.com/onyx-dot-app/onyx/issues/3427)): 64 GB System, Vespa wird OOM-gekillt
- **Komplexitaet**: Vespa hat proprietaere Query-Sprache (YQL), eigenes Schema-Format, eigenes Deployment-Modell

---

## 3. Technische Architektur

### 3.1 Document Index Abstraktion

Onyx hat eine **Factory-Pattern** Architektur fuer Document Indexing:

```
                    ┌────────────────────────────────────────┐
                    │           factory.py                    │
                    │  get_default_document_index() → 1 Index │  ← Retrieval
                    │  get_all_document_indices()   → N Indices│  ← Indexing
                    └────────┬────────────────────┬──────────┘
                             │                    │
              ┌──────────────┘                    └────────────────┐
              ▼                                                    ▼
   ┌──────────────────────┐                        ┌──────────────────────────┐
   │      VespaIndex       │                        │ OpenSearchOldDocumentIndex│
   │   (interfaces.py OLD) │                        │   (Wrapper → NEW impl)   │
   └──────────┬───────────┘                        └──────────┬───────────────┘
              │                                                │
              ▼                                                ▼
   ┌──────────────────────┐                        ┌──────────────────────────┐
   │ VespaDocumentIndex    │                        │ OpenSearchDocumentIndex   │
   │ (OLD interface impl)  │                        │ (interfaces_new.py NEW)  │
   └──────────────────────┘                        └──────────────────────────┘
```

**Zwei Interface-Generationen existieren parallel:**
- `interfaces.py` (OLD) — wird von Vespa genutzt, `DocumentIndex` mit `BaseIndex + HybridCapable`
- `interfaces_new.py` (NEW) — von OpenSearch nativ implementiert, moderneres Design mit Pydantic BaseModel

OpenSearch implementiert das neue Interface nativ. Ein Wrapper (`OpenSearchOldDocumentIndex`) adaptiert es ins alte Interface, damit die Factory-Methoden einheitlich funktionieren. Kommentar im Code: *"TODO(andrei): This is very dumb and purely temporary until there are no more references to the old interface in the hotpath."*

### 3.2 Drei Betriebsmodi

**Modus 1: Nur Vespa (unser aktueller Stand)**
```
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX = false
→ Indexing: Nur Vespa
→ Retrieval: Nur Vespa
→ Kein OpenSearch-Client wird instanziiert
```

**Modus 2: Dual-Write (Upstream-Default seit v3.0.0)**
```
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX = true
ENABLE_OPENSEARCH_RETRIEVAL_FOR_ONYX = false (per DB-Flag umschaltbar)
→ Indexing: Vespa + OpenSearch parallel (Vespa immer zuerst, autoritativ bei Konflikten)
→ Retrieval: Vespa (umschaltbar auf OpenSearch via Admin UI)
→ Migration-Task laeuft alle 120 Sekunden (kopiert historische Chunks)
```

**Modus 3: Nur OpenSearch (Ziel fuer v4.0.0)**
```
Vespa-Code entfernt
→ Indexing: Nur OpenSearch
→ Retrieval: Nur OpenSearch
```

### 3.3 Readiness-Check-Kette

```python
# backend/onyx/background/celery/apps/app_base.py, Zeile 517
def wait_for_vespa_or_shutdown():
    if DISABLE_VECTOR_DB:
        return  # Skip alles

    if not wait_for_vespa_with_timeout():
        raise WorkerShutdown()  # Vespa MUSS erreichbar sein

    if ENABLE_OPENSEARCH_INDEXING_FOR_ONYX:
        if not wait_for_opensearch_with_timeout():
            raise WorkerShutdown()  # OpenSearch MUSS AUCH erreichbar sein!
```

**Kritisch:** Wenn `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true` und kein OpenSearch laeuft, starten weder API-Server noch Celery-Worker. Das war die Ursache unserer Crashes nach dem Upstream-Sync.

### 3.4 Env Vars Uebersicht (vollstaendig)

#### OpenSearch

| Env Var | Default (Upstream) | Unser Override | Beschreibung |
|---------|-------------------|----------------|-------------|
| **`ENABLE_OPENSEARCH_INDEXING_FOR_ONYX`** | **`"true"`** | **`"false"`** | Master-Switch: Dual-Write in OpenSearch |
| **`ENABLE_OPENSEARCH_RETRIEVAL_FOR_ONYX`** | `""` (false) | nicht gesetzt | Fallback fuer Retrieval-Umschaltung (primaer per DB-Flag) |
| **`OPENSEARCH_FOR_ONYX_ENABLED`** | `"true"` (env.template) | **`"false"`** | Docker-Compose Alias |
| `OPENSEARCH_HOST` | `"localhost"` | nicht gesetzt | Server Hostname |
| `OPENSEARCH_REST_API_PORT` | `9200` | nicht gesetzt | REST Port |
| `OPENSEARCH_ADMIN_USERNAME` | `"admin"` | nicht gesetzt | Admin-User |
| `OPENSEARCH_ADMIN_PASSWORD` | `"StrongPassword123!"` | nicht gesetzt | Admin-Passwort |
| `DEFAULT_OPENSEARCH_CLIENT_TIMEOUT_S` | `60` | nicht gesetzt | Client-Timeout |
| `DEFAULT_OPENSEARCH_QUERY_TIMEOUT_S` | `50` | nicht gesetzt | Query-Timeout |
| `USING_AWS_MANAGED_OPENSEARCH` | `""` (false) | nicht gesetzt | AWS Managed Modus |
| `OPENSEARCH_PROFILING_DISABLED` | `""` (false) | nicht gesetzt | Profiling |
| `OPENSEARCH_EXPLAIN_ENABLED` | `""` (false) | nicht gesetzt | Score-Explain (1000x langsamer!) |
| `OPENSEARCH_TEXT_ANALYZER` | `"english"` | nicht gesetzt | Text-Analyzer |
| `OPENSEARCH_MIGRATION_GET_VESPA_CHUNKS_PAGE_SIZE` | `500` | nicht gesetzt | Migration Page-Size |
| `OPENSEARCH_DEFAULT_NUM_HYBRID_SEARCH_CANDIDATES` | `0` | nicht gesetzt | Search-Tuning |
| `VERIFY_CREATE_OPENSEARCH_INDEX_ON_INIT_MT` | `"true"` | nicht gesetzt | Multitenant-Init |

#### Vespa

| Env Var | Default | Beschreibung |
|---------|---------|-------------|
| `VESPA_HOST` | `"localhost"` | Server Hostname |
| `VESPA_CONFIG_SERVER_HOST` | = VESPA_HOST | Config Server |
| `VESPA_PORT` | `"8081"` | Application Port |
| `VESPA_TENANT_PORT` | `"19071"` | Config Port |
| `NUM_RETRIES_ON_STARTUP` | `10` | Startup-Retries |
| `VESPA_REQUEST_TIMEOUT` | `15` | Request-Timeout |
| `VESPA_MIGRATION_REQUEST_TIMEOUT_S` | `120` | Migration-Timeout |
| `VESPA_SEARCHER_THREADS` | `2` | Parallele Threads |
| `VESPA_LANGUAGE_OVERRIDE` | `None` | Sprach-Override |
| `LOG_VESPA_TIMING_INFORMATION` | `""` (false) | Debug-Logs |
| `MANAGED_VESPA` | `""` (false) | Vespa Cloud Modus |

#### Uebergreifend

| Env Var | Default | Beschreibung |
|---------|---------|-------------|
| `DISABLE_VECTOR_DB` | `""` (false) | Vespa + OpenSearch komplett deaktivieren |

### 3.5 Deprecation-Signale im Code

Explizite Kommentare in `factory.py`:
- Zeile 27: *"To be used for retrieval only. Indexing should be done through both indices **until Vespa is deprecated**."*
- Zeile 100: *"Used for indexing only. **Until Vespa is deprecated** we will index into both document indices."*

Weitere Signale:
- `indexing/models.py:44`: *"TODO(andrei): This is deprecated as of the OpenSearch migration. Remove."*
- `db/models.py:1047`: *"This table can be dropped when the migration is complete for all Onyx instances."*
- Das neue Interface (`interfaces_new.py`) ersetzt langfristig das alte (`interfaces.py`)

**Aber:** Es gibt keinen konkreten Removal-Zeitplan im Code. Keine `FIXME: Remove Vespa by v4.0` Kommentare. Der Plan ist klar, der Zeitpunkt noch nicht.

### 3.6 Code-Statistik

| Metrik | OpenSearch | Vespa |
|--------|-----------|-------|
| Python-Dateien (Produktion) | ~30 | ~85 |
| Python-Dateien (Tests) | ~6 | ~25 |
| Total Python-Dateien | 46 | 128 |
| Commits (OpenSearch-bezogen) | 131 | (historisch, nicht gezaehlt) |

Vespa ist tief in die gesamte Architektur integriert (Celery-Worker, DB Models, Redis, Search Pipeline, KG Processing, Indexing Pipeline). OpenSearch ist modular und konzentriert in `document_index/opensearch/` + `opensearch_migration/`.

---

## 4. Auswirkung auf den VoeB-Fork

### 4.1 Bekannte Probleme bei Upstream-Syncs

Beim Sync #3 (161 Commits, 2026-03-17) mussten wir **3 OpenSearch-bezogene Breaking Changes** beheben:

| # | Problem | Default vorher | Default nachher | Unser Fix |
|---|---------|---------------|----------------|-----------|
| 1 | `OPENSEARCH_FOR_ONYX_ENABLED` | `false` | `true` | `values-common.yaml: "false"` |
| 2 | `auth.opensearch.enabled` | `false` | `true` | `values-common.yaml: false` + alle Env-Files |
| 3 | `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX` | existierte nicht | `true` (NEU) | `values-common.yaml: "false"` |

**Ohne diese Fixes:** API-Server crasht mit `ConnectionError localhost:9200`, Celery-Worker crashen mit OpenSearch Readiness Probe Timeout. Alle Pods in CrashLoopBackOff.

### 4.2 Unsere aktuellen Overrides (vollstaendig)

6 Overrides um OpenSearch komplett zu deaktivieren:

**`values-common.yaml` (alle Environments):**
```yaml
# Zeile 81
opensearch:
  enabled: false

# Zeile 88-89
auth:
  opensearch:
    enabled: false

# Zeile 212-215
configMap:
  OPENSEARCH_FOR_ONYX_ENABLED: "false"
  ENABLE_OPENSEARCH_INDEXING_FOR_ONYX: "false"
```

**`values-{dev,test,prod}.yaml` (redundant aber explizit):**
```yaml
auth:
  opensearch:
    enabled: false
```

### 4.3 Risikobewertung

| Szenario | Wahrscheinlichkeit | Impact | Zeitrahmen | Unsere Reaktion |
|----------|-------------------|--------|-----------|----------------|
| **Vespa-Code wird in v4.0.0 entfernt** | **Sehr hoch** (offizielle Ankuendigung) | **Hoch** — Sync nicht mehr moeglich ohne Migration | Q2-Q3 2026 (geschaetzt) | **Migration planen** |
| Vespa bleibt in v3.x voll funktional | **Sehr hoch** | Kein Impact | Jetzt | Weiterarbeiten wie bisher |
| Neue OpenSearch-Flags mit Default `true` bei jedem Sync | **Hoch** | Mittel — 5 Min Fix pro Sync | Laufend | `configmap.yaml` + `app_configs.py` pruefen |
| Neue Features nur fuer OpenSearch | **Mittel** | Mittel — Features die wir evtl. brauchen | Laufend | Feature-by-Feature bewerten |
| Vespa-Code wird nicht mehr getestet upstream | **Mittel-Hoch** | Mittel — Subtile Bugs moeglich | Schleichend | Eigene Tests fuer Vespa-Pfad |
| OpenSearch wird Pflicht (kein Opt-Out) | **Niedrig** in v3.x, **Hoch** in v4.x | Hoch | v4.0.0 | s.o. Migration |
| `configmap.yaml` Template-Logik aendert sich | **Mittel** | Mittel — Overrides greifen evtl. nicht mehr | Bei Sync | Template-Diff pruefen |

### 4.4 Aufwand bei Wechsel zu OpenSearch

#### Ressourcen-Vergleich

| Ressource | Vespa (Upstream-Default) | Vespa (unser PROD) | OpenSearch (Upstream-Default) | OpenSearch (geschaetzt fuer uns) |
|-----------|------------------------|--------------------|------------------------------|--------------------------------|
| CPU Request | 4000m | 2000m | 2000m | 500-1000m |
| CPU Limit | 8000m | 4000m | 4000m | 2000m |
| RAM Request | 8000Mi | 4Gi | 4Gi | 2-4Gi |
| RAM Limit | 32000Mi | 8Gi | 8Gi | 4-8Gi |
| JVM Heap | N/A | N/A | 4g | 2g |
| Storage PVC | 30Gi | 50Gi | 30Gi | 20-30Gi |
| Replicas | 1 | 1 | 1 | 1 |
| AVX2 Pflicht | **JA** | JA (StackIT hat es) | **NEIN** | NEIN |
| privileged | true (Default) | false (override) | Nein | Nein |

**Onyx-eigener Benchmark (v2.11.0):**
| Komponente | RAM |
|------------|-----|
| Vespa (Quelle) | 128 GB |
| OpenSearch (Ziel) | **8 GB** |
| Faktor | **16x weniger** |

**Fuer unsere Nodes (g1a.4d: 4 vCPU, 16 GB RAM pro Node):**
- OpenSearch mit 2Gi Request / 4Gi Limit passt problemlos
- Wahrscheinlich sogar ressourcenschonender als Vespa
- Dual-Mode (Migration) auf DEV/TEST moeglich wenn Vespa und OpenSearch-Requests gesenkt werden

#### Migrations-Aufwand

| Schritt | Aufwand | Beschreibung |
|---------|---------|-------------|
| 1. Helm Values anpassen | 30 Min | `opensearch.enabled: true`, Auth-Secret konfigurieren, OpenSearch-Env-Vars setzen |
| 2. OpenSearch-Pod deployen | 15 Min | `helm upgrade`, Pod startet, Readiness-Check OK |
| 3. Dual-Write aktivieren | 5 Min | `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX: "true"` |
| 4. Migration starten | 5 Min | Ueber Admin UI oder API |
| 5. Migration laufen lassen | Stunden-Tage | Abhaengig von Dokumentenanzahl (~200k Chunks/h) |
| 6. Retrieval umschalten | 5 Min | Admin UI: Toggle Retrieval auf OpenSearch |
| 7. Vespa deaktivieren | 15 Min | `vespa.enabled: false` in Helm Values |
| 8. Monitoring anpassen | 1-2h | Neue Health Checks, Alerts, Grafana Dashboards |
| **Gesamt** | **~0.5-1 PT** | Plus Wartezeit fuer Migration (automatisch) |

#### Kosten-Impact

| Posten | Vespa (aktuell) | OpenSearch (geschaetzt) | Delta |
|--------|----------------|------------------------|-------|
| CPU (PROD) | 2000m Request | 500-1000m Request | **-50% bis -75%** |
| RAM (PROD) | 4Gi Request | 2-4Gi Request | **0% bis -50%** |
| Storage (PROD) | 50Gi PVC | 20-30Gi PVC | **-40% bis -60%** |
| Kosten/Monat | Im Node-Preis | Im Node-Preis | **Neutral bis guenstiger** |

---

## 5. Empfehlung

### Option A: Bei Vespa bleiben (kurzfristig empfohlen)

| Pro | Contra |
|-----|--------|
| Kein Migrationsaufwand jetzt | Zunehmende Reibung bei jedem Sync |
| Funktioniert stabil, getestet | Vespa wird in v4.0.0 entfernt |
| Bekannte Ressourcen-Anforderungen | Evtl. neue Features nur fuer OpenSearch |
| Unsere Overrides greifen zuverlaessig | "Schwimmen gegen den Strom" |

### Option B: Zu OpenSearch wechseln (mittelfristig empfohlen)

| Pro | Contra |
|-----|--------|
| Aligned mit Upstream-Richtung | ~0.5-1 PT Migrationsaufwand |
| Keine Sync-Probleme mehr | Neue Komponente in der Infrastruktur |
| Weniger Ressourcen als Vespa | Monitoring muss angepasst werden |
| Kein AVX2-Requirement | Neues Wissen noetig (OpenSearch vs. Vespa) |
| Langfristig unvermeidlich | Risiko bei Migration (Datenverlust) |

### Option C: Abwarten und beobachten (nicht empfohlen)

| Pro | Contra |
|-----|--------|
| Kein sofortiger Aufwand | Wechsel wird spaeter teurer und dringender |
| - | v4.0.0 koennte ueberraschend kommen |
| - | Kein kontrollierter Uebergang moeglich |

### **Empfehlung: A jetzt, B planen**

1. **Jetzt (Q1 2026):** Bei Vespa bleiben. Die 6 Overrides funktionieren zuverlaessig, jeder Sync braucht ~5 Min fuer OpenSearch-Checks. Kein akuter Handlungsbedarf.

2. **Planen (Q2 2026):** OpenSearch-Migration als eigenes Arbeitspaket einplanen, BEVOR v4.0.0 erscheint. Idealer Zeitpunkt: Nach M1-Abnahme und Entra ID Integration, wenn die Infrastruktur stabil ist.

3. **Ausfuehren (Q2-Q3 2026):** Migration durchfuehren:
   - Zuerst auf DEV testen (OpenSearch aktivieren, Dual-Write, Migration, Switch)
   - Dann TEST, dann PROD
   - Geschaetzter Aufwand: 1-2 PT gesamt (inkl. Monitoring-Anpassung)

4. **Monitoring:** Bei jedem Upstream-Sync die Checkliste (Abschnitt 6) abarbeiten. Wenn v4.0.0-beta erscheint, Migration priorisieren.

**Begruendung:** Die Migration ist unvermeidlich — die Frage ist nur wann. Jetzt migrieren waere premature optimization (wir haben wichtigere Themen: Entra ID, M1-Abnahme, NetworkPolicies). Zu lange warten riskiert einen erzwungenen Wechsel unter Zeitdruck. Q2 2026 ist der Sweet Spot.

---

## 6. Checkliste fuer jeden Upstream-Sync

### Vor dem Merge

| # | Pruefung | Datei | Aktion |
|---|----------|-------|--------|
| 1 | `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX` Default | `backend/onyx/configs/app_configs.py:299-300` | Muss in values-common.yaml auf `"false"` stehen |
| 2 | Neue OpenSearch env vars mit Default `true` | `backend/onyx/configs/app_configs.py` (grep "OPENSEARCH") | Neue Overrides in values-common.yaml hinzufuegen |
| 3 | `opensearch.enabled` Default im Chart | `deployment/helm/charts/onyx/values.yaml` | Muss in values-common.yaml auf `false` stehen |
| 4 | `auth.opensearch.enabled` Default im Chart | `deployment/helm/charts/onyx/values.yaml` | Muss in values-common.yaml + allen Env-Files auf `false` stehen |
| 5 | ConfigMap Template-Logik | `deployment/helm/charts/onyx/templates/configmap.yaml:15-20` | Pruefen ob `{{- if .Values.opensearch.enabled }}` Block noch korrekt |
| 6 | Auth-Secrets Template-Logik | `deployment/helm/charts/onyx/templates/auth-secrets.yaml:9-12` | Pruefen ob Validierung bei `opensearch.enabled: false` nicht greift |
| 7 | Neue OpenSearch Readiness Probes | `backend/onyx/background/celery/apps/app_base.py` | Pruefen ob neue Probes an `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX` gebunden sind |
| 8 | Neue Celery-Queues fuer OpenSearch | `deployment/helm/charts/onyx/templates/celery-worker-*.yaml` | Harmlos wenn Tasks intern `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX` pruefen |
| 9 | OpenSearch Subchart Version | `deployment/helm/charts/onyx/Chart.yaml` | `helm dependency update` braucht evtl. neue Repo-Version |
| 10 | `env.template` OpenSearch-Defaults | `deployment/docker_compose/env.template` | Unser Append-Block bleibt am Ende, aber pruefen ob neue Defaults dazukommen |

### Quick-Grep nach dem Merge

```bash
# Alle neuen OpenSearch-bezogenen Aenderungen finden
git diff HEAD~1 --name-only | xargs grep -l "opensearch\|OPENSEARCH" 2>/dev/null

# Neue env vars mit Default true
grep -n "ENABLE_OPENSEARCH\|OPENSEARCH.*true\|opensearch.*enabled" \
  backend/onyx/configs/app_configs.py \
  deployment/helm/charts/onyx/values.yaml \
  deployment/helm/charts/onyx/templates/configmap.yaml
```

---

## 7. Quellen

### Offizielle Onyx-Quellen
- [Onyx Changelog / Release Notes](https://docs.onyx.app/changelog) — v2.8.0, v2.11.0, v2.12.0, v3.0.0
- [Onyx GitHub Releases](https://github.com/onyx-dot-app/onyx/releases) — v3.0.0 bis v3.0.3
- [Onyx GitHub Repository](https://github.com/onyx-dot-app/onyx)
- [Onyx FOSS Repository](https://github.com/onyx-dot-app/onyx-foss)
- [Onyx Resourcing Docs](https://docs.onyx.app/deployment/getting_started/resourcing)
- [Onyx Configuration Docs](https://docs.onyx.app/deployment/configuration/configuration)

### Vespa-Blog (historisch)
- [Why Danswer uses Vespa (Sep 2024)](https://blog.vespa.ai/why-danswer-users-vespa/)
- [Onyx cost optimization on Vespa Cloud (Sep 2025)](https://blog.vespa.ai/using-vespa-cloud-resource-suggestions-to-optimize-costs/)

### GitHub Issues (Vespa-Probleme)
- [#697: Vespa AVX2 Requirement](https://github.com/onyx-dot-app/onyx/issues/697)
- [#3209: Vespa illegal instruction](https://github.com/onyx-dot-app/onyx/issues/3209)
- [#3427: High memory consumption](https://github.com/onyx-dot-app/onyx/issues/3427)
- [#1165: Alternative Vector DBs](https://github.com/onyx-dot-app/onyx/issues/1165)

### OpenSearch-Ressourcen
- [OpenSearch Docs: Docker](https://docs.opensearch.org/latest/install-and-configure/install-opensearch/docker/)
- [OpenSearch Forum: Resource Requirements](https://forum.opensearch.org/t/opensearch-resource-requirements/15708)
- [OpenSearch Helm Chart (Official)](https://github.com/opensearch-project/helm-charts/blob/main/charts/opensearch/values.yaml)
- [Opster: OpenSearch Memory Usage Guide](https://opster.com/guides/opensearch/opensearch-capacity-planning/memory-usage/)

### Vergleiche
- [Zilliz: OpenSearch vs Vespa](https://zilliz.com/comparison/opensearch-vs-vespa)
- [MyScale: Vespa vs OpenSearch](https://www.myscale.com/blog/vespa-vs-opensearch-battle-search-engine-titans/)

### Community
- [Hacker News: Onyx Launch](https://news.ycombinator.com/item?id=46045987)
- [TechCrunch: Why Onyx thinks open source will win](https://techcrunch.com/2025/03/12/why-onyx-thinks-its-open-source-solution-will-win-enterprise-search/)

### Lokale Codebase (Schluessel-Dateien)
- `backend/onyx/document_index/factory.py` — Factory mit Dual-Mode-Logik, Deprecation-Kommentare
- `backend/onyx/document_index/interfaces.py` — OLD Interface (Vespa)
- `backend/onyx/document_index/interfaces_new.py` — NEW Interface (OpenSearch)
- `backend/onyx/configs/app_configs.py:250-337` — Alle OpenSearch/Vespa Env Vars
- `backend/onyx/background/celery/apps/app_base.py:517-538` — Readiness Probes
- `backend/onyx/background/celery/tasks/beat_schedule.py:216-230` — Migration-Task Scheduling
- `deployment/helm/charts/onyx/values.yaml` — Upstream-Defaults
- `deployment/helm/charts/onyx/templates/configmap.yaml:15-20` — OpenSearch ConfigMap-Logik
- `deployment/helm/charts/onyx/templates/auth-secrets.yaml:9-12` — Auth-Validierung
- `deployment/helm/values/values-common.yaml:78-89, 209-215` — Unsere OpenSearch-Deaktivierung
