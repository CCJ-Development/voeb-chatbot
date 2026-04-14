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
| 2026-04-13/14 | 344 | 7 (4 trivial, 3 ernsthaft + 3 Fix-Commits post-Deploy) | ~4-6 Std | PR #20, Chart 0.4.44, SSR→CSR Layout, AdminSidebar Opal, current_admin_user Removal, Core #13 entfernt, Core #15 NEU |

## Recovery-Szenarien

### Szenario A: Alembic parallele Heads — fehlende Migrations nach Deploy

**Symptom:** API-Server startet, aber alle Datenbank-Queries werfen `UndefinedColumn` oder `relation does not exist`. Pod ist Running aber nicht funktional.

**Ursache:** Unsere ext-Chain (z.B. `ff7273065d0d` → ... → `d8a1b2c3e4f5`) setzt auf einem alten Upstream-Head auf. Upstream fuehrt neue Migrations "in der Mitte" ein. Alembic sieht: `current == head`, fuehrt nichts aus → DB-Schema haengt hinterher.

**Bei Sync #5 aufgetreten:** 11 Upstream-Migrations (group_permissions_phase1, seed_default_groups, rename_persona_is_visible_to_is_listed, etc.) wurden nicht ausgefuehrt. Kolumnen `user.account_type`, `persona.is_listed`, Tabelle `permission_grant` fehlten.

**Recovery:**

```bash
# 1. Pod-Name finden
POD=$(kubectl get pods -n onyx-dev -l app=api-server -o jsonpath='{.items[0].metadata.name}')

# 2. Aktuellen DB-Head bestaetigen
kubectl exec -n onyx-dev $POD -- alembic current
# Output z.B.: d8a1b2c3e4f5 (head)

# 3. DB-State pruefen — fehlen erwartete Schema-Aenderungen?
kubectl exec -n onyx-dev $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    # Kandidaten fuer Schema-Sentinels
    tests = {
      'user.account_type': \"SELECT 1 FROM information_schema.columns WHERE table_name='user' AND column_name='account_type'\",
      'persona.is_listed': \"SELECT 1 FROM information_schema.columns WHERE table_name='persona' AND column_name='is_listed'\",
      'permission_grant table': \"SELECT 1 FROM information_schema.tables WHERE table_name='permission_grant'\",
    }
    for name, sql in tests.items():
        print(f'{name}: {bool(conn.execute(text(sql)).scalar())}')
"

# 4. Falls Schema-Sentinels False sind: Manuelle Migration
#    Strategie: alembic_version temporaer auf alten Upstream-Head setzen,
#    upgrade auf neuen Upstream-Head, dann zurueck auf unseren ext-Head.

# 4a. Aktuellen Head sichern
CURRENT_HEAD=$(kubectl exec -n onyx-dev $POD -- alembic current 2>&1 | grep -oE '[a-f0-9]{12} \(head\)' | awk '{print $1}')
echo "Unser Head: $CURRENT_HEAD"

# 4b. Alten Upstream-Head recherchieren (vor dem Sync, war die down_revision der ersten ext-Migration VOR dem Sync)
#    Sync #5: alter upstream head war 689433b0d8de, neuer ist 503883791c39
OLD_UPSTREAM_HEAD="689433b0d8de"
NEW_UPSTREAM_HEAD="503883791c39"

# 4c. alembic_version zurueckstellen
kubectl exec -n onyx-dev $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text(\"UPDATE alembic_version SET version_num = '$OLD_UPSTREAM_HEAD'\"))
    conn.commit()
"

# 4d. Upstream-Migrations ausfuehren
kubectl exec -n onyx-dev $POD -- alembic upgrade $NEW_UPSTREAM_HEAD

# 4e. alembic_version auf unseren echten Head zurueckstellen
kubectl exec -n onyx-dev $POD -- python -c "
from sqlalchemy import create_engine, text
import os
url = f\"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}\"
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text(\"UPDATE alembic_version SET version_num = '$CURRENT_HEAD'\"))
    conn.commit()
"

# 5. API-Server Pod neustarten, damit er die DB neu evaluiert
kubectl delete pod -n onyx-dev $POD

# 6. Verifikation
kubectl get pods -n onyx-dev -l app=api-server
curl -sS -o /dev/null -w "%{http_code}\n" https://dev.chatbot.voeb-service.de/api/health
```

**Wichtig vor PROD-Deploy:** Auf PROD **immer** denselben Check vorher machen. Backup der `alembic_version` Tabelle erstellen, falls Rollback noetig wird. PROD-User-Daten nie per Downgrade verlieren.

### Szenario B: Fehlende ext-Router nach Deploy

**Symptom:** Admin-Sidebar zeigt keine ext-Links (Branding, Token, Prompts), API liefert 404 fuer `/api/enterprise-settings`, Logs zeigen nur `Extension health router registered` — andere ext-Router fehlen.

**Ursache:** Upstream hat eine Dependency oder Funktion entfernt, die unsere Router importieren. Der Import scheitert, die Exception wird im `try/except` in `main.py` gefangen, aber nur der **erste** erfolgreiche Router (`health`) ist registriert — alle weiteren brechen auf dem Import-Fehler ab.

**Diagnose:**

```bash
POD=$(kubectl get pods -n onyx-dev -l app=api-server -o jsonpath='{.items[0].metadata.name}')

# 1. Welche ext-Router wurden registriert?
kubectl logs -n onyx-dev $POD 2>&1 | grep -iE "extension.*router.*registered"
# Erwartet: 7-8 Zeilen (health, branding, token, prompts, rbac, doc-access, analytics, audit)

# 2. Isolated Import-Test
kubectl exec -n onyx-dev $POD -- python -c "
try:
    from ext.routers.branding import admin_router
    print('branding OK')
except Exception as e:
    import traceback; traceback.print_exc()
"

# 3. Wenn ImportError: Neue/entfernte Onyx-Funktion suchen
kubectl exec -n onyx-dev $POD -- python -c "
from onyx.auth.users import current_admin_user  # z.B. diese Funktion
"
```

**Bei Sync #5 aufgetreten:** Upstream PR #9930 hat `current_admin_user` aus `onyx.auth.users` entfernt. Fix: `backend/ext/auth.py` als Wrapper mit `_is_require_permission = True` Sentinel, alle ext-Router-Imports umgestellt.

**Recovery-Muster:**
1. Upstream-Funktion identifizieren die nicht mehr existiert
2. Wrapper in `backend/ext/auth.py` (oder `backend/ext/<module>.py`) implementieren mit alter Semantik
3. Falls Onyx's `check_router_auth` involviert ist: `_is_require_permission = True` Sentinel auf den Wrapper setzen
4. Imports in allen betroffenen ext-Routern umstellen

### Szenario C: `useEnterpriseSettings` / Branding-Assets nicht geladen

**Symptom:** Admin-Sidebar zeigt Onyx-Standard-Logo statt VOEB-Branding, "Spending Limits"/"Upgrade Plan" erscheinen, obwohl unsere ext-Config das ausblenden sollte.

**Ursache:** Upstream hat den Client-Side-Call fuer `useEnterpriseSettings()` hinter einen EE-Lizenz-Flag gegatet. Unsere Gate-Condition `extBrandingActive = settings?.enterpriseSettings && !hasSubscription` ist false.

**Diagnose:**

```bash
# 1. Backend liefert Daten?
curl -sS https://dev.chatbot.voeb-service.de/api/enterprise-settings
# Erwartet: JSON mit application_name, use_custom_logo, etc.

# 2. Frontend-Build-Args pruefen
kubectl get deploy -n onyx-dev onyx-dev-web-server -o yaml | grep -i NEXT_PUBLIC_EXT_BRANDING
# Erwartet: NEXT_PUBLIC_EXT_BRANDING_ENABLED=true
```

**Bei Sync #5 aufgetreten:** Upstream PR #9529 (SSR→CSR Migration) hat in `web/src/hooks/useSettings.ts` den Check `shouldFetch = EE_ENABLED || eeEnabledRuntime` eingefuehrt.

**Recovery / Fix:** **NIE EE-Flags aktivieren** (Lizenzrechtlich problematisch). Stattdessen Core-Patch #15 in `web/src/hooks/useSettings.ts`:
```typescript
const EXT_BRANDING_ENABLED =
  process.env.NEXT_PUBLIC_EXT_BRANDING_ENABLED?.toLowerCase() === "true";
const shouldFetch = EE_ENABLED || eeEnabledRuntime || EXT_BRANDING_ENABLED;
```
Plus Build-Arg `NEXT_PUBLIC_EXT_BRANDING_ENABLED=true` in `web/Dockerfile` und `stackit-deploy.yml`.

### Szenario D: Registry-Credentials Drift

**Symptom:** CI/CD `build-backend` oder `build-frontend` scheitert mit `Error response from daemon: login attempt to https://registry.onstackit.cloud/v2/ failed with status: 401 Unauthorized`. DEV/PROD-Pods laufen weiter (Image-Pull OK).

**Ursache:** `STACKIT_REGISTRY_PASSWORD` in GitHub ist veraltet, K8s-Secret hat aktuellere Credentials.

**Recovery:** Siehe `docs/runbooks/secret-rotation.md` → Abschnitt "Container Registry Token (StackIT)" → "Recovery bei Drift".

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
