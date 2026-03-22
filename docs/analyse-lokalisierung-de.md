# Analyse: Lokalisierung Onyx → Deutsch

> **Datum:** 2026-03-20
> **Autor:** Claude Code (Opus 4.6 Max) im Auftrag von Nikolaj Ivanov
> **Projekt:** VÖB Chatbot — Entscheidungsgrundlage für Lokalisierung
> **Status:** Analyse abgeschlossen, Entscheidung offen

---

## 1. Ausgangslage

| Fakt | Detail |
|------|--------|
| **Plattform** | Onyx FOSS (ehemals Danswer), Next.js 15 / React 18 / TypeScript |
| **Sprache aktuell** | Englisch (komplett) |
| **Ziel** | Deutsche UI für ~150 VÖB-Mitarbeiter |
| **Upstream-Sync** | Alle 1-3 Monate, ~100-400 Commits pro Sync |
| **Core-Dateien-Limit** | 10 Dateien dürfen minimal gepatcht werden |
| **Bereits gepatcht** | 7 von 10 Core-Dateien (main.py, multi_llm.py, prompt_utils.py, constants.ts, LoginText.tsx, AuthFlowContainer.tsx, AdminSidebar.tsx) |
| **Ungepatcht** | layout.tsx (Core #4), access.py (Core #3), header/ (Core #5) |
| **Admin-Bereich** | Nur CCJ/Niko — kann Englisch bleiben |

### Kernfrage

Wie bringen wir die Onyx-UI auf Deutsch, **ohne bei jedem Upstream-Sync Merge-Konflikte zu erzeugen?**

---

## 2. i18n-Status von Onyx

### Ergebnis: **ZERO i18n-Infrastruktur**

| Prüfpunkt | Status | Evidenz |
|-----------|--------|---------|
| i18n-Libraries | ❌ KEINE | `package.json` hat 158 Dependencies, null i18n-Pakete |
| Translations-Dateien | ❌ KEINE | Keine `.json`/`.yaml` Locale-Dateien gefunden |
| i18n-Config | ❌ KEINE | `next.config.js` hat kein `i18n`-Feld |
| Locale-Routes | ❌ NEIN | Kein `/[locale]/`-Pattern in der App-Struktur |
| Hardcoded Strings | ✅ JA | ~200-250 englische Strings in ~848 `.tsx`-Dateien |
| Zentrale String-Datei | ❌ NEIN | Kein `strings.ts`, `messages.json`, `locales/` |
| Backend Locale API | ❌ NEIN | Kein `/api/locale` oder `/api/settings/language` |
| Environment Variable | ❌ NEIN | Kein `NEXT_PUBLIC_LANG`, `DEFAULT_LANGUAGE` |
| Text-Komponente | ❌ NEIN | `<Text>` hat keine `locale`- oder `key`-Props |

### Upstream-Position zu i18n

**Onyx hat i18n explizit abgelehnt** und zeigt null Interesse an Mehrsprachigkeit:

| # | Typ | Titel | Status | Detail |
|---|-----|-------|--------|--------|
| #984 | Issue | I18n - Localize | Stale-Closed | Erste Anfrage (Jan 2024). Keine Maintainer-Reaktion. |
| #1128 | Issue | Internationalization | Stale-Closed | Duplikat von #984. |
| #1129 | **PR** | i18n minimal infrastructure | **Explizit abgelehnt** | `i18next` + `react-i18next`, EN + IT. Maintainer: *"would slow down velocity... we cannot accept this."* |
| #2896-#3055 | PR (4x) | German translations | Alle Stale-Closed | @jastpexon: Vollständigstes i18next-Setup mit deutschen Übersetzungen. 4 Versuche, nie reviewt. |
| #3475 | PR | 1st i18n collaboration | Stale-Closed | `web/src/messages/en.json`-Ansatz. Nie reviewt. |
| #4530 | PR | Russian translation | Stale-Closed | Nie reviewt. |

**Zitat eines Community-Mitglieds (@mymro, Juli 2024):**
> *"We implemented it ourselves, but dropped it, because of the rebase conflicts."*

### Was Onyx an Multilingual-Support HAT (nur Search)

- `multilingual_expansion` — Suchanfragen in mehrere Sprachen übersetzen (DB-Setting)
- `VESPA_LANGUAGE_OVERRIDE` — Vespa-Linguistik auf eine Sprache festlegen (z.B. `de`)
- Multilingual Embedding/Reranker-Modelle (wir nutzen bereits Qwen3-VL-Embedding)

→ Diese Features betreffen die **Dokumentensuche**, nicht die UI.

---

## 3. String-Inventar

### 3a) User-Journey: Was sieht ein normaler VÖB-Mitarbeiter?

```
Login → Chat-Hauptseite → Sidebar → Gelegentlich: Einstellungen, Fehlermeldungen
        ↑ Hier verbringt der User 95% seiner Zeit
```

**Der Admin-Bereich wird NUR von CCJ/Niko genutzt und kann Englisch bleiben.**

### 3b) Strings nach Bildschirm

#### Login-Seite (~15 Strings)

| String | Datei | Status |
|--------|-------|--------|
| `"Welcome to {app_name}"` | `LoginText.tsx` (Core #8) | ✅ Bereits via ext-branding konfigurierbar |
| `{custom_header_content}` | `LoginText.tsx` (Core #8) | ✅ Bereits via ext-branding konfigurierbar |
| `"Sign In"` | `EmailPasswordForm.tsx` | ❌ Hardcoded |
| `"Email"` | `EmailPasswordForm.tsx` | ❌ Hardcoded |
| `"Password"` | `EmailPasswordForm.tsx` | ❌ Hardcoded |
| `"email@yourcompany.com"` | `EmailPasswordForm.tsx` | ❌ Hardcoded |
| `"New to {app_name}?"` | `AuthFlowContainer.tsx` (Core #9) | Bereits gepatcht |
| `"Create an Account"` | `AuthFlowContainer.tsx` (Core #9) | Bereits gepatcht |
| `"Already have an account?"` | `AuthFlowContainer.tsx` (Core #9) | Bereits gepatcht |
| `"Invalid email or password"` | `EmailPasswordForm.tsx` | ❌ Hardcoded |
| `"or continue as guest"` | `EmailPasswordForm.tsx` | ❌ Hardcoded |
| `"Forgot Password"` | `forgot-password/page.tsx` | ❌ Hardcoded |

#### Chat-UI (~10 Strings)

| String | Datei | Status |
|--------|-------|--------|
| `"How can I help?"` / `"Let's get started."` | `greetingMessages.ts` | ✅ Via `custom_greeting_message` (ext-branding) |
| `"How can I help you today?"` | `AppInputBar.tsx` | ❌ Hardcoded (Chat-Input-Placeholder) |
| `"Listening..."` | `AppInputBar.tsx` | ❌ Hardcoded (Voice-Modus) |
| `"Onyx is speaking..."` | `AppInputBar.tsx` | ❌ Hardcoded (Voice-Modus) |
| `"Search connected sources"` | `AppInputBar.tsx` | ❌ Hardcoded (Suchmodus) |
| `"New Chat"` | `constants.ts` (Core #6) | Bereits gepatcht (`UNNAMED_CHAT`) |
| Agent-Name | Dynamisch | ✅ Konfigurierbar (DB) |
| Starter-Messages | `constants.ts` | ❌ Hardcoded (4 Beispiel-Prompts) |

#### Sidebar (~10 Strings)

| String | Datei | Status |
|--------|-------|--------|
| `"New Chat"` | `constants.ts` (Core #6) | Bereits gepatcht |
| `"Search chat sessions, projects..."` | `ChatSearchCommandMenu.tsx` | ❌ Hardcoded |
| `"Share"` / `"Rename"` / `"Delete"` | `ChatButton.tsx` | ❌ Hardcoded |
| `"Move to Project"` | `ChatButton.tsx` | ❌ Hardcoded |
| `"Search Projects"` | `ChatButton.tsx` | ❌ Hardcoded |
| `"Delete Chat"` | Confirmation Dialog | ❌ Hardcoded |

#### User-Menü (~5 Strings)

| String | Datei | Status |
|--------|-------|--------|
| `"Settings"` | `UserAvatarPopover.tsx` | ❌ Hardcoded |
| `"Notifications"` | `UserAvatarPopover.tsx` | ❌ Hardcoded |
| `"Logout"` / `"Log out"` | `UserAvatarPopover.tsx` | ❌ Hardcoded |

#### Fehlermeldungen / Toasts (~15 Strings)

| String | Datei | Status |
|--------|-------|--------|
| `"Failed to delete chat..."` | Diverse | ❌ Hardcoded |
| `"An error occurred."` | Diverse | ❌ Hardcoded |
| `"Please try again."` | Diverse | ❌ Hardcoded |
| `"Too many requests..."` | Auth | ❌ Hardcoded |

### 3c) Zusammenfassung

| Kategorie | Geschätzt | Bereits konfigurierbar | Zu übersetzen |
|-----------|-----------|----------------------|---------------|
| Login/Auth | 15 | 3 (ext-branding) | **~12** |
| Chat-UI | 10 | 2 (ext-branding + constants) | **~8** |
| Sidebar | 10 | 1 (constants) | **~9** |
| User-Menü | 5 | 0 | **~5** |
| Fehlermeldungen | 15 | 0 | **~15** |
| Admin-Bereich | 100+ | — | **0** (bleibt EN) |
| Settings (User) | 20 | 0 | **~20** (niedrige Prio) |
| **Gesamt User-facing** | **~75** | **~6** | **~69** |
| **Priorität 1 (täglich sichtbar)** | **~35** | **~6** | **~29** |

**Kerninsight:** Nur ~29 Strings sind täglich sichtbar und noch nicht konfigurierbar. Das ist überraschend wenig.

---

## 4. Strategien (bewertet)

### Strategie A: Vollständiges i18n-Framework (next-intl / i18next)

Alle ~848 `.tsx`-Dateien refactoren, Strings durch Translation-Keys ersetzen, Locale-Dateien pflegen.

| Pro | Contra |
|-----|--------|
| Saubere Trennung (Strings ≠ Code) | **Jede `.tsx`-Datei muss geändert werden** |
| Sprachwechsel zur Laufzeit | **Massive Merge-Konflikte bei JEDEM Upstream-Sync** |
| Professionell, skalierbar | Community-Mitglied: *"dropped it because of rebase conflicts"* |
| | Upstream wird es nie übernehmen (explizit abgelehnt) |
| | Wochen initialer Aufwand |

### Strategie B: Runtime DOM-Manipulation (MutationObserver)

JavaScript-Layer der Text-Nodes im DOM zur Laufzeit ersetzt. Dictionary-Datei als Mapping.

| Pro | Contra |
|-----|--------|
| Keine Änderung an Upstream-Code | Visuelles Flackern (EN → DE) |
| Null Merge-Konflikte | Performance-Overhead (Observer auf jedem DOM-Change) |
| Dictionary als eigene Datei | Fragil: DOM-Änderungen können Mapping brechen |
| | React-Re-Renders überschreiben Übersetzungen |
| | Placeholders/Inputs schwer erreichbar |
| | Strings mit Variablen (`"Welcome to {name}"`) problematisch |

### Strategie C: Build-Time Patch-Dateien

Patch-Dateien die englische Strings bei Build/Deploy durch deutsche ersetzen.

| Pro | Contra |
|-----|--------|
| Keine Runtime-Kosten | Patches brechen bei Upstream-Änderungen |
| Sauberes Ergebnis | Hoher initialer Aufwand |
| | Patches nach jedem Sync prüfen + reparieren |
| | Hunderte Patches nötig |

### Strategie D: ext-i18n Modul (Zwei-Schichten-Ansatz)

Schicht 1: Direkte Übersetzung in bereits gepatchten Core-Dateien. Schicht 2: React Context + Hook für restliche Strings. Nur ext/-Dateien + 1 zusätzlicher Core-Patch.

| Pro | Contra |
|-----|--------|
| Dictionary in `web/src/ext/i18n/` → null Konflikte | 1 zusätzlicher Core-Patch (layout.tsx) |
| Inkrementell: Wichtigstes zuerst | Nicht-Core-Dateien nicht direkt patchbar |
| Nutzt bereits existierende Patches | Für ~20 Strings braucht man Component-Overrides |
| ext-branding-Infrastruktur wiederverwendbar | Gemischt-sprachig bis alles übersetzt |
| Upstream-unabhängig | |

### Strategie E: Onyx Enterprise Localization

**Existiert NICHT.** Weder FOSS noch Enterprise hat Lokalisierung. Kein Language-Setting in Admin.

### Strategie F: Pragmatisch — Nur die sichtbarsten Strings

Nur die ~29-35 täglich sichtbaren Strings übersetzen. Login, Chat-Greeting, Sidebar-Labels. Rest bleibt Englisch.

| Pro | Contra |
|-----|--------|
| Minimaler Aufwand (1-2 Tage) | Nicht vollständig |
| Wenig Merge-Konflikte | Gemischt-sprachig |
| 80/20: Chat-UI dominiert die Nutzung | Kann im Banking-Umfeld unprofessionell wirken |
| Inkrementell erweiterbar | |

### Bewertungsmatrix

| Kriterium | Gewicht | A (i18n) | B (Runtime) | C (Patch) | D (ext-i18n) | E (Enterprise) | F (Pragmatisch) |
|-----------|---------|----------|-------------|-----------|--------------|----------------|-----------------|
| Initialer Aufwand | 20% | 1 | 3 | 2 | 4 | — | **5** |
| Merge-Konflikte | 30% | 1 | **5** | 2 | **4** | — | **4** |
| Wartungsaufwand | 20% | 1 | 2 | 2 | **4** | — | **5** |
| Vollständigkeit | 15% | **5** | 3 | 4 | 4 | — | 2 |
| Professionalität | 15% | **5** | 2 | 4 | 4 | — | 3 |
| **Gewichteter Score** | | **2.2** | **3.2** | **2.6** | **4.0** | — | **4.0** |

**Strategie D und F sind gleichauf.** Die optimale Lösung kombiniert beide.

---

## 5. Empfehlung: Hybrid D+F — ext-i18n Modul (pragmatisch)

### Warum

1. **29 täglich sichtbare Strings** sind das Minimum das Deutsch sein muss — Banking-Umfeld, 150 nicht-technische Mitarbeiter
2. **ext-branding deckt bereits ~6 Strings ab** (App-Name, Greeting, Login-Texte)
3. **7 Core-Dateien sind bereits gepatcht** — dort können wir Übersetzungen einfügen ohne zusätzliche Merge-Konflikte
4. **1 neuer Core-Patch** (layout.tsx, Core #4) für den TranslationProvider — vertretbar
5. **Admin bleibt Englisch** — nur CCJ/Niko, kein VÖB-Mitarbeiter sieht das
6. **Upstream wird nie i18n haben** — wir müssen unabhängig sein

### Architektur: Zwei-Schichten-Übersetzung

```
┌─────────────────────────────────────────────────────────────┐
│  Schicht 1: Direkte Übersetzung (in gepatchten Core-Dateien)│
│  ─────────────────────────────────────────────────────────── │
│  • t("Sign In") → "Anmelden"                               │
│  • Import von @/ext/i18n/translations                       │
│  • In: LoginText.tsx, AuthFlowContainer.tsx, constants.ts   │
│  • Kein Flackern, kein Performance-Overhead                 │
│  • Deckt ~15 der 29 Prio-1-Strings ab                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Schicht 2: TranslationProvider (DOM-basiert, Fallback)     │
│  ─────────────────────────────────────────────────────────── │
│  • React Context in layout.tsx (Core #4)                    │
│  • MutationObserver für dynamisch gerenderte Strings        │
│  • Übersetzt Placeholders, Tooltips, Aria-Labels            │
│  • Deckt ~14 weitere Prio-1-Strings ab                     │
│  • Fallback: Unübersetzte Strings bleiben Englisch          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Schicht 0: ext-branding (bereits vorhanden)                │
│  ─────────────────────────────────────────────────────────── │
│  • application_name → "VÖB Chatbot"                        │
│  • custom_greeting_message → "Wie kann ich helfen?"         │
│  • custom_header_content → Deutsche Tagline                 │
│  • Deckt ~6 Strings ab                                      │
└─────────────────────────────────────────────────────────────┘
```

### Dateien im ext/-Ordner (ZERO Merge-Konflikte)

```
web/src/ext/i18n/
  translations.ts        ← Deutsches Dictionary (~100 Einträge)
  TranslationProvider.tsx ← React Context + MutationObserver
  useTranslation.ts      ← Hook: t(key) → deutscher String
  index.ts               ← Re-Exports
```

### Core-Datei-Änderungen

| Core-Datei | Bereits gepatcht | Neue Änderung |
|-----------|-----------------|---------------|
| `constants.ts` (Core #6) | ✅ Ja | `UNNAMED_CHAT = "Neuer Chat"` statt `"New Chat"` |
| `LoginText.tsx` (Core #8) | ✅ Ja | `t("Welcome to")` Import hinzufügen |
| `AuthFlowContainer.tsx` (Core #9) | ✅ Ja | `t("New to")`, `t("Create an Account")` etc. |
| `layout.tsx` (Core #4) | ❌ Nein | **NEU:** `<TranslationProvider>` Wrapper (1 Import + 1 Tag) |

**Insgesamt:** 3 bestehende Patches erweitern + 1 neuer Patch. Alle im Rahmen der 10 erlaubten Core-Dateien.

### Aufwand

| Phase | Aufwand | Ergebnis |
|-------|---------|----------|
| Dictionary erstellen | 0,5 Tage | `translations.ts` mit ~100 DE-Strings |
| TranslationProvider | 0,5 Tage | Context + MutationObserver |
| Core-Patches erweitern | 0,5 Tage | 3 bestehende + 1 neuer Patch |
| Testen + Feinschliff | 0,5 Tage | Visueller Check aller Screens |
| **Gesamt Initial** | **~2 Tage** | **~80% der User-facing UI auf Deutsch** |
| Pro Upstream-Sync | ~1 Stunde | Dictionary prüfen, neue Strings nachführen |
| Wartung laufend | ~0 | Dictionary-Datei in ext/ hat keine Konflikte |

### Was bleibt Englisch (bewusst)

- **Admin-Bereich** komplett (nur CCJ/Niko)
- **Connector-Konfiguration** (Admin)
- **API-Keys / Integrations** (Admin)
- **Technische Fehlermeldungen** in der Konsole
- **Seltene Edge-Cases** (Deep Settings, Advanced Config)
- **LLM-Responses**: Bereits Deutsch (LLM antwortet in der Sprache der Frage + System Prompt)

---

## 6. Umsetzungsplan

### Phase 1: Dictionary + Provider (1 Tag)

```
1. Feature-Branch: git checkout -b feature/ext-i18n
2. Dictionary erstellen: web/src/ext/i18n/translations.ts
3. useTranslation Hook: web/src/ext/i18n/useTranslation.ts
4. TranslationProvider: web/src/ext/i18n/TranslationProvider.tsx
5. Feature Flag: EXT_I18N_ENABLED in backend/ext/config.py
```

### Phase 2: Core-Patches (0,5 Tage)

```
6. constants.ts (Core #6): UNNAMED_CHAT → "Neuer Chat"
7. LoginText.tsx (Core #8): t() Import + "Willkommen bei"
8. AuthFlowContainer.tsx (Core #9): t() für alle Strings
9. layout.tsx (Core #4): <TranslationProvider> Wrapper
10. Patches aktualisieren: _core_originals/*.patch
```

### Phase 3: Test + Erweiterung (0,5 Tage)

```
11. Visueller Check: Login → Chat → Sidebar → User-Menü
12. Dictionary erweitern für Schicht-2-Strings
13. Placeholder-Übersetzungen testen (Input-Felder)
14. Error-Toast-Übersetzungen verifizieren
```

### Phase 4: Deploy + Dokumentation

```
15. Modulspezifikation: docs/technisches-feinkonzept/ext-i18n.md
16. Helm Values: EXT_I18N_ENABLED=true
17. Deploy auf DEV
18. CHANGELOG.md aktualisieren
```

---

## 7. Beispiel-Code (Skizze)

### 7a) Dictionary (`web/src/ext/i18n/translations.ts`)

```typescript
/**
 * Deutsches Übersetzungs-Dictionary für VÖB Chatbot.
 * Fallback: Wenn ein Key nicht gefunden wird, bleibt der englische Text stehen.
 */
export const DE_TRANSLATIONS: Record<string, string> = {
  // === Login / Auth ===
  "Sign In": "Anmelden",
  "Create Account": "Konto erstellen",
  "Create an Account": "Konto erstellen",
  "Already have an account?": "Bereits ein Konto?",
  "Email": "E-Mail",
  "Password": "Passwort",
  "email@yourcompany.com": "email@example.com",
  "Invalid email or password": "Ungültige E-Mail oder Passwort",
  "or continue as guest": "oder als Gast fortfahren",
  "Forgot Password": "Passwort vergessen",
  "Reset Password": "Passwort zurücksetzen",
  "Back to Login": "Zurück zur Anmeldung",

  // === Chat UI ===
  "How can I help you today?": "Wie kann ich Ihnen helfen?",
  "Listening...": "Ich höre zu...",
  "Search connected sources": "Verbundene Quellen durchsuchen",
  "New Chat": "Neuer Chat",

  // === Sidebar ===
  "Search chat sessions, projects...": "Chats und Projekte suchen...",
  "Share": "Teilen",
  "Rename": "Umbenennen",
  "Delete": "Löschen",
  "Move to Project": "In Projekt verschieben",
  "Search Projects": "Projekte suchen",
  "Delete Chat": "Chat löschen",
  "Are you sure you want to delete this chat? This action cannot be undone.":
    "Möchten Sie diesen Chat wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.",

  // === User-Menü ===
  "Settings": "Einstellungen",
  "Notifications": "Benachrichtigungen",
  "Logout": "Abmelden",
  "Log out": "Abmelden",
  "Profile": "Profil",

  // === Allgemein ===
  "Cancel": "Abbrechen",
  "Save": "Speichern",
  "Submit": "Absenden",
  "Close": "Schließen",
  "Back": "Zurück",
  "Next": "Weiter",
  "Loading...": "Wird geladen...",
  "No data available": "Keine Daten verfügbar",

  // === Fehlermeldungen ===
  "An error occurred.": "Ein Fehler ist aufgetreten.",
  "Please try again.": "Bitte versuchen Sie es erneut.",
  "Too many requests. Please try again later.":
    "Zu viele Anfragen. Bitte versuchen Sie es später erneut.",
  "Failed to delete chat. Please try again.":
    "Chat konnte nicht gelöscht werden. Bitte versuchen Sie es erneut.",
};
```

### 7b) Hook (`web/src/ext/i18n/useTranslation.ts`)

```typescript
import { DE_TRANSLATIONS } from "./translations";

// Feature Flag Check (server-side env)
const I18N_ENABLED =
  process.env.NEXT_PUBLIC_EXT_I18N_ENABLED?.toLowerCase() === "true";

/**
 * Übersetzt einen englischen String ins Deutsche.
 * Fallback: Gibt den Original-String zurück wenn keine Übersetzung existiert.
 */
export function t(text: string): string {
  if (!I18N_ENABLED) return text;
  return DE_TRANSLATIONS[text] ?? text;
}
```

### 7c) TranslationProvider (Schicht 2 — DOM-basiert)

```typescript
"use client";

import { useEffect } from "react";
import { DE_TRANSLATIONS } from "./translations";

const I18N_ENABLED =
  process.env.NEXT_PUBLIC_EXT_I18N_ENABLED?.toLowerCase() === "true";

export function TranslationProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!I18N_ENABLED) return;

    const translateNode = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent?.trim();
        if (text && DE_TRANSLATIONS[text]) {
          node.textContent = node.textContent!.replace(text, DE_TRANSLATIONS[text]);
        }
      }
    };

    const translateElement = (element: Element) => {
      // Text-Nodes
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) translateNode(walker.currentNode);

      // Placeholders
      element.querySelectorAll("[placeholder]").forEach((el) => {
        const val = el.getAttribute("placeholder");
        if (val && DE_TRANSLATIONS[val]) el.setAttribute("placeholder", DE_TRANSLATIONS[val]);
      });

      // Titles / Aria-Labels
      ["title", "aria-label"].forEach((attr) => {
        element.querySelectorAll(`[${attr}]`).forEach((el) => {
          const val = el.getAttribute(attr);
          if (val && DE_TRANSLATIONS[val]) el.setAttribute(attr, DE_TRANSLATIONS[val]);
        });
      });
    };

    // Initial
    translateElement(document.body);

    // Dynamische Inhalte (React Re-Renders)
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.TEXT_NODE) translateNode(node);
          if (node.nodeType === Node.ELEMENT_NODE) translateElement(node as Element);
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return <>{children}</>;
}
```

### 7d) Core-Patch Beispiel: layout.tsx (Core #4)

```diff
+ import { TranslationProvider } from "@/ext/i18n";

  // ... in der return-Anweisung von RootLayout:
  <ThemeProvider ...>
    <TooltipProvider>
+     <TranslationProvider>
        <AppProvider ...>
          {children}
        </AppProvider>
+     </TranslationProvider>
    </TooltipProvider>
  </ThemeProvider>
```

**Merge-Risiko:** Minimal — `layout.tsx` ändert sich selten strukturell, und unser Patch ist 3 Zeilen (1 Import + 2 Tags).

---

## 8. Merge-Konflikt-Profil

| Datei | Ort | Neue Zeilen | Konflikt-Risiko |
|-------|-----|-------------|-----------------|
| `web/src/ext/i18n/translations.ts` | ext/ | ~100 | **ZERO** (Upstream hat kein ext/) |
| `web/src/ext/i18n/TranslationProvider.tsx` | ext/ | ~50 | **ZERO** |
| `web/src/ext/i18n/useTranslation.ts` | ext/ | ~15 | **ZERO** |
| `constants.ts` (Core #6) | Bereits gepatcht | +0 (Wert ändern) | **Niedrig** |
| `LoginText.tsx` (Core #8) | Bereits gepatcht | +2 (Import + t()) | **Niedrig** |
| `AuthFlowContainer.tsx` (Core #9) | Bereits gepatcht | +5 (Import + t()-Calls) | **Niedrig** |
| `layout.tsx` (Core #4) | **Neuer Patch** | +3 (Import + Tags) | **Niedrig** |

**Gesamtes Merge-Profil:** 4 Core-Patches (3 bestehende erweitert + 1 neuer) + 3 ext/-Dateien = **Vernachlässigbar** im Vergleich zu Strategie A (848 Datei-Änderungen).

---

## 9. Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Schicht 2 (DOM) erzeugt Flackern | Mittel | Schicht 1 deckt die wichtigsten Strings direkt ab; DOM-Observer nur für Randstrings |
| MutationObserver Performance | Niedrig | Observer ist O(n) auf addedNodes, nicht auf gesamtes DOM. Chat-UI hat wenig DOM-Churn |
| Upstream ändert String-Text | Mittel | Dictionary-Key matcht nicht mehr → String bleibt Englisch (graceful Fallback) |
| React Re-Renders überschreiben | Niedrig | Observer fängt Re-Renders ab (childList + subtree) |
| False-Positive-Ersetzungen | Niedrig | Nur exakte String-Matches, keine Substring-Ersetzung |
| Neue Upstream-Strings | Sicher | Fallback auf Englisch, kein Crash. Bei Sync: Dictionary erweitern |

---

## 10. Alternative: Reiner Schicht-1-Ansatz (ohne DOM-Observer)

Falls Schicht 2 (DOM-Manipulation) als zu riskant bewertet wird, ist auch ein **reiner Schicht-1-Ansatz** möglich:

- Nur die bereits gepatchten Core-Dateien übersetzen
- **Kein** TranslationProvider, **kein** layout.tsx-Patch
- Ergebnis: ~20 der 29 Prio-1-Strings auf Deutsch
- Rest (Sidebar-Kontextmenü, User-Menü, Error-Toasts) bleibt Englisch
- Aufwand: ~1 Tag statt 2

**Nachteil:** "Settings", "Notifications", "Logout" im User-Menü bleiben Englisch — sichtbar, aber vertretbar.

---

## 11. Entscheidungsmatrix für Niko

| Option | Aufwand | Abdeckung | Merge-Risiko | Empfehlung |
|--------|---------|-----------|-------------|------------|
| **A: Nichts tun** | 0 | 0% | 0 | Nur wenn VÖB Englisch akzeptiert |
| **B: Nur ext-branding** (Status quo) | 0 | ~20% (6/29) | 0 | Minimum, bereits done |
| **C: Schicht 1 only** (Core-Patches) | 1 Tag | ~70% (20/29) | Niedrig | Guter Kompromiss |
| **D: Schicht 1+2** (empfohlen) | 2 Tage | ~90% (26/29) | Niedrig | Professionellstes Ergebnis |
| **E: Volles i18n-Framework** | 2+ Wochen | 100% | **Hoch** | Nicht empfohlen (Merge-Hölle) |

**Meine Empfehlung: Option D (Schicht 1+2).** 2 Tage Aufwand für 90% Abdeckung bei minimalem Merge-Risiko. Banking-tauglich.

---

## Anhang A: Referenz — Community i18n-Versuche

| PR | Autor | Ansatz | Schicksal |
|----|-------|--------|-----------|
| #1129 | @giova23 | `i18next` + `react-i18next` + `[locale]` Routes | **Explizit abgelehnt** durch Maintainer |
| #2896-#3055 | @jastpexon | Vollstes Setup: `i18next`, `web/src/locales/`, EN+DE | 4x Stale-Closed, nie reviewt |
| #3475 | @johnfelipe | `web/src/messages/en.json` | Stale-Closed |
| #4530 | @Camelot22rus | Russisch | Stale-Closed |

**Lesson Learned der Community:** i18n per Framework = Rebase-Konflikte bei jedem Upstream-Sync.

## Anhang B: Bereits konfigurierbare Strings (ext-branding)

| Setting | DB-Feld | Beispielwert |
|---------|---------|-------------|
| App-Name | `application_name` | "VÖB Chatbot" |
| Login-Tagline | `custom_header_content` | "Ihre KI-Plattform für..." |
| Chat-Greeting | `custom_greeting_message` | "Wie kann ich Ihnen helfen?" |
| Logo | `use_custom_logo` | true |
| Popup-Text | `custom_popup_header` / `custom_popup_content` | Deutsch |
| Disclaimer | `enable_consent_screen` + Texte | Deutsch |

## Anhang C: Onyx Multilingual-Search (bereits nutzbar)

Unabhängig von der UI-Übersetzung können wir die Suche in deutschen Dokumenten verbessern:

```yaml
# Helm Values oder Admin-UI:
VESPA_LANGUAGE_OVERRIDE: "de"              # Vespa-Linguistik auf Deutsch
multilingual_expansion: ["de", "en"]       # Suchanfragen in DE+EN expandieren
# Embedding: Qwen3-VL-Embedding 8B (bereits aktiv, multilingual)
```
