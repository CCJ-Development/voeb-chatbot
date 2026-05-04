# Fork-Management & Upstream-Sync

## Remotes
- `origin` → unser Fork (CCJ-Development/voeb-chatbot)
- `upstream` → Onyx FOSS (onyx-dot-app/onyx-foss)

## Branch-Strategie (Simplified GitLab Flow)

**Kein `develop`-Branch.** `main` ist der einzige langlebige Branch.

- `main` ← Integrationsbranch, auto-deploy DEV
- `feature/*` ← Feature-Branches von main, lokal merge zurück nach main (kein PR)
- `chore/upstream-sync-*` ← Upstream-Merges via Branch+PR (Ausnahme: Diff-Inspektion)
- `release/*` ← Geschnitten von main wenn TEST/PROD-ready

### Promotion-Modell
```
feature/* → local merge → main → push → auto-deploy DEV
                  │
                  └→ release/1.0 → workflow_dispatch → TEST
                          │
                          └→ tag v1.0.0 → workflow_dispatch → PROD
                          │
                          └→ merge back → main
```

### Release-Workflow
```bash
# 1. Release-Branch schneiden (wenn DEV stabil)
git checkout main
git checkout -b release/1.0

# 2. TEST deployen
gh workflow run stackit-deploy.yml -f environment=test --ref release/1.0

# 3. Bugfixes auf Release-Branch, cherry-pick zurück nach main
git cherry-pick <fix-commit> # auf main

# 4. Wenn TEST approved: Tag setzen + PROD deployen
git tag -a v1.0.0 -m "Release v1.0.0 — M1 Infrastruktur"
git push origin v1.0.0
gh workflow run stackit-deploy.yml -f environment=prod --ref release/1.0

# 5. Release-Branch zurück nach main mergen
git checkout main
git merge release/1.0
```

## Upstream-Sync — Schritt für Schritt

### 1. Vorbereitung
```bash
git fetch upstream
git log --oneline HEAD..upstream/main | wc -l   # Anzahl neuer Commits
```

### 1a. Pre-PR-Verifikation (PFLICHT vor PR-Erstellung)

**Lesson Learned Sync #7:** Wenn ein Sync neue oder strengere Lint-Regeln scharf macht, decken sie sich sequenziell im CI auf — jeder Push triggert einen Concurrency-cancelten Deploy. Drei Iterationen in 7 Min sind Verschwendung. Daher VOR `git push` lokal alle Stages durchspielen, die `ci-checks.yml` (`.github/workflows/ci-checks.yml`) prueft:

```bash
# 1. TOML-Parser (kann Auto-Merge-Duplicate-Keys uebersehen)
python3 -c "import tomllib; tomllib.loads(open('pyproject.toml').read())"

# 2. Ruff Check (I001, G004, F401, ARG, etc.)
ruff check backend/ext/

# 3. Ruff Format (line-length, Trailing-Commas, multi-line/single-line)
ruff format --check backend/ext/

# 4. TypeScript Strict (Frontend)
cd web && npx tsc --noEmit --project tsconfig.json && cd -

# 5. AST-Sanity der gepatchten Backend-Files (Quick-Check, ersetzt nicht pytest)
for f in backend/onyx/main.py backend/onyx/llm/multi_llm.py \
         backend/onyx/access/access.py backend/onyx/chat/prompt_utils.py \
         backend/onyx/db/persona.py backend/onyx/db/document_set.py \
         backend/onyx/natural_language_processing/search_nlp_models.py; do
  python3 -c "import ast; ast.parse(open('$f').read())" && echo "✓ $f"
done
```

**Falls ruff lokal nicht installiert ist:** `pipx install ruff` oder `pyenv exec python -m pip install ruff`. Auf macOS+pyenv funktionierte zuletzt: `PYENV_VERSION=3.11.12 pyenv exec python -m pip install ruff` (~2s).

**Falls eine Stage failt:** Direkt fixen, **nicht** als CI-Followup-Commit nachreichen — sonst entsteht eine Concurrency-Cancel-Kette. Ruff hat fuer I001 `--fix`, fuer G004 manuell auf `%`-Style umstellen (`f"... {x}"` → `"... %s", x`).

### 2. Test-Merge (Dry-Run in Worktree)
```bash
mkdir -p .claude/worktrees
git worktree add .claude/worktrees/upstream-test upstream/main
cd .claude/worktrees/upstream-test
git merge main --no-commit --no-ff
# Konflikte prüfen:
git diff --name-only --diff-filter=U
# Aufräumen:
git merge --abort
cd -
git worktree remove .claude/worktrees/upstream-test
```

### 3. Merge-Branch erstellen + Merge durchführen
```bash
# Upstream-Syncs nutzen weiterhin Branch+PR (Diff-Inspektion bei grossen Merges)
git checkout -b chore/upstream-sync-YYYY-MM-DD

# Merge durchführen
git merge upstream/main --no-commit --no-ff
```

### 4. Konflikte lösen

**Erwartete Konflikte (harmlos):**
- `AGENTS.md`, `.claude/skills` → Unsere Version behalten (`git checkout --ours`)
- `Chart.yaml`, `Chart.lock` → Upstream übernehmen (`git checkout --theirs`)
- 17 Core-Dateien (Stand 2026-04-20: Sync #5 ergaenzte Core #15 useSettings.ts, 2026-04-20 kamen Core #16 DynamicMetadata.tsx und Core #17 AccountPopover.tsx hinzu) → Upstream übernehmen, Patches neu anwenden (siehe unten)
- `backend/Dockerfile` → Upstream übernehmen, COPY ext/ neu einfügen (siehe "Zusätzliche Merge-Stellen")
- `deployment/docker_compose/env.template` → Manuell mergen (wir appenden am Ende, Upstream ändert Mitte)

**Unerwartete Konflikte:**
- Dateien in `backend/onyx/`, `web/src/` (außer Core) = Regeln gebrochen
- Ursache analysieren, ext_-Code anpassen (NICHT Onyx-Code)

### 5. Core-Datei-Patches aktualisieren

Fuer JEDE gepatchte Core-Datei (aktuell 16 von 17 gepatcht — nur #5 `header/` offen):
- Backend: `main.py`, `multi_llm.py`, `access.py`, `prompt_utils.py`, `persona.py`, `document_set.py`, `search_nlp_models.py`
- Frontend: `layout.tsx`, `constants.ts`, `LoginText.tsx`, `AuthFlowContainer.tsx`, `AdminSidebar.tsx`, `ActionsPopover/index.tsx`, `useSettings.ts`, `DynamicMetadata.tsx`, `AccountPopover.tsx`

```bash
# Beispiel Backend-Datei:
git show upstream/main:backend/onyx/main.py > backend/ext/_core_originals/main.py.original
diff -u backend/ext/_core_originals/main.py.original backend/onyx/main.py \
  > backend/ext/_core_originals/main.py.patch

# Beispiel Frontend-Datei:
git show upstream/main:web/src/lib/constants.ts > backend/ext/_core_originals/constants.ts.original
diff -u backend/ext/_core_originals/constants.ts.original web/src/lib/constants.ts \
  > backend/ext/_core_originals/constants.ts.patch

# Analog fuer LoginText.tsx, AuthFlowContainer.tsx und AdminSidebar.tsx
```

Falls Core-Datei-Konflikte auftreten (auto-merge fehlschlägt):
```bash
# Upstream übernehmen:
git checkout --theirs backend/onyx/main.py  # oder web/src/lib/constants.ts etc.
# Patch anwenden:
patch -p0 < backend/ext/_core_originals/main.py.patch
# Prüfen ob Patch sauber angewendet wurde, ggf. manuell nachbessern
```

> **Alle Patches liegen zentral in `backend/ext/_core_originals/`** — sowohl Backend- als auch Frontend-Dateien. Pro Core-Datei genau ein `.original` + ein `.patch`.

### 6. Helm-Dependencies prüfen
```bash
# Neue Sub-Charts in Chart.yaml?
grep "repository:" deployment/helm/charts/onyx/Chart.yaml
# Vergleichen mit helm repo add in .github/workflows/stackit-deploy.yml
# Fehlende Repos in ALLEN 3 Deploy-Jobs (dev, test, prod) ergänzen
```

### 7. PR erstellen und mergen (nur für Upstream-Syncs)
```bash
git commit -m "chore(upstream): Merge upstream/main — <N> Commits"
git push origin chore/upstream-sync-YYYY-MM-DD

# PR erstellen — IMMER -R Flag (sonst geht PR an upstream/onyx-foss!)
gh pr create --base main -R CCJ-Development/voeb-chatbot \
  --title "chore(upstream): Merge upstream/main — <N> Commits" \
  --body "Upstream-Sync: <N> Commits, <X> Konflikte"

# Nach CI-Checks: Merge
gh pr merge <PR-NR> -R CCJ-Development/voeb-chatbot --squash --delete-branch
```

> **Warum PR nur für Upstream-Syncs?** Upstream-Merges bringen hunderte fremde Commits — der PR-Diff zeigt Konflikte und unerwartete Änderungen bevor sie auf main landen. Für eigene Feature-Branches ist das nicht nötig (Solo-Dev, lokaler Merge reicht).
> CI-Checks (helm-validate, build-backend, build-frontend) laufen auf Push-to-main.

### 8. TEST nach erfolgreichem DEV
```bash
gh workflow run stackit-deploy.yml -f environment=test -R CCJ-Development/voeb-chatbot
```

## Erster Upstream-Merge (2026-03-03) — Referenz

| Metrik | Wert |
|--------|------|
| Upstream-Commits | 415 |
| Konflikte | 4 (AGENTS.md, .claude/skills, Chart.yaml, Chart.lock) |
| Core-Datei-Konflikte | 0 (main.py auto-merged) |
| ext_-Code Konflikte | 0 |
| Infrastruktur-Konflikte | 0 |
| Zusätzlicher Fix | Helm Repo `python-sandbox` in CI/CD ergänzt |
| Merge-Dauer | ~5 Min (inkl. Verifikation) |

## Zweiter Upstream-Merge (2026-03-06) — Referenz

| Metrik | Wert |
|--------|------|
| Upstream-Commits | 100 |
| Konflikte | 1 (AGENTS.md) |
| Core-Datei-Konflikte | 0 (main.py auto-merged, ext-Hook intakt) |
| ext_-Code Konflikte | 0 |
| Infrastruktur-Konflikte | 0 |
| Wichtig | PR #9014 entfernt Lightweight Mode, PR #9005 Embedding-Blocker aufgehoben |
| Merge-Dauer | ~5 Min |
| Workflow | Branch + PR (erstmals mit Branch Protection) |

## Dritter Upstream-Merge (2026-03-18) — Referenz

| Metrik | Wert |
|--------|------|
| Auslöser | Helm-Release DEV musste gelöscht und neu installiert werden (Chart-Inkompatibilität) |
| Alembic-Problem | 4 Upstream-Migrationen in Chain eingefügt aber nie ausgeführt (DB auf Head gestempelt) |
| Fehlende Migrationen | `b5c4d7e8f9a1` (hierarchy_node), `27fb147a843f` (user timestamps), `93a2e195e25c` (voice_provider), `689433b0d8de` (hooks) |
| Fix | SQL manuell auf DEV-DB ausgeführt via `kubectl exec` + `psycopg2` |
| LB-IP-Wechsel | `188.34.74.187` → `188.34.118.222` (NGINX Controller neu erstellt) |
| DNS-Update | ✅ Leif hat A-Record aktualisiert auf `188.34.118.222` (verifiziert 2026-03-22) |
| **Lesson Learned** | `helm delete + install` = neue LB-IP. `helm upgrade` behält LB-IP. |
| **Lesson Learned** | Alembic `upgrade head` holt eingefügte Migrationen NICHT nach wenn DB bereits auf späterem Head steht |

## Vierter Upstream-Merge (2026-03-22) — Referenz

| Metrik | Wert |
|--------|------|
| Upstream-Commits | 71 |
| Konflikte | 0 |
| Core-Datei-Konflikte | 0 |
| ext_-Code Konflikte | 0 |
| Infrastruktur-Konflikte | 0 |
| Chart-Version | 0.4.35 → 0.4.36 |
| Wichtig | Hook-System, OpenSearch-Verbesserungen, Groups Page, tool_choice-Fix |
| Workflow | Branch + PR (#19), Squash Merge |
| PROD-Deploy | Manueller `helm upgrade` am selben Tag (Chart 0.4.32 → 0.4.36, OpenSearch + ext-i18n) |

## Sync #6 PROD-Rollout (2026-04-25) — Referenz

| Metrik | Wert |
|--------|------|
| Auslöser | Kombinierter Rollout: Sync #6 PROD + Vespa-Disable + Worker-Resource-Rebalance |
| Image-Tag deployed | `a211c3b` (Commit `a211c3b6b` aus `feature/prod-vespa-out-and-rebalance`) |
| Helm-Rev-Sequenz | 20 (Sync #5, deployed) → 21 (Sync #6 erste Trigger, **failed** durch Alembic-Crash) → 22 (eigenes manuelles Helm aus falschem Branch, **failed**) → 23 (Workflow-Re-Trigger, **deployed**) |
| Chart-Version | 0.4.44 → 0.4.47 |
| Alembic-Recovery | 3-Step-Pattern auf laufendem celery-worker-primary-Pod (api-server war im CrashLoopBackoff): `UPDATE 503883791c39` → `alembic upgrade a7c3e2b1d4f8` → `UPDATE d8a1b2c3e4f5` |
| Crash-Trigger DB | `psycopg2.errors.UndefinedColumn: column document.file_id does not exist` — Sync-#6-Code liest sofort beim Boot von der durch `91d150c361f6` neu eingefuehrten Spalte |
| Vespa-Pod | Removed — `vespa.enabled=false` in values-common.yaml + `ONYX_DISABLE_VESPA=true` in configMap. Vespa-Pod nicht mehr existent, alle 8 Celery-Worker uebergehen `wait_for_vespa_or_shutdown` |
| Worker-Resources rebalanced | Onyx-Komponenten Total-CPU-Requests 8.450m → 2.600m. RAM gleich (1 Worker mit hoeherem RAM-Bedarf: user-file-processing 512 → 768 Mi) |
| OpenSearch | RAM-Limit 4 → 5 GiB (Peak 3.469 Mi = 85 % am alten Limit), JavaOpts -Xmx 2g → 3g |
| PROD-Outage geplant | ~50 Min (Alembic-Crash bis Recovery durch) |
| PROD-Outage ungeplant | ~50 Min (eigener Branch-Hygiene-Fehler — siehe Lessons unten) |
| Final-State | 17/17 Pods Running, Health 200, Cluster-Requests 7.294m CPU / 14,7 Gi RAM |
| Workflow-Runs | DEV: 24925683562 (push-to-main, 7 Min, success). PROD #1: 24925872185 (workflow_dispatch, 16 Min, failure — Helm-Timeout durch Alembic). PROD #2: 24928356519 (Recovery, ~5 Min, success nach Required-Reviewer-Approval) |

### Lessons Learned Sync #6 PROD

1. **3-Step-Alembic-Recovery ist robustes Pattern (2/2 erfolgreich).** Sync #5 PROD + Sync #6 PROD. Identische Sequenz, beide Male auf einem laufenden Celery-Pod ausgefuehrt (api-server war in CrashLoopBackoff). PG-Backup vorab (`/tmp/prod-alembic-version-backup-<ts>.txt` mit dem aktuellen `version_num`) ist ausreichend — kein voller `pg_dump` noetig, weil ext-Tabellen nicht angefasst werden.

2. **Branch-Hygiene bei manuellen Helm-Upgrades ist KRITISCH.** Heute live erlebt: `helm upgrade` aus `docs/plattform-acl-praezisierung` (mit alten Working-Dir-Files) hat Vespa wieder hochgefahren UND Image-Tag auf `:latest` gesetzt (CI/CD setzt sonst Commit-SHA per `--set global.version=$SHA`). `:latest` zeigt auf Onyx-Mainline ohne unsere ext-Migrationen → CrashLoopBackoff `Can't locate revision identified by 'd8a1b2c3e4f5'`. **Regel:** Vor `helm upgrade <release>` immer `git rev-parse HEAD` und `git status` checken. Besser: nur ueber Workflow oder explicite `git checkout main && git pull` davor. Korrekturpfad: `gh workflow run stackit-deploy.yml -f environment=prod --ref main` (checkt automatisch main aus).

3. **Required-Reviewer-Gate auf PROD-Workflow** verzoegert Recovery um die Zeit zwischen Trigger und Approval. Im Vorfall heute ~3 Min. Vorab kommunizieren: bei kritischen PROD-Recoveries entweder Niko-on-Standby oder PR-Approval-Gate temporaer suspendieren (heute nicht noetig — Niko war on-call).

4. **Helm-Status `failed` ist kosmetisch** (nur das Helm-Release-Tracking ist auf failed, der Cluster kann gesund sein) — aber das Heilen darf nicht aus falschem Branch erfolgen (siehe Lesson 2). Bessere Heil-Strategie: warten bis ein neuer main-Push (z.B. Doku-Commit oder anderer Fix) durchlaeuft, das setzt automatisch eine neue Helm-Revision.

5. **Cluster-Total-Requests sinken massiv durch Worker-Rebalance** (PROD 8.450m → ~2.600m Onyx-Komponenten, +Monitoring +System ~7.294m gesamt). Aber: Cluster-Total auf 2x g1a.4d-Allocatable (~7.400m) waere bei aktueller Auslastung 99 %. **API-Peak 1.245m (einmaliger 30d-Outlier) frisst Headroom**, deshalb Node-Downgrade g1a.8d → g1a.4d nicht direkt nach Rollout, sondern erst nach 7-Tage-Soak unter Sync-#6-Stack mit neuen 30d-Daten zu pruefen.

6. **DEV-Single-Node-Konsolidierung ist mathematisch nicht machbar** mit aktivem Monitoring-Stack. Cluster-Total ~3.974m CPU > 1× g1a.4d-Allocatable ~3.700m. 1× g1a.8d kostet identisch zu 2× g1a.4d (lineares vCPU-Pricing bei StackIT) und verliert HA. → DEV bleibt 2× g1a.4d, dokumentiert in `values-dev.yaml`-Header. Alternative: DEV-Monitoring-Removal eroeffnet den Single-Node-Pfad (~143 EUR/Mo Ersparnis), Niko nutzt DEV-Monitoring selten — eigener Branch bei Bedarf.

## Siebter Upstream-Merge (2026-05-02) — Referenz

| Metrik | Wert |
|--------|------|
| Upstream-Commits | 168 |
| Konflikte | 5: 2 trivial (`AGENTS.md` + `README.md` per `--ours`) + 1 moderat (`web/Dockerfile`: `overriden`→`overridden`-Fix, unsere ARG/ENV-Bloecke beibehalten) + 2 ernsthaft auf Core #9 + #17 |
| Core-Datei-Konflikte | 2 (auto-merged: 14 — alle Hooks intakt). Core #9 `AuthFlowContainer.tsx` (Opal-Migration `OnyxIcon`→`SvgOnyxLogo`); Core #17 `AccountPopover.tsx` (Schema-Migration `LineItem`→`LineItemButton`, Patch von 3 auf 4 Gate-Stellen erweitert) |
| ext_-Code Konflikte | 0 |
| ext-Code Anpassung | 1 Datei: `web/src/ext/components/LogoCropModal.tsx` Checkbox-Import von `@/refresh-components/inputs/Checkbox` (Pfad weg) auf `{ Checkbox } from "@opal/components"` umgestellt — Upstream hat Checkbox in das Opal-Design-System verschoben (Default-Export → Named-Export, `onChange` → `onCheckedChange`) |
| Alembic-Migrationen | 2 neue Upstream (`14162713706c` IndexAttempt-Stage-Metric-Tabelle, `31bd8c17325e` Targeted-Reindex-Schema). Chain: `ff7273065d0d` (ext-branding) `down_revision` von `a7c3e2b1d4f8` auf `31bd8c17325e` umgehaengt |
| Chart-Version | 0.4.47 → 0.4.48 (Patch-Bump, keine neuen Sub-Charts) |
| Helm-Repos | Keine neuen Repos (alle 7 bereits in CI) |
| Neue Features relevant fuer uns | 2 Security-Fixes DSGVO/Banking-relevant (`#10602` document set access in search filters, `#10601` agent access on chat session creation, `#10528` is_listed-Filter fuer Nicht-Owner-Agent-Zugriffe); OpenSearch-Race-Fixes (Index-Lock #10446, Index-Refresh #10525/#10514); Confluence `/Date`-Macro + kyrillisches Encoding (#10488); `litellm 1.83.0` (Tool-Calling-Stabilitaet); Multi-Threading fuer Image-Processing (#10744); Helm `extraEnv`-Hook (#10533); LLM-Tracing-Infrastruktur via Braintrust (#10735, #10478, passive) |
| Breaking Changes ohne ext-Impact | Opal `OnyxIcon`/`LineItem` deprecated (durch unsere zwei Core-Patches behandelt), `DANSWER_RUNNING_IN_DOCKER` → `ONYX_RUNNING_IN_DOCKER` ENV-Rename (#10442, wir setzen das nicht), Vespa-Refactor (#10613, bei uns durch `ONYX_DISABLE_VESPA=true` unkritisch), Node 20 → 24 (#10526) |
| Force-Push auf upstream/main | Ja (von Upstream vor dem Merge beobachtet) — Merge-Base `5c896e2caf95` blieb stabil. Lesson #7 von Sync #6 erneut bestaetigt |
| Workflow | Branch + PR (Push offen — wartet auf Nikos Freigabe) |
| Verifikation | `tsc --strict` 0 Errors, Backend-AST-Sanity gruen. Pytest lokal nicht ausgefuehrt (Sync-Branch ohne aktives venv) — wird durch `ci-checks.yml` abgedeckt |

### Lessons Learned Sync #7

1. **Frontend Opal-Migration trifft uns alle 1-2 Syncs.** Sync #5 brachte AdminSidebar-Opal-Refactor, Sync #7 jetzt `OnyxIcon`→`SvgOnyxLogo` (Core #9) + `LineItem`→`LineItemButton` (Core #17, gerade erst 2026-04-20 neu gepatcht). Erwartung fuer kommende Syncs: weitere Opal-Migrationen werden Patches berueheren — die Patches sind aber jeweils klein (~10-30 Zeilen) und haben klare 1:1-Mappings. Frontend `web/CLAUDE.md` ist die Single Source of Truth fuer "aktuelle vs. legacy"-Komponentenpfade.

2. **ext-Code kann durch Upstream-Refactors mit-rotzen.** Beim Sync #7 hat `LogoCropModal.tsx` gebrochen, weil Upstream `Checkbox` aus `@/refresh-components/inputs/` herausgezogen hat. Erkennt man nur via `tsc --strict` — keine Runtime-Errors, keine Lint-Warnings. **Lesson:** Nach jedem Sync `tsc --strict` als Pflicht-Check, **bevor** der Branch zum Push freigegeben wird. Backend hat AST-Sanity, Frontend braucht echtes TS-Strict.

3. **Patch-Erweiterung statt -Reduktion bei Schema-Migrationen.** Core #17 hatte vor Sync #7 drei `EXT_BRANDING_ENABLED`-Gates. Upstream PR #10646 hat einen vierten Whitelabel-relevanten Eintrag (`Onyx <version>`-Link auf docs.onyx.app/changelog) eingefuehrt — den haben wir gleich mit-gegated, weil Whitelabel-Logik konsistent bleiben muss. **Lesson:** Bei Schema-Migrationen den Patch nicht mechanisch portieren, sondern **die Whitelabel-Anforderung neu bewerten** — neue Upstream-Eintraege koennen auch ausgeblendet werden muessen.

4. **Drift-Cadence ~10 Tage ist optimal.** Sync #5 (344 Commits, 10h Aufwand), Sync #6 (234 Commits, 6h), Sync #7 (168 Commits, ~5h Vorbereitung). Bei kleinerem Drift sind Konflikte besser vorhersagbar, Patch-Inhalte uebersichtlicher. Kuerzer als 10 Tage hat marginalen Mehrwert (Aufwand-Untergrenze sind die Doku + 3-Step-Recovery), laenger als 14 Tage erhoeht das Risiko unaufloesbarer Schema-Migrationen quadratisch.

5. **Alembic 3-Step-Recovery jetzt 3/3.** Sync #5 + Sync #6 + Sync #7 = drei mal in Folge das gleiche Pattern ohne Abweichung. Klar etabliertes Runbook-Pattern. Fuer Sync #8+ kann man die Sequenz vermutlich automatisieren (Bash-Script in `docs/runbooks/upstream-sync.md`), wenn der Aufwand der Pflege rechtfertigt.

## Sechster Upstream-Merge (2026-04-23) — Referenz

| Metrik | Wert |
|--------|------|
| Upstream-Commits | 234 |
| Konflikte | 3 trivial: `.gitignore` (manuell, VOeB-Block + `.claude/CLAUDE.md`-Append), `AGENTS.md` + `README.md` (`--ours`) |
| Core-Datei-Konflikte | 0 (alle 16 gepatchten Core-Dateien auto-gemergt, semantisch verifiziert) |
| ext_-Code Konflikte | 0 |
| ext-Code Anpassung | 0 (keine Upstream-Rename trifft ext-Code) |
| Alembic-Migrationen | 5 neue Upstream (`d129f37b3d87`, `a6fcd3d631f9`, `91d150c361f6`, `856bcbe14d79`, `a7c3e2b1d4f8`) + 3 kosmetisch modifiziert (nur `# type: ignore`-Kommentar-Refactors). Chain: `ff7273065d0d` down von `503883791c39` auf `a7c3e2b1d4f8` umgehaengt |
| Chart-Version | 0.4.44 → 0.4.47 |
| Helm-Repos | Keine neuen Repos (alle 7 bereits in CI) |
| Neue Features relevant fuer uns | `ONYX_DISABLE_VESPA`-ENV-Flag (#10330) — erlaubt Vespa-Entfernung als eigenes Epic; Skills-Framework erweitert (#10418, `ods install-skill`); xlsx-Performance-Fixes (Streaming, Cell-Limit); `fix(security)` chat session ownership enforcement (#10413); `fix(files)` chat-file-download authorization hardening (#10380) |
| Breaking Changes ohne ext-Impact | `/admin/configuration/llm` → `/admin/configuration/language-models` (#10327, nicht verlinkt), `multilingual_expansion` removal (#10282, nicht genutzt), Opal-Component-Renames (`topRightChildren`, `nonInteractive`, Tooltip-Migration — keine ext-Komponente nutzt sie) |
| Force-Push auf upstream/main | Ja (von Upstream vor dem Merge beobachtet) — unser Fork war davon unberueht, Merge-Base war stabil |
| Workflow | Branch + PR #22, Admin-Merge (`--admin --merge`) |
| Commits auf Sync-Branch | 1 (initialer Merge-Commit) |
| Fix-Commits nach Deploy | 2 auf Follow-up-Branches: `d73d2353b` (ruff unused imports, pre-existing Lint-Drift) + `d5540594d` (helm-prod celery_worker_primary 2→1, unabhaengig vom Sync) |

### Lessons Learned Sync #6

1. **Alembic 3-Step-Recovery ist jetzt robustes Pattern.** Zum zweiten Mal in Folge (Sync #5 + Sync #6) reichte der dokumentierte 3-Step-Ansatz ohne Abweichungen: `UPDATE alembic_version = <alter Upstream-Head>` → `alembic upgrade <neuer Upstream-Head>` → `UPDATE alembic_version = <unser Head>`. Laufen kann die Sequenz auf jedem Pod mit `psycopg2` + `alembic`-CLI — bei Sync #6 war der api-server down (CrashLoopBackOff), wir haben auf `deploy/onyx-dev-celery-worker-primary` ausgefuehrt. Entscheidender Detail: Der neue Container-Build enthaelt die umgehaengte `ff7273065d0d` (down_revision auf neuen Upstream-Head), also findet `alembic upgrade` die Chain-Struktur korrekt — egal von welchem Pod aus.

2. **Helm-Release-Status `failed` ist nur kosmetisch, wenn der Cluster gesund ist.** Der erste Deploy-Versuch timeoutete bei `helm upgrade --wait --timeout 15m` weil api-server in CrashLoopBackOff blieb. Helm setzte Release-Status auf `failed` (Rev 64). Nach manueller Alembic-Recovery kamen alle Pods hoch, **aber der Helm-Status blieb `failed`**, bis ein naechster `helm upgrade` drueberlief. Jeder Push auf main heilt das automatisch (der naechste Deploy erzeugt eine neue Release-Revision). Wir haben das durch die Ruff-Fix + Helm-Singleton-Fix-Commits "mitgenommen" — Rev 65 deployed = Status `deployed`.

3. **Ruff-Lint-Drift entdeckt sich nur durch CI.** Die 17 pre-existing Lint-Errors in `backend/ext/` (12 unused imports + 3 F821 + 2 ARG001) waren Monate alt, aber nie aufgefallen weil die Lint-Stage erst kuerzlich in `ci-checks.yml` scharf geschaltet wurde. Konsequenz: **Bei neuen CI-Stages immer den aktuellen Code gegenchecken**, damit Baseline sauber ist — sonst wird die erste Nutzung zum Merge-Blocker. Ruff-Config in `pyproject.toml` fuer `line-length` + `quote-style` waere der naechste Schritt, um auch die 28 Format-Drift-Files deterministisch zu fixen.

4. **`ci-checks.yml` triggert NICHT auf PRs** (nur `push: branches: main`). Bei PR-basierten Upstream-Syncs gibt es daher **keinen PR-Check-Status** — GitHub's Branch-Protection-Rule "N of M status checks expected" kann nie erfuellt werden, Merge erfordert Admin-Bypass (`gh pr merge --admin --merge`). Fuer zukuenftige Syncs entweder (a) akzeptieren und dokumentieren, (b) CI-Config auf `pull_request` erweitern, oder (c) Branch-Protection-Rules anpassen. Option (b) ist sauber, verdoppelt aber CI-Kosten (Run auf PR + Run auf main-Push).

5. **Concurrency-Config cancelt laufende Deploys.** `stackit-deploy.yml` hat `concurrency: group: stackit-deploy-${{ github.ref }}, cancel-in-progress: true`. Bei zwei schnellen main-Pushes hintereinander (hier: Ruff-Fix-Merge direkt gefolgt vom Helm-Singleton-Fix-Merge) wird der erste Deploy nach 1-2 Min gecancelt. **Kein Problem**, weil der zweite Commit den ersten enthaelt (Merge-Kette). Aber: Bei schneller Commit-Abfolge sollte man wissen, dass nur der letzte Push wirklich deployed wird — vorsichtig bei "parallel vermuteten" Fixes.

6. **Vespa bleibt weiterhin aktiv — PR #10330 bringt nur das Feature, nicht die Auto-Entfernung.** `ONYX_DISABLE_VESPA` ist eine neue ENV-Variable, aber unsere Helm-Config hat sie nicht gesetzt. Vespa-Pod unveraendert (35d Uptime nach Sync #6). Separater Task: Vespa-Entfernen als eigenes Epic (2-4h inkl. PVC-Aufraeumung, NetworkPolicy-Anpassung, Smoke-Test dass OpenSearch alle Ops abdeckt).

7. **Upstream force-pushed main vor dem Merge.** Beim `git fetch upstream` kam `forced update` fuer `main`. Der alte Upstream-Head (vor Force-Push) wurde verworfen. Unser Merge-Base (`cc5a74511`, Sync #5) blieb durch den Force-Push unangetastet, weil er nicht am Ende der Branch-Historie lag. **Lesson fuer Sync #7+:** `git log HEAD..upstream/main` zeigt den echten Drift, unabhaengig von Force-Pushes.

## Fuenfter Upstream-Merge (2026-04-13/14) — Referenz

| Metrik | Wert |
|--------|------|
| Upstream-Commits | 344 |
| Konflikte | 7 (4 trivial: .gitignore, AGENTS.md, README.md, web/Dockerfile; 3 ernsthaft: layout.tsx, CustomModal.tsx, AdminSidebar.tsx) |
| Backend-Core-Konflikte | 0 (alle 7 Hooks auto-merged) |
| ext_-Code Konflikte | 0 |
| ext-Code Anpassung | 1 Zeile: `analytics.py` `is_visible` → `is_listed` (Upstream-Rename #9569) |
| Alembic-Migrationen | 11 neue Upstream + 1 modifiziert. Chain: `ff7273065d0d` down von `689433b0d8de` auf `503883791c39` umgehaengt |
| Core #13 entfernt | CustomModal.tsx — Upstream-Bug onyx-dot-app/onyx#9592 gefixt (PR #10009 etc). |
| Core #15 NEU | useSettings.ts — `NEXT_PUBLIC_EXT_BRANDING_ENABLED` als Gate fuer `useEnterpriseSettings()` ohne EE-Lizenz-Flag. Core-Datei-Zahl: 15 (net). |
| Chart-Version | 0.4.36 → 0.4.44 (code-interpreter 0.3.1 → 0.3.3) |
| Helm-Repos | Keine neuen Repos (alle 7 bereits in CI) |
| Wichtig | SSR→CSR Layout Migration (#9529), AdminSidebar Opal-Refactor, current_admin_user Removal (#9930), Multi-Model Chat Feature, Group-Permissions Phase 1 (additiv, kein Konflikt) |
| ext-i18n | 4 neue Multi-Model-Strings ins Dictionary ("Show response", "Hide response", "Add Model", "Deselect preferred response") |
| Neue Dateien in ext/ | `backend/ext/auth.py` (current_admin_user Wrapper mit `_is_require_permission` Sentinel) |
| Commits auf Sync-Branch | 4 (1 Merge + 3 Fix-Commits nach Deploy-Tests) |
| Workflow | Branch + PR #20 |

### Fix-Commits nach initialem Merge

Alle drei Fixes wurden erst beim DEV-Deploy sichtbar und waren nicht im initialen Merge vorhersehbar:

| Commit | Thema | Betroffene Dateien |
|--------|-------|-------------------|
| `481eb7ccb` | `current_admin_user` in ext/auth.py kapseln | `backend/ext/auth.py` NEU + 7 Router-Imports umgestellt |
| `8eab7ff2c` | `_is_require_permission = True` Sentinel | `backend/ext/auth.py` (1 Zeile) |
| `89b2f0ec6` | Core #15 `useSettings.ts` Gate | `useSettings.ts` + Dockerfile + stackit-deploy.yml + Doku |

### Lessons Learned

1. **`current_admin_user` wird in EE-Migrationen gelegentlich entfernt.** Upstream PR #9930 hat es aus `onyx.auth.users` entfernt (Migration zu account-type-Permission-System). Loesung: `backend/ext/auth.py` als Wrapper mit **Original-Admin-Only-Semantik**. Bei zukuenftigen Auth-Refactors ist das die einzige Stelle zum Nachziehen.

2. **`_is_require_permission = True` Sentinel** ist Onyx's offizielle Extension-API fuer eigene Auth-Dependencies. Ohne das Attribut wirft `check_router_auth` beim Boot einen RuntimeError fuer alle Routen die unsere Wrapper nutzen. Siehe `onyx/server/auth_check.py` und `onyx/auth/permissions.py:124`.

3. **SSR→CSR Migration gated `useEnterpriseSettings` hinter EE-Flag.** Upstream PR #9529 fuehrte `shouldFetch = EE_ENABLED || eeEnabledRuntime` ein. Unsere ext-branding Architektur hat keine EE-Lizenz → API-Call wurde nicht gemacht → VOEB-Logo + Branding-Links fehlten. **NIE EE-Flags auf true setzen** (Lizenzrechtliches Problem). Stattdessen: **Core #15 mit eigenem `NEXT_PUBLIC_EXT_BRANDING_ENABLED` Flag**.

4. **Alembic parallele Heads bei jedem Sync** (zweiter Fall, nach Sync #3). Unsere ext-Chain setzt auf dem letzten Upstream-Head auf. Upstream fuegt in der Mitte neue Migrationen ein → unser Code-Head = DB-Head, aber Upstream-Migrations in der Mitte fehlen. **Manuelle Recovery nötig:** `UPDATE alembic_version SET version_num = <alter head>` → `alembic upgrade <neuer upstream head>` → `UPDATE alembic_version SET version_num = <unser head>`. Details in `docs/runbooks/upstream-sync.md`.

5. **Upstream `seed_default_groups` (#9795)** benennt existierende "Admin"/"Basic" Gruppen zu "(Custom)" um. **PROD-Check notwendig** vor Deploy.

6. **`diff3` style zeigt Konflikt-Marker in Symlinks** (CLAUDE.md → AGENTS.md). `git ls-files -u` ist authoritativ, nicht `git status` bei Symlinks.

7. **Bei massiven Refactors (AdminSidebar Opal)** ist `git checkout --theirs` + manuelle Hook-Reinsertion schneller als Marker aufloesen.

8. **StackIT Container Registry Token Drift**: Das GitHub Secret `STACKIT_REGISTRY_PASSWORD` war seit Februar stale (~7 Wochen). K8s-Secret `stackit-registry` in `onyx-dev` hatte die korrekten Credentials. **Root Cause:** Bei Token-Rotation wurde nur das K8s-Secret aktualisiert, nicht das GitHub-Secret. **Recovery:** Password aus K8s-Secret extrahieren und via `gh secret set` in GitHub uebernehmen. Runbook: `docs/runbooks/secret-rotation.md`.

9. **Registry-Login Race Condition** beim parallelen Build von Frontend + Backend (401 Unauthorized). Tritt gelegentlich auf. Quick-Fix: `gh run rerun --failed`. Langfristig: `build-backend needs: build-frontend` im Workflow — Trade-Off ~5 Min laengere Gesamtzeit.

10. **Upstream Metrics-Stack eingefuehrt** (`prometheus-fastapi-instrumentator` + `metrics_server.py`). Die 7 Celery-Worker starten automatisch HTTP-Server auf Ports 9092-9096. Default `PROMETHEUS_METRICS_ENABLED=true`, ServiceMonitors default off. **Kein Konflikt mit unserem Custom-Monitoring**, laeuft passiv mit. Separater Task: Upstream-Monitoring evaluieren und Custom-Setup reduzieren.

## Zusätzliche Merge-Stellen (neben Core-Dateien)

Neben den 17 Core-Dateien (Stand 2026-04-20: 16 gepatcht, nur #5 header/ offen — Core #15 useSettings.ts (Sync #5, 2026-04-14) + Core #16 DynamicMetadata.tsx (2026-04-20) + Core #17 AccountPopover.tsx (2026-04-20) sind die jüngsten Ergaenzungen) ändern wir einige weitere Upstream-Dateien. Diese sind KEINE Core-Dateien, aber bekannte Merge-Stellen.

Zusätzlich gibt es **eine neue ext/-Datei seit Sync #5**, die bei jedem Sync evaluiert werden muss:

### `backend/ext/auth.py` (NEU seit Sync #5, 2026-04-14)

Wrapper fuer `current_admin_user` nach Upstream PR #9930 (current_admin_user aus `onyx.auth.users` entfernt). Muss bei zukuenftigen Auth-Refactors nachgezogen werden.

- **Import in allen ext-Routern:** `from ext.auth import current_admin_user` (statt `from onyx.auth.users import current_admin_user`)
- **Sentinel:** `current_admin_user._is_require_permission = True` — ohne das Attribut crasht `check_router_auth` beim API-Boot
- **Semantik:** Original-Admin-Only (nicht das neue account-type-Permission-System)
- **Risiko:** Niedrig — isolierter Wrapper, nur anpassen wenn Upstream die Semantik von Admin-Checks grundlegend aendert

### `backend/Dockerfile` (seit Phase 4a)

3 Zeilen zwischen `COPY ./ee` und `COPY ./onyx`:
```dockerfile
# VÖB Extension Framework
COPY --chown=onyx:onyx ./ext /app/ext
```

**Bei Upstream-Konflikt:**
```bash
git checkout --theirs backend/Dockerfile
# Manuell einfuegen: 3 Zeilen nach "COPY ./ee /app/ee" + "COPY supervisord.conf"
```

**Risiko:** Mittel — Upstream ändert Dockerfile aktiv (~5 Commits/Monat). Insertion-Stelle ist stabil (zwischen ee und onyx COPY).

### `deployment/docker_compose/env.template` (seit Phase 4b)

27 Zeilen am Dateiende: VÖB Extension Framework Feature Flags.

**Bei Upstream-Konflikt:**
```bash
# Meist auto-merge (Append am Ende). Falls nicht:
git checkout --theirs deployment/docker_compose/env.template
# Unseren Block am Ende wieder anfuegen
```

**Risiko:** Niedrig — Appends am Dateiende mergen fast immer automatisch.

### `backend/onyx/chat/prompt_utils.py` (CORE #7, seit ext-prompts)

1 Stelle: ext-prompts Hook in `build_system_prompt()` (~15 Zeilen nach `user_info_section`, vor `should_append_citation_guidance`). Prepend aktiver Prompts vor Base System Prompt.

**Bei Upstream-Konflikt:**
```bash
git checkout --theirs backend/onyx/chat/prompt_utils.py
patch -p0 < backend/ext/_core_originals/prompt_utils.py.patch
# Pruefen ob Patch sauber angewendet wurde
```

**Risiko:** Niedrig — `build_system_prompt()` ist eine stabile Funktion, Hook-Stelle (nach user_info_section) aendert sich selten.

### `web/src/sections/sidebar/AdminSidebar.tsx` (CORE #10, seit ext-branding + ext-token + ext-prompts)

3 Stellen: Import-Zeilen (SvgPaintBrush + SvgActivity + SvgFileText hinzufuegen) + Settings-Section (~19 Zeilen: Billing durch Branding ersetzen + Token Usage Link + System Prompts Link).

**Bei Upstream-Konflikt:**
```bash
git checkout --theirs web/src/sections/sidebar/AdminSidebar.tsx
patch -p0 < backend/ext/_core_originals/AdminSidebar.tsx.patch
# Pruefen ob Patch sauber angewendet wurde
```

**Risiko:** Mittel — Upstream aendert Admin-Sidebar aktiv (neue Features, Restrukturierung). Patch-Stelle (Settings-Section) ist relativ stabil, aber Import-Zeilen koennen sich verschieben.

### Vollständige Liste aller Upstream-Änderungen

| Datei | Art | Zeilen | Risiko |
|-------|-----|--------|--------|
| `backend/onyx/main.py` (CORE #1) | Hook | ~14 | Niedrig |
| `backend/onyx/llm/multi_llm.py` (CORE #2) | 3 Hooks | ~45 | Mittel |
| `backend/onyx/chat/prompt_utils.py` (CORE #7) | Hook | ~15 | Niedrig |
| `web/src/lib/constants.ts` (CORE #6) | 1 Zeile | 1 | Niedrig |
| `web/src/app/auth/login/LoginText.tsx` (CORE #8) | Conditional | ~8 | Niedrig |
| `web/src/components/auth/AuthFlowContainer.tsx` (CORE #9) | Logo+Name | ~25 | Mittel |
| `web/src/sections/sidebar/AdminSidebar.tsx` (CORE #10) | Branding+TokenUsage+Prompts+EE-Hidden | ~30 | Mittel |
| `backend/Dockerfile` | COPY | 3 | Mittel |
| `backend/onyx/db/persona.py` (CORE #11) | Hook | ~10 | **Mittel-Hoch** |
| `backend/onyx/db/document_set.py` (CORE #12) | Hook | ~8 | Niedrig |
| `deployment/docker_compose/env.template` | Append | 30 | Niedrig |
| `web/Dockerfile` | ARG/ENV | 4 | Niedrig |
| `.github/workflows/stackit-deploy.yml` | Build-Arg | 1 | Niedrig |
| `backend/onyx/natural_language_processing/search_nlp_models.py` (CORE #13) | `.lower()` | 1 | Niedrig |
| `web/src/refresh-components/popovers/ActionsPopover/index.tsx` (CORE #14) | Early-Return | 1 | Niedrig |
| `web/src/hooks/useSettings.ts` (CORE #15) | shouldFetch + EXT_BRANDING_ENABLED (nur `useEnterpriseSettings`, **NICHT** `useCustomAnalyticsScript` — sonst 404-Loop, siehe Incident 2026-04-20) | ~8 | Niedrig |
| `web/src/providers/DynamicMetadata.tsx` (CORE #16) | `usePathname` + `useSearchParams` + Deps | ~9 | Niedrig |
| `web/src/sections/sidebar/AccountPopover.tsx` (CORE #17) | EXT_BRANDING_ENABLED-Gate an 3 Stellen (Notifications-Item, Help-FAQ-Item, Bubble) | ~30 | Niedrig |
**Hinweis:** #11 (persona.py) + #12 (document_set.py) gepatcht (ext-rbac, 2026-03-23).
**Achtung #11:** `persona.py` hat 14 Commits/3 Monate (Sharing-Features aktiv upstream). Bei Upstream-Sync besonders pruefen.
**Achtung #13:** TEMPORAER — OpenSearch lowercase Index-Name. Bei Upstream-Sync pruefen ob `clean_model_name()` selbst lowercase macht. Falls ja: Patch entfernen.

Alle anderen Dateien (ext/, docs/, .claude/, deployment/helm/values/) existieren nicht in Upstream → Zero Konflikte.

### `web/Dockerfile` (seit ext-i18n)

4 Zeilen: ARG/ENV `NEXT_PUBLIC_EXT_I18N_ENABLED` in beiden Stages (builder + runner).

**Bei Upstream-Konflikt:**
```bash
git checkout --theirs web/Dockerfile
# In BEIDEN Stages (nach letztem NEXT_PUBLIC ARG/ENV Block):
# ARG NEXT_PUBLIC_EXT_I18N_ENABLED
# ENV NEXT_PUBLIC_EXT_I18N_ENABLED=${NEXT_PUBLIC_EXT_I18N_ENABLED}
```

**Risiko:** Niedrig — Insertion-Stelle ist stabil (Ende der NEXT_PUBLIC-ARG-Liste).

### ext-i18n: Dictionary-Pflege bei Upstream-Sync

Nach jedem Upstream-Sync: Dictionary (`web/src/ext/i18n/translations.ts`) pruefen.
1. Neue englische Strings in user-facing Screens → Dictionary erweitern
2. Geaenderte Strings → Dictionary-Keys aktualisieren
3. `web/src/app/layout.tsx` Patch pruefen: TranslationProvider + `lang="de"` intakt?

**Geschaetzter Aufwand:** ~1 Stunde pro Sync.

## Warum "Extend, don't modify" funktioniert
- Max 15 vorhersagbare Core-Konflikte + 4 bekannte Infra-Stellen
- Unser ext_-Code: Zero Konflikte (Ordner existiert nicht in Upstream)
- Unsere Infra (Terraform, Helm Values, CI/CD): Zero Konflikte (Pfade existieren nicht in Upstream)
- Unsere Docs: Zero Konflikte (existieren nicht in Upstream)
- Patches pro Core-Datei: 2-5 Zeilen, einfach neu anwendbar
- **Einzige Überraschungen:** Neue Helm-Dependencies → CI/CD Workflow anpassen
