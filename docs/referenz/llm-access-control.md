# LLM Access Control — SOLL-Konzept

> **SSOT** fuer LLM-Zugriffssteuerung im VÖB Chatbot.
> Letzte Aktualisierung: 2026-03-24
> Basis: [Audit 2026-03-24](../audit/2026-03-24-llm-access-control-audit.md)

---

## 1. Uebersicht

### Konzept: Abteilungs-basierte Modellzuweisung

Jede VÖB-Abteilung bekommt gezielt die LLM-Modelle zugewiesen, die sie fuer ihre Arbeit braucht. Nicht jeder sieht alles — jede Abteilung sieht nur die fuer sie freigegebenen Modelle.

### Architektur-Pattern: 1:1 Provider-Modell-Mapping

Onyx steuert Zugriff auf **Provider-Ebene**. Um modellgranulare Steuerung zu erreichen, wird jedes Modell als eigener Provider angelegt — mit denselben API-Credentials, aber eigenem Access-Control-Setting:

```
Provider "GPT-OSS 120B"   → 1 Modell → Gruppen: Marketing, Vertrieb, ...
Provider "Qwen3-VL 235B"  → 1 Modell → Gruppen: Research, Fachabteilungen, ...
Provider "Llama 3.3 70B"  → 1 Modell → is_public=true (Basis fuer alle)
Provider "Claude"          → 1 Modell → Gruppen: Entwicklung (eigene API, Anthropic)
```

### Prinzipien

1. **1 Provider = 1 Modell** — Ermoeglicht modellgranulare Zugriffssteuerung
2. **Gruppen = Abteilungen** — Mapping auf VÖB-Organisationsstruktur
3. **Ein Basis-Modell fuer alle** — Mindestens ein Provider bleibt `is_public=true`
4. **Graceful Fallback** — Kein Zugriff auf Persona-Provider → stiller Fallback auf Basis-Modell
5. **Externe Provider nur fuer berechtigte Gruppen** — Andere DPAs, andere Compliance-Anforderungen

---

## 2. Provider-Matrix (SOLL)

### 2.1 StackIT-Modelle (gemeinsame API-Credentials)

| Provider-Name | Modell-ID | `is_public` | Zugewiesene Gruppen | Zweck |
|---------------|-----------|-------------|---------------------|-------|
| **Llama 3.3 70B** | `cortecs/Llama-3.3-70B-Instruct-FP8-Dynamic` | `true` | — (alle User) | Basis-Modell. Schnell, 128K Context, Tool Calling. Fuer allgemeine Fragen. |
| **GPT-OSS 120B** | `openai/gpt-oss-120b` | `false` | _[Abteilungen laut VÖB]_ | Bestes Reasoning. 131K Context. Fuer anspruchsvolle Analyse-Aufgaben. |
| **Qwen3-VL 235B** | `Qwen/Qwen3-VL-235B-A22B-Instruct-FP8` | `false` | _[Abteilungen laut VÖB]_ | Groesstes Context-Fenster (218K). Multi-Modal (Vision). Fuer lange Dokumente, Bild-Analyse. |

**Gemeinsame Konfiguration:**

| Parameter | Wert |
|-----------|------|
| API Base | `https://api.openai-compat.model-serving.eu01.onstackit.cloud/v1` |
| API Key | StackIT AI Model Serving Token (identisch fuer alle StackIT-Provider) |
| Region | EU01 Frankfurt (BSI C5 Type 2) |

### 2.2 Externe Provider (eigene API-Credentials)

| Provider-Name | Modell-ID | `is_public` | Zugewiesene Gruppen | API | Zweck |
|---------------|-----------|-------------|---------------------|-----|-------|
| **Claude** _(Beispiel)_ | z.B. `claude-sonnet-4-6` | `false` | Entwicklung | Anthropic API | Claude Code, technische Entwicklung. Eigene DPA (Anthropic). |

> **Hinweis:** Externe Provider haben andere Datenschutzvereinbarungen als StackIT. Die Gruppenzuweisung muss das beruecksichtigen — nicht jede Abteilung darf Daten an externe Provider senden.

### 2.3 Embedding (nicht zugriffskontrolliert)

| Modell | Provider | Status |
|--------|----------|--------|
| Qwen3-VL-Embedding 8B | LiteLLM (Model Server) | ✅ Aktiv DEV+PROD. Laeuft im Model-Server, nicht ueber LLM-Provider. Nicht zugriffskontrolliert. |

---

## 3. Abteilungs-Gruppen (SOLL)

### 3.1 Gruppen-Design

Gruppen entsprechen VÖB-Abteilungen. Die konkrete Abteilungsliste muss von VÖB kommen.

| Gruppe | Modell-Zugriff | Sync-Quelle | Bemerkung |
|--------|---------------|-------------|-----------|
| _[Alle Mitarbeiter]_ | Llama 3.3 70B (public) | Automatisch | Kein expliziter Link noetig — public Provider |
| _[Abteilung A, z.B. Marketing]_ | + GPT-OSS 120B | ext-rbac (manuell) | Beispiel: Marketing braucht starkes Reasoning |
| _[Abteilung B, z.B. Research]_ | + Qwen3-VL 235B | ext-rbac (manuell) | Beispiel: Research braucht langes Context-Fenster |
| _[Abteilung C, z.B. Entwicklung]_ | + Claude | ext-rbac (manuell) | Beispiel: Entwickler brauchen Claude fuer Code |
| _[Abteilung D, z.B. Vorstand]_ | + GPT-OSS + Qwen3-VL | ext-rbac (manuell) | Beispiel: Zugriff auf mehrere Modelle |
| System-Admin | Alle Provider | Onyx ADMIN-Rolle | Admins umgehen Gruppen automatisch |

> **Offen:** Konkrete Abteilungsliste + Modell-Zuordnung von VÖB anfordern. Bis dahin sind die obigen Beispiele Platzhalter.

### 3.2 Gruppen-zu-Provider-Mapping (Beispiel)

```
Alle Mitarbeiter ──→ Llama 3.3 70B (public, automatisch)
Marketing ─────────→ Llama 3.3 + GPT-OSS 120B
Research ──────────→ Llama 3.3 + Qwen3-VL 235B
Entwicklung ───────→ Llama 3.3 + Claude
Vorstand ──────────→ Llama 3.3 + GPT-OSS + Qwen3-VL
System-Admin ──────→ Alle (Admin-Bypass)
```

Ein User kann in **mehreren Gruppen** sein → sieht die Vereinigung aller Provider seiner Gruppen.

### 3.3 Entra ID Integration (Zukunft)

| Phase | Beschreibung | Status |
|-------|-------------|--------|
| Aktuell | Manuelle Gruppenzuweisung via ext-rbac Admin-UI (`/admin/ext-groups`) | ✅ Verfuegbar |
| Geplant | Entra ID `groups` Claim → automatisches Gruppen-Mapping | ⏳ Abhaengig von VÖB Entra-ID-Konfiguration |
| Spaeter | Microsoft Graph API → vollstaendige Gruppen-Synchronisation | ⏳ Abhaengig von VÖB Genehmigung |

---

## 4. Agent/Persona-Strategie (SOLL)

### 4.1 Standard-Konfiguration

| Persona | LLM-Override | `is_public` | Zielgruppe | Zweck |
|---------|-------------|-------------|------------|-------|
| Default Assistant | Keiner (nutzt User's Provider-Auswahl) | `true` | Alle | Allgemeine Fragen, Dokumentensuche |

### 4.2 Optionale Erweiterungen (bei Bedarf)

Personas koennen ein festes Modell erzwingen (LLM-Override). User ohne Zugriff auf den Provider des Modells fallen still auf das Basis-Modell zurueck.

| Persona | LLM-Override | `is_public` | Zielgruppe | Zweck |
|---------|-------------|-------------|------------|-------|
| Recherche-Agent | Qwen3-VL 235B Provider | `true` | Alle (Fallback fuer User ohne Qwen-Zugriff) | Tiefgehende Dokumentenanalyse |
| Code-Agent | Claude Provider | `false` | Entwicklung | Code-Review, technische Analyse |

### 4.3 Persona-Whitelisting (Agent Restriction)

Zusaetzlich zu Gruppen-Restrictions koennen Provider auf bestimmte Personas eingeschraenkt werden. Beispiel: Claude-Provider NUR ueber den Code-Agent nutzbar, nicht im freien Chat.

> **Aktuell nicht noetig.** Wird erst implementiert wenn konkrete Use Cases vorliegen.

---

## 5. Access Decision Matrix

### 5.1 Entscheidungslogik (implementiert in `can_user_access_llm_provider()`)

```
User sendet Nachricht mit Persona
        │
        ▼
┌─ Hat Provider Persona-Restrictions? ─┐
│                                       │
│  JA: Ist Persona in Whitelist?        │
│       NEIN → ZUGRIFF VERWEIGERT       │
│       JA → weiter ↓                   │
│                                       │
│  NEIN → weiter ↓                      │
└───────────────────────────────────────┘
        │
        ▼
┌─ Ist Provider public? ───────────────┐
│                                       │
│  JA → ZUGRIFF GEWAEHRT               │
│                                       │
│  NEIN → weiter ↓                      │
└───────────────────────────────────────┘
        │
        ▼
┌─ Hat Provider Gruppen-Restrictions? ──┐
│                                       │
│  JA: Ist User in erlaubter Gruppe     │
│      ODER Admin?                      │
│       JA → ZUGRIFF GEWAEHRT          │
│       NEIN → ZUGRIFF VERWEIGERT      │
│                                       │
│  NEIN: Ist User Admin?               │
│       JA → ZUGRIFF GEWAEHRT          │
│       NEIN → ZUGRIFF VERWEIGERT      │
└───────────────────────────────────────┘
```

### 5.2 Fallback-Verhalten

Wenn ein User keinen Zugriff auf den LLM-Provider seiner Persona hat:
- **Kein Fehler** — Chat funktioniert weiter
- **Stiller Fallback** auf den Default-Provider (public, Basis-Modell)
- User bemerkt ggf. anderes Modell, erhaelt aber keine Fehlermeldung

### 5.3 Sichtbarkeit

- Private Provider sind **komplett unsichtbar** fuer User ohne Zugriff
- Gilt in: Agent-Editor, Chat-UI Model Selector, API-Responses
- Admins sehen alle Provider (umgehen Gruppen), aber NICHT Persona-restricted Provider ohne passende Persona
- User sieht nur: Public Provider + Provider seiner Gruppen

### 5.4 Beispiel

Marketing-Mitarbeiter oeffnet den Chat und sieht im Model Selector:
- ✅ Llama 3.3 70B (public)
- ✅ GPT-OSS 120B (Marketing-Gruppe hat Zugriff)
- ❌ Qwen3-VL 235B (unsichtbar — nur Research)
- ❌ Claude (unsichtbar — nur Entwicklung)

---

## 6. Kosten-Kontrolle

### 6.1 Bestehende Mechanismen

| Mechanismus | Modul | Status |
|-------------|-------|--------|
| Per-User Token Tracking | ext-token | ✅ Aktiv |
| Per-User Token Limits | ext-token | ✅ Konfigurierbar |
| Per-Model Usage Dashboard | ext-token | ✅ Aktiv |
| Provider-basierte Zugriffskontrolle | Onyx FOSS (nativ) | ⏳ Noch nicht konfiguriert |

### 6.2 Kosten-Steuerung durch Abteilungs-Zuweisung

Durch die abteilungs-basierte Modellzuweisung wird der Kostenkreis automatisch eingeschraenkt:
- Teure Modelle (235B) nur fuer Abteilungen die sie brauchen
- Externe Provider (Claude) nur fuer berechtigte Abteilungen
- ext-token trackt den Verbrauch per User und Modell — Kostentransparenz

> **StackIT Pricing:** Alle StackIT-Modelle laufen ueber denselben Endpoint. Kosten korrelieren mit Modellgroesse und Token-Verbrauch. Exakte Preise: StackIT Service Portal. Externe Provider haben eigene Preismodelle.

---

## 7. Compliance-Aspekte

### 7.1 Provider-Klassifizierung

| Provider-Typ | DPA | Datenstandort | Compliance |
|-------------|-----|---------------|------------|
| StackIT AI Model Serving | StackIT DPA (BSI C5 Type 2) | EU01 Frankfurt | ✅ DSGVO-konform, deutsche Cloud |
| Externe Provider (z.B. Anthropic) | Eigene DPA pro Provider | Variiert | ⚠️ Separate DSGVO-Pruefung noetig |

### 7.2 Regel

**Externe Provider duerfen nur Abteilungen zugewiesen werden, die explizit fuer die Nutzung freigegeben sind.** Die Freigabe muss die DPA des jeweiligen Providers beruecksichtigen.

---

## 8. Implementierungsreihenfolge

### Phase 1: Provider-Split (UI-Konfiguration, kein Code)

1. Aktuellen Provider aufloesen → 3 einzelne Provider anlegen (1:1 Modell-Mapping)
2. Fuer jeden Provider: Gleiche API-Credentials (StackIT Token + API Base)
3. Basis-Modell (z.B. Llama 3.3 70B) auf `is_public=true` belassen
4. Andere Provider auf `is_public=false` setzen

### Phase 2: Abteilungs-Gruppen + Zuweisung

5. Abteilungsliste von VÖB einholen
6. Gruppen in ext-rbac anlegen (`/admin/ext-groups`)
7. Provider → User Group Access pro Abteilung zuweisen
8. Validierung als Nicht-Admin-User

### Phase 3: Externe Provider (optional)

9. Neuen Provider fuer Claude/Anthropic anlegen (eigene API-Credentials)
10. `is_public=false`, nur Entwickler-Gruppe zuweisen
11. DPA-Pruefung sicherstellen

### Phase 4: Dokumentation + Monitoring

12. Dieses Dokument als SSOT pflegen
13. Sicherheitskonzept aktualisieren
14. ext-token Dashboard auf abteilungs-basierte Auswertung pruefen

---

## 9. Offene Punkte

| # | Punkt | Wartet auf |
|---|-------|-----------|
| 1 | Konkrete VÖB-Abteilungsliste | VÖB |
| 2 | Welche Abteilung braucht welches Modell? | VÖB / Niko |
| 3 | Soll Claude als externer Provider angebunden werden? | Niko |
| 4 | Entra ID `groups` Claim verfuegbar? | VÖB IT |
| 5 | DPA fuer externe Provider (Anthropic, etc.) | VÖB Datenschutz |

---

## 10. Aenderungshistorie

| Datum | Autor | Aenderung |
|-------|-------|-----------|
| 2026-03-24 | Claude Code (Opus) / Nikolaj Ivanov | Initiales SOLL-Konzept: Abteilungs-basierte Modellzuweisung statt Tier-Modell |
