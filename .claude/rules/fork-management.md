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
- 10 Core-Dateien → Upstream übernehmen, Patches neu anwenden (siehe unten)
- `backend/Dockerfile` → Upstream übernehmen, COPY ext/ neu einfügen (siehe "Zusätzliche Merge-Stellen")
- `deployment/docker_compose/env.template` → Manuell mergen (wir appenden am Ende, Upstream ändert Mitte)

**Unerwartete Konflikte:**
- Dateien in `backend/onyx/`, `web/src/` (außer Core) = Regeln gebrochen
- Ursache analysieren, ext_-Code anpassen (NICHT Onyx-Code)

### 5. Core-Datei-Patches aktualisieren

Fuer JEDE gepatchte Core-Datei (aktuell 10 von 12 gepatcht: main.py, multi_llm.py, prompt_utils.py, constants.ts, LoginText.tsx, AuthFlowContainer.tsx, AdminSidebar.tsx, layout.tsx, persona.py, document_set.py — die 2 ungepatchten: access.py (#3), header/ (#5)):

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

## Zusätzliche Merge-Stellen (neben Core-Dateien)

Neben den 12 Core-Dateien ändern wir 2 weitere Upstream-Dateien. Diese sind KEINE Core-Dateien, aber bekannte Merge-Stellen:

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
| `web/src/sections/modals/llmConfig/CustomModal.tsx` (CORE #13) | UI-Fix | ~25 | Mittel |
**Hinweis:** #11 (persona.py) + #12 (document_set.py) gepatcht (ext-rbac, 2026-03-23).
**Achtung #11:** `persona.py` hat 14 Commits/3 Monate (Sharing-Features aktiv upstream). Bei Upstream-Sync besonders pruefen.
**Achtung #13:** TEMPORAER — Upstream-Bug onyx-dot-app/onyx#9592. Bei Upstream-Sync pruefen ob Issue gefixt. Falls ja: Patch entfernen, `.original` + `.patch` loeschen, #13 aus core-dateien.md entfernen.

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
- Max 10 vorhersagbare Core-Konflikte + 4 bekannte Infra-Stellen
- Unser ext_-Code: Zero Konflikte (Ordner existiert nicht in Upstream)
- Unsere Infra (Terraform, Helm Values, CI/CD): Zero Konflikte (Pfade existieren nicht in Upstream)
- Unsere Docs: Zero Konflikte (existieren nicht in Upstream)
- Patches pro Core-Datei: 2-5 Zeilen, einfach neu anwendbar
- **Einzige Überraschungen:** Neue Helm-Dependencies → CI/CD Workflow anpassen
