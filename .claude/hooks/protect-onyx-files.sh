#!/bin/bash
# Claude Code Hook: Blockiert Änderungen an Onyx-Dateien (deterministisch)
# Triggert bei Edit/Write Tool — Exit Code 2 = Aktion blockieren

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')

# Kein Dateipfad → durchlassen
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Erlaubte Verzeichnisse (unser Code)
if [[ "$FILE_PATH" == */backend/ext/* ]] || \
   [[ "$FILE_PATH" == */web/src/ext/* ]] || \
   [[ "$FILE_PATH" == */docs/* ]] || \
   [[ "$FILE_PATH" == */.claude/* ]] || \
   [[ "$FILE_PATH" == */.github/* ]] || \
   [[ "$FILE_PATH" == */.githooks/* ]] || \
   [[ "$FILE_PATH" == */deployment/docker_compose/.env* ]] || \
   [[ "$FILE_PATH" == */web/src/app/admin/ext-* ]]; then
  exit 0  # Erlaubt
fi

# 16 erlaubte Core-Dateien (Stand 2026-04-20, synchron mit .githooks/pre-commit)
# Source of Truth: .claude/rules/core-dateien.md
ALLOWED_CORE=(
  # Backend Core (7)
  "backend/onyx/main.py"                                           # #1  Router registrieren
  "backend/onyx/llm/multi_llm.py"                                  # #2  Token Hook
  "backend/onyx/access/access.py"                                  # #3  Access Control
  "backend/onyx/chat/prompt_utils.py"                              # #7  System Prompts
  "backend/onyx/db/persona.py"                                     # #11 Persona Gruppen-Zuordnung
  "backend/onyx/db/document_set.py"                                # #12 DocumentSet Gruppen-Zuordnung
  "backend/onyx/natural_language_processing/search_nlp_models.py"  # #13 OpenSearch lowercase

  # Frontend Core (9)
  "web/src/app/layout.tsx"                                         # #4  Navigation + i18n
  "web/src/components/header/"                                     # #5  Branding (noch offen)
  "web/src/lib/constants.ts"                                       # #6  CSS Variables
  "web/src/app/auth/login/LoginText.tsx"                           # #8  Login Tagline
  "web/src/components/auth/AuthFlowContainer.tsx"                  # #9  Login Icon + Text
  "web/src/sections/sidebar/AdminSidebar.tsx"                      # #10 Admin Sidebar
  "web/src/refresh-components/popovers/ActionsPopover/index.tsx"   # #14 Actions-Popover
  "web/src/hooks/useSettings.ts"                                   # #15 useEnterpriseSettings Gate
  "web/src/providers/DynamicMetadata.tsx"                          # #16 Title Sync pathname dep
)

for allowed in "${ALLOWED_CORE[@]}"; do
  if [[ "$FILE_PATH" == *"$allowed"* ]]; then
    exit 0  # Core-Datei — erlaubt (mit Vorsicht)
  fi
done

# Onyx-Code? → BLOCKIEREN
if [[ "$FILE_PATH" == */backend/onyx/* ]] || \
   [[ "$FILE_PATH" == */web/src/app/* ]] || \
   [[ "$FILE_PATH" == */web/src/components/* ]] || \
   [[ "$FILE_PATH" == */web/src/lib/* ]]; then
  echo "❌ BLOCKIERT: $FILE_PATH gehört zum Onyx-Core und darf nicht verändert werden." >&2
  echo "Erlaubt sind nur: backend/ext/, web/src/ext/, docs/, und die 16 definierten Core-Dateien." >&2
  exit 2  # Exit 2 = Aktion wird deterministisch blockiert
fi

# Alles andere durchlassen
exit 0
