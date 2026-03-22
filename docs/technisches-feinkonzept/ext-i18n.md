# Technisches Feinkonzept: ext-i18n (Deutsche Lokalisierung)

## Version

| Version | Datum | Autor | Beschreibung |
|---------|-------|-------|-------------|
| 1.0 | 2026-03-22 | COFFEESTUDIOS | Erstversion |

## 1. Zweck

Lokalisierung der Onyx-UI von Englisch auf Deutsch fuer ~150 VÖB-Mitarbeiter.
Onyx hat keine i18n-Infrastruktur und wird keine bekommen (Upstream hat i18n explizit abgelehnt, PR #1129).

## 2. Architektur

### Drei-Schichten-Modell

```
Schicht 0: ext-branding (bereits vorhanden)
  → application_name, custom_greeting_message, custom_header_content
  → ~6 Strings, DB-konfigurierbar

Schicht 1: t()-Aufrufe in Core-Patches
  → Import { t } from "@/ext/i18n" in gepatchten Core-Dateien
  → SSR-kompatibel (kein Flackern)
  → ~5 Strings (LoginText, AuthFlowContainer, constants)

Schicht 2: TranslationProvider (DOM-basiert)
  → MutationObserver ersetzt Text-Nodes zur Laufzeit
  → Uebersetzt Placeholders, Titles, Aria-Labels
  → ~240 Strings (alle restlichen user-facing Screens)
  → Fallback: Unuebersetzte Strings bleiben Englisch
```

### Dateien

| Datei | Typ | Beschreibung |
|-------|-----|-------------|
| `web/src/ext/i18n/translations.ts` | Dictionary | ~250 DE-Uebersetzungen |
| `web/src/ext/i18n/useTranslation.ts` | Hook | `t()` Funktion fuer Schicht 1 |
| `web/src/ext/i18n/TranslationProvider.tsx` | React Provider | MutationObserver fuer Schicht 2 |
| `web/src/ext/i18n/index.ts` | Re-Exports | |

### Core-Patches

| Core | Datei | Aenderung |
|------|-------|----------|
| #4 NEU | `layout.tsx` | TranslationProvider Wrapper + `lang="de"` (3 Stellen) |
| #6 | `constants.ts` | `UNNAMED_CHAT = "Neuer Chat"` |
| #8 | `LoginText.tsx` | `t()` Import + `t("Welcome to")` |
| #9 | `AuthFlowContainer.tsx` | `t()` Import + 4 String-Uebersetzungen |

### Zusaetzliche Merge-Stellen

| Datei | Aenderung | Risiko |
|-------|----------|--------|
| `web/Dockerfile` | ARG/ENV `NEXT_PUBLIC_EXT_I18N_ENABLED` in beiden Stages | Niedrig |
| `.github/workflows/stackit-deploy.yml` | Build-Arg `NEXT_PUBLIC_EXT_I18N_ENABLED=true` | Niedrig |

## 3. Feature Flag

| Variable | Scope | Default | Beschreibung |
|----------|-------|---------|-------------|
| `EXT_I18N_ENABLED` | Backend | `"false"` | Backend-Flag (AND-gated mit EXT_ENABLED) |
| `NEXT_PUBLIC_EXT_I18N_ENABLED` | Frontend | enabled wenn `!== "false"` | Client-seitiger Switch, Build-Arg |

## 4. Uebersetzungs-Abdeckung

| Bereich | Strings | Methode | Status |
|---------|---------|---------|--------|
| Login/Auth | ~30 | Schicht 0+1+2 | Deutsch |
| Chat-UI | ~15 | Schicht 0+1+2 | Deutsch |
| Sidebar | ~20 | Schicht 2 | Deutsch |
| User-Menu | ~5 | Schicht 2 | Deutsch |
| Agents (Liste + Erstellen) | ~30 | Schicht 2 | Deutsch |
| Projekte (Erstellen + Detail) | ~15 | Schicht 2 | Deutsch |
| Settings (User) | ~50 | Schicht 2 | Deutsch |
| Fehlermeldungen/Toasts | ~25 | Schicht 2 | Deutsch |
| Onboarding | ~5 | Schicht 2 | Deutsch |
| Admin-Bereich | 100+ | NICHT UEBERSETZT | Bewusst EN |
| **Gesamt User-facing** | **~250** | | **~95%** |

## 5. Wartung bei Upstream-Sync

### Checkliste

1. **Dictionary pruefen:** Haben sich Upstream-Strings geaendert?
   - Neue Strings identifizieren → Dictionary erweitern
   - Geaenderte Strings → Dictionary-Keys aktualisieren
2. **Core-Patches pruefen:** Koennen die 4 Patches noch angewendet werden?
3. **web/Dockerfile pruefen:** ARG/ENV noch vorhanden?
4. **CI/CD pruefen:** Build-Arg noch vorhanden?

### Geschaetzter Aufwand: ~1 Stunde pro Sync

## 6. Bekannte Einschraenkungen

- Strings mit Variablen muessen in Schicht 1 (t()-Calls) behandelt werden
- MutationObserver kann minimales Flackern verursachen (EN→DE, ~50ms)
- Neue Upstream-Strings erscheinen auf Englisch bis zum naechsten Dictionary-Update
- Sehr kurze/generische Strings ("Name", "Edit") koennten in unerwarteten Kontexten uebersetzt werden

## 7. Sicherheit

- Dictionary enthaelt keine sensitiven Daten
- Feature Flag deaktiviert alles sauber (Fallback auf EN)
- MutationObserver hat keinen Zugriff auf Netzwerk/Storage
- Kein XSS-Risiko (nur textContent + setAttribute, kein innerHTML)
- WeakSet verhindert Endlos-Loops

## 8. Analyse-Grundlage

Vollstaendige Analyse: `docs/analyse-lokalisierung-de.md`
