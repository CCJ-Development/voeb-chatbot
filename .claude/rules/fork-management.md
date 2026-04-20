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
