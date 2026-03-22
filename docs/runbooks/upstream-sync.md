# Runbook: Upstream-Sync (Onyx FOSS)

**Upstream Remote:** `upstream` → `onyx-dot-app/onyx-foss`
**Sync-Zyklus:** Monatlich (oder bei Security-Patches sofort)
**Workflow:** Immer Branch + PR (Diff-Inspektion bei grossen Merges)

---

## Vor jedem Sync

> **Hinweis:** `git rerere` und `merge.conflictstyle diff3` sind aktiviert — wiederkehrende Konflikte (z.B. AGENTS.md) werden automatisch geloest. Neu auftretende Konflikte muessen weiterhin manuell geprueft werden.

### 1. Evaluieren (NICHT mergen)

```bash
git fetch upstream
git log main..upstream/main --oneline --no-merges | wc -l  # Anzahl Commits
git diff main..upstream/main --stat | tail -5               # Geaenderte Dateien
```

### 2. Hook-Dateien auf Konflikte pruefen

Unsere 8 gepatchten Core-Dateien (MUESSEN nach jedem Sync intakt sein):

```bash
for FILE in \
  "backend/onyx/main.py" \
  "backend/onyx/llm/multi_llm.py" \
  "backend/onyx/chat/prompt_utils.py" \
  "web/src/lib/constants.ts" \
  "web/src/app/auth/login/LoginText.tsx" \
  "web/src/components/auth/AuthFlowContainer.tsx" \
  "web/src/sections/sidebar/AdminSidebar.tsx" \
  "web/src/app/layout.tsx"; do
  CHANGES=$(git diff main..upstream/main -- "$FILE" | wc -l)
  if [ "$CHANGES" -gt 0 ]; then
    echo "KONFLIKT-RISIKO: $FILE ($CHANGES diff-Zeilen)"
  else
    echo "OK: $FILE"
  fi
done
```

### 3. Neue Alembic Migrations identifizieren

```bash
git diff main..upstream/main --name-only | grep "alembic.*versions.*\.py$"
```

### 4. Helm Chart Version pruefen

```bash
git diff main..upstream/main -- deployment/helm/charts/onyx/Chart.yaml
git diff main..upstream/main -- deployment/helm/charts/onyx/values.yaml | head -30
```

---

## Waehrend des Sync

### 5. Branch + Merge

```bash
git checkout main && git pull origin main
git checkout -b chore/upstream-sync-YYYY-MM-DD
git merge upstream/main --no-commit --no-ff
```

### 6. Konflikte loesen

**Erwartete Konflikte:**

| Datei | Loesung |
|-------|---------|
| `AGENTS.md` | `git checkout --ours AGENTS.md` |
| `.github/CODEOWNERS` | `git checkout --ours .github/CODEOWNERS` |
| `.claude/skills` | `git checkout --ours .claude/skills` |
| `AdminSidebar.tsx` | Upstream nehmen, ext-Links manuell einfuegen |
| `web/Dockerfile` | Upstream nehmen, ARG/ENV `NEXT_PUBLIC_EXT_I18N_ENABLED` in beiden Stages neu einfuegen |
| Core-Dateien (falls betroffen) | Upstream nehmen, Patches neu anwenden |

**Nach Konflikt-Loesung:** `git add <datei>` fuer jede geloeste Datei.

### 7. Bekannte Fixes anwenden

#### 7a. OpenSearch + Vespa Konfiguration pruefen

OpenSearch ist seit v3.0.0 unser Default Document Index. Pruefen ob Upstream neue Env Vars oder Defaults eingefuehrt hat:

```bash
grep "OPENSEARCH\|opensearch.*enabled\|VESPA\|vespa.*enabled" deployment/helm/charts/onyx/values.yaml
```

Checkliste (Details: `docs/analyse-opensearch-vs-vespa.md` Abschnitt 6):
- `auth.opensearch.enabled: true` in values-common.yaml (OpenSearch Pod wird deployed)
- `configMap.ENABLE_OPENSEARCH_INDEXING_FOR_ONYX: "true"` (Dual-Write aktiv)
- **`vespa.enabled` MUSS `true` bleiben** — v3.x Code erfordert Vespa-Pod fuer Readiness Check (`wait_for_vespa_or_shutdown` in `app_base.py:517`). Erst ab v4.0.0 kann Vespa deaktiviert werden!
- Vespa Ressourcen auf Zombie-Mode pruefen: DEV/TEST 50m/512Mi, PROD 100m/512Mi (minimale Ressourcen, kein aktiver Index-Traffic)

**KRITISCH — Vespa StatefulSet:**
- `volumeClaimTemplates` sind **immutable** in Kubernetes. PVC-Groesse kann NICHT per Helm geaendert werden. Bei Bedarf: StatefulSet loeschen, PVC manuell loeschen, neu erstellen.
- Vespa benoetigt **mindestens 4 Gi memory LIMIT** (Hard-Check im Container-Startskript). `requests` koennen niedriger sein (z.B. 512Mi), aber `limits.memory` muss >= 4Gi bleiben.

#### 7b. Alembic Chain reparieren

```bash
# Pruefen ob Multiple Heads entstanden sind:
grep "down_revision.*a3b8d9e2f1c4" backend/alembic/versions/*.py

# Falls ja: ext-branding down_revision auf LETZTEN neuen Upstream-Migration-Hash setzen
# Kette: ... → [letzter Upstream] → ff7273065d0d (ext-branding) → ext-token → ext-prompts
```

#### 7c. AdminSidebar ext-Links

Die Upstream-Struktur kann sich aendern. Aktuell (Stand 2026-03-17):
- `buildItems()` Funktion, Section-basiert
- ext-Links in Section `SECTIONS.ORGANIZATION`
- Import: `SvgActivity, SvgFileText, SvgPaintBrush` aus `@opal/icons`

### 8. Core-Originals aktualisieren

```bash
# Fuer JEDE gepatchte Core-Datei:
git show upstream/main:backend/onyx/main.py > backend/ext/_core_originals/main.py.original
diff -u backend/ext/_core_originals/main.py.original backend/onyx/main.py \
  > backend/ext/_core_originals/main.py.patch
# Analog fuer alle 8 Dateien (main.py, multi_llm.py, prompt_utils.py,
# constants.ts, LoginText.tsx, AuthFlowContainer.tsx, AdminSidebar.tsx, layout.tsx)
#
# WICHTIG: layout.tsx nicht vergessen (ext-i18n TranslationProvider + lang="de")
git show upstream/main:web/src/app/layout.tsx > backend/ext/_core_originals/layout.tsx.original
diff -u backend/ext/_core_originals/layout.tsx.original web/src/app/layout.tsx \
  > backend/ext/_core_originals/layout.tsx.patch
```

### 9. Validierung

```bash
# Hook-Check (11 Stellen):
grep -q "register_ext_routers" backend/onyx/main.py && echo "OK: ext-Router"
grep -q "check_user_token_limit" backend/onyx/llm/multi_llm.py && echo "OK: Token-Limit"
grep -q "log_token_usage" backend/onyx/llm/multi_llm.py && echo "OK: Token-Log"
grep -q "EXT_CUSTOM_PROMPTS_ENABLED" backend/onyx/chat/prompt_utils.py && echo "OK: ext-Prompts"
grep -q "EXT_BRANDING_ENABLED" web/src/lib/constants.ts && echo "OK: ext-Branding"
grep -q "custom_header_content" web/src/app/auth/login/LoginText.tsx && echo "OK: Tagline"
grep -q "use_custom_logo" web/src/components/auth/AuthFlowContainer.tsx && echo "OK: Logo"
grep -q "ext-branding" web/src/sections/sidebar/AdminSidebar.tsx && echo "OK: Sidebar-Branding"
grep -q "ext-token" web/src/sections/sidebar/AdminSidebar.tsx && echo "OK: Sidebar-Token"
grep -q "ext-prompts" web/src/sections/sidebar/AdminSidebar.tsx && echo "OK: Sidebar-Prompts"
grep -q "COPY.*ext" backend/Dockerfile && echo "OK: Dockerfile"
# ext-i18n (seit 2026-03-22):
grep -q "TranslationProvider" web/src/app/layout.tsx && echo "OK: TranslationProvider"
grep -q 'lang="de"' web/src/app/layout.tsx && echo "OK: lang=de"
grep -q 'from.*@/ext/i18n' web/src/app/auth/login/LoginText.tsx && echo "OK: i18n LoginText"
grep -q 'from.*@/ext/i18n' web/src/components/auth/AuthFlowContainer.tsx && echo "OK: i18n AuthFlow"
grep -q "Neuer Chat" web/src/lib/constants.ts && echo "OK: UNNAMED_CHAT deutsch"
grep -q "I18N" web/Dockerfile && echo "OK: web/Dockerfile i18n ARG"

# Helm Template (mit Dummy-Secrets):
helm template test deployment/helm/charts/onyx/ \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-dev.yaml \
  --set auth.postgresql.values.password=d \
  --set auth.redis.values.redis_password=d \
  --set auth.objectstorage.values.s3_aws_access_key_id=d \
  --set auth.objectstorage.values.s3_aws_secret_access_key=d \
  --set auth.dbreadonly.values.db_readonly_password=d \
  2>/dev/null | grep -i "onyx-opensearch" && echo "OK: OpenSearch-Pod vorhanden" || echo "WARNUNG: Kein OpenSearch-Pod im Template!"

# Vespa Zombie-Mode pruefen (MUSS noch aktiv sein bis v4.0.0):
helm template test deployment/helm/charts/onyx/ \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-dev.yaml \
  --set auth.postgresql.values.password=d \
  --set auth.redis.values.redis_password=d \
  --set auth.objectstorage.values.s3_aws_access_key_id=d \
  --set auth.objectstorage.values.s3_aws_secret_access_key=d \
  --set auth.dbreadonly.values.db_readonly_password=d \
  2>/dev/null | grep -i "da-vespa" && echo "OK: Vespa-Pod vorhanden (Zombie-Mode)" || echo "FEHLER: Vespa-Pod fehlt — v3.x braucht ihn!"

# Merge-Markers:
git diff --cached --name-only | xargs grep -l "<<<<<<" 2>/dev/null && echo "FEHLER!" || echo "OK"
```

### 10. Commit + PR

```bash
# Spezifische Dateien stagen — KEIN git add -A (Commit-Workflow-Regel: nur gezielte Dateien)
git add backend/onyx/main.py backend/onyx/llm/multi_llm.py backend/onyx/chat/prompt_utils.py
git add web/src/lib/constants.ts web/src/app/auth/login/LoginText.tsx
git add web/src/components/auth/AuthFlowContainer.tsx web/src/sections/sidebar/AdminSidebar.tsx
git add web/src/app/layout.tsx backend/Dockerfile web/Dockerfile
git add deployment/helm/charts/onyx/ deployment/docker_compose/env.template
git add backend/alembic/ backend/ext/_core_originals/ AGENTS.md
# ... alle weiteren geaenderten Dateien explizit anfuegen
git commit --no-verify -m "chore(upstream): Merge upstream/main — N Commits"
git push origin chore/upstream-sync-YYYY-MM-DD

gh pr create --base main --head chore/upstream-sync-YYYY-MM-DD \
  -R CCJ-Development/voeb-chatbot \
  --title "chore(upstream): Merge upstream/main — N Commits" \
  --body "..."
```

---

## Nach dem Sync

### 11. DEV deployen und verifizieren

```bash
# PR mergen (nach Review) — IMMER --squash (konsistent mit fork-management.md)
gh pr merge <NR> -R CCJ-Development/voeb-chatbot --squash --delete-branch

# CI/CD triggert auto-deploy auf DEV
# Alternativ manuell:
gh workflow run stackit-deploy.yml -f environment=dev -R CCJ-Development/voeb-chatbot
```

**ACHTUNG — Alembic:** `alembic upgrade head` holt eingefuegte Upstream-Migrationen NICHT nach, wenn die DB bereits auf einem spaeteren Head gestempelt ist. Wenn Upstream neue Migrationen in die Chain eingefuegt hat, muessen diese ggf. manuell via SQL ausgefuehrt werden (siehe Sync #3 Lesson Learned in `docs/runbooks/upstream-sync.md` Historische Syncs).

**ACHTUNG — OpenSearch-Passwort PROD:** PROD nutzt ein eigenes OpenSearch-Passwort (GitHub Secret `OPENSEARCH_PASSWORD`). Bei Upstream-Aenderungen an der Chart-Authentifizierung (z.B. neue `auth.opensearch.*`-Felder) muessen die CI/CD-Workflow-Steps (`stackit-deploy.yml`) und `values-prod-secrets.yaml` geprueft und ggf. aktualisiert werden.

### 12. ext-i18n Dictionary pruefen

Nach jedem Sync: Pruefen ob Upstream neue/geaenderte englische Strings eingefuehrt hat.

```bash
# Geaenderte user-facing Dateien identifizieren (Login, Chat, Sidebar, Settings)
git diff HEAD~1 --name-only | grep -E "(auth|chat|sidebar|settings|input|modal)" | grep "\.tsx$"

# Neue Strings in diesen Dateien suchen (Stichproben)
# Falls neue englische Strings → web/src/ext/i18n/translations.ts erweitern
```

Geschaetzter Aufwand: ~30-60 Minuten pro Sync.

### 13. Health Check

```bash
# Pods pruefen
kubectl get pods -n onyx-dev

# API Logs (Alembic + OpenSearch + Vespa Fehler)
kubectl logs -n onyx-dev -l app=api-server --tail=50 | grep -i "error\|alembic\|opensearch\|vespa"

# Health
curl -s https://dev.chatbot.voeb-service.de/api/health
```

---

## Historische Syncs

| Datum | Commits | Konflikte | Dauer | Besonderheiten |
|-------|---------|-----------|-------|----------------|
| 2026-03-03 | 415 | 4 (AGENTS, .claude, Chart) | ~5 Min | Erster Sync |
| 2026-03-06 | 100 | 1 (AGENTS) | ~5 Min | PR #3 |
| 2026-03-17 | 161 | 3 (AGENTS, CODEOWNERS, AdminSidebar) | ~45 Min | PR #18, AdminSidebar Rewrite |
| 2026-03-22 | 71 | 0 (alle auto-merged) | ~10 Min | PR #19, Chart 0.4.36, tool_choice-Fix, Hook-System, 8 OpenSearch-Commits |

## NIEMALS

- Blind `git merge upstream/main` ohne `--no-commit` — immer pruefen
- PROD deployen ohne DEV-Verifizierung
- Migrations ohne Chain-Check uebernehmen
- AdminSidebar ohne Hook-Check deployen
- `vespa.enabled` auf `false` setzen (bis v4.0.0! — Celery-Worker crashen ohne Vespa-Pod)
- Vespa StatefulSet `volumeClaimTemplates` aendern (immutable — K8s lehnt Update ab)
- Vespa memory LIMIT unter 4 Gi setzen (Hard-Check im Container, Pod startet nicht)

---

## Referenzen

- `docs/analyse-opensearch-vs-vespa.md` — Vollstaendige Analyse inkl. Upstream-Sync-Checkliste (Abschnitt 6)
- `.claude/rules/fork-management.md` — Fork-Management Regeln
