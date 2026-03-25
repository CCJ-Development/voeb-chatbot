# LLM Access Control Audit — 2026-03-24

**Auditor:** Nikolaj Ivanov (CCJ)
**Scope:** LLM-Provider-Zugriffssteuerung im VÖB Chatbot
**Basis:** Onyx FOSS Codebase (Commit `48ea1b0db`), Helm Values, ext-Konfiguration

---

## 1. IST-Zustand

### 1.1 LLM-Provider-Konfiguration

| Eigenschaft | Wert |
|-------------|------|
| Anzahl Provider | **1** (StackIT AI Model Serving) |
| Provider-Typ | `openai` (OpenAI-kompatibler Endpoint) |
| API Base | `https://api.openai-compat.model-serving.eu01.onstackit.cloud/v1` |
| API Key | StackIT AI Model Serving Token (K8s Secret) |
| `is_public` | **`true`** (Default) |
| User Group Restrictions | **Keine** (leer) |
| Agent/Persona Restrictions | **Keine** (leer) |

**Modelle pro Environment:**

| Modell | Model-ID | Context | DEV | PROD |
|--------|----------|---------|-----|------|
| GPT-OSS 120B | `openai/gpt-oss-120b` | 131K | ✅ | ✅ |
| Qwen3-VL 235B | `Qwen/Qwen3-VL-235B-A22B-Instruct-FP8` | 218K | ✅ | ✅ |
| Llama 3.3 70B | `cortecs/Llama-3.3-70B-Instruct-FP8-Dynamic` | 128K | ✅ | ✅ |
| Llama 3.1 8B | `neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8` | 128K | ✅ | ❌ |

> **Architektur-Einschraenkung:** Alle Modelle laufen auf **einem einzelnen Provider**. Onyx Access Control operiert auf **Provider-Ebene**, nicht auf Modell-Ebene. Fuer modellgranulare Zugriffssteuerung muss jedes Modell als eigener Provider angelegt werden (1:1 Mapping).

### 1.2 User-Gruppen (ext-rbac)

| Eigenschaft | Wert |
|-------------|------|
| ext-rbac aktiv | ✅ (`EXT_RBAC_ENABLED=true`) |
| Onyx UserGroup Tabelle | Vorhanden (FOSS) |
| `LLMProvider__UserGroup` Tabelle | Vorhanden (FOSS), **leer** |
| `LLMProvider__Persona` Tabelle | Vorhanden (FOSS), **leer** |
| Gruppen angelegt | **DB-Verifikation noetig** (ext-rbac Endpoints funktional) |
| Entra ID Gruppen-Sync | **Nicht implementiert** (manuelles Management) |

### 1.3 Agents/Personas

| Eigenschaft | Wert |
|-------------|------|
| Default-Persona | Onyx Default Assistant |
| Custom Personas | **DB-Verifikation noetig** |
| LLM-Override pro Persona | Moeglich (`llm_model_provider_override`, `llm_model_version_override`) |
| Persona Access Control | `is_public=true` (Default, alle User sehen alle Personas) |

### 1.4 Token-Tracking

| Eigenschaft | Wert |
|-------------|------|
| ext-token aktiv | ✅ (`EXT_TOKEN_LIMITS_ENABLED=true`) |
| Per-User Tracking | ✅ (prompt_tokens, completion_tokens, model_name) |
| Per-User Limits | Konfigurierbar (token_budget, period_hours) |
| Kosten-Tracking | ❌ Keine EUR/USD-Zuordnung pro Modell |

### 1.5 Authentifizierung

| Environment | Auth-Typ | Status |
|-------------|----------|--------|
| DEV | OIDC (Entra ID) | ✅ LIVE (seit 2026-03-23) |
| PROD | OIDC (Entra ID) | ✅ LIVE (seit 2026-03-24) |
| TEST | — | Heruntergefahren |

---

## 2. Onyx FOSS Access Control Capabilities

### 2.1 Verfuegbare Features (Code-Analyse)

| Feature | FOSS-Code vorhanden | Tabelle/Funktion | Aktuell genutzt |
|---------|---------------------|-------------------|-----------------|
| Public/Private Provider | ✅ | `llm_provider.is_public` | ❌ (alles public) |
| User Group Restrictions | ✅ | `llm_provider__user_group` | ❌ (leer) |
| Persona Whitelist | ✅ | `llm_provider__persona` | ❌ (leer) |
| Kombinierte AND-Logik | ✅ | `can_user_access_llm_provider()` | ❌ |
| Provider Visibility (Hiding) | ✅ | API-Filterung in `list_llm_provider_basics()` | ❌ |
| Graceful Fallback | ✅ | `get_llm_for_persona()` → Default Provider | ❌ (nicht relevant, alles public) |

> **Wichtig:** Trotz "EE only"-Kommentaren im Code (`models.py:2953`) ist die gesamte Access-Control-Logik in der FOSS-Codebase implementiert und funktional. `backend/ee/` ist leer (nur `__init__.py`). Kein EE-Override existiert fuer LLM-Access-Control.

### 2.2 Access Decision Matrix (aus Code `backend/onyx/db/llm.py:101-147`)

| is_public | Groups gesetzt | Personas gesetzt | Zugriffsregel |
|-----------|---------------|-----------------|---------------|
| true | Egal | Nein | **Alle haben Zugriff** |
| true | Egal | Ja | Alle User, aber NUR ueber whitelisted Personas |
| false | Ja | Ja | Muss in Gruppe **UND** whitelisted Persona nutzen |
| false | Ja | Nein | Muss in Gruppe sein (Admins umgehen Gruppen) |
| false | Nein | Ja | Muss whitelisted Persona nutzen (gilt auch fuer Admins!) |
| false | Nein | Nein | **Nur Admin-Zugriff** (gesperrt) |

**Admin-Verhalten:**
- Admins umgehen **Group Restrictions** (immer Zugriff unabhaengig von Gruppenmitgliedschaft)
- Admins koennen **Persona Restrictions NICHT umgehen** (Persona-Whitelist gilt fuer alle)
- Fallback: Wenn User keinen Zugriff auf Persona's LLM-Provider hat → stiller Fallback auf Default-Provider (kein Fehler)

### 2.3 Enforcement Points im Code

| Stelle | Datei | Funktion |
|--------|-------|----------|
| Chat-Flow (Modell-Auswahl) | `backend/onyx/llm/factory.py:84-138` | `get_llm_for_persona()` |
| Provider-Liste (User-API) | `backend/onyx/server/manage/llm/api.py:634-683` | `list_llm_provider_basics()` |
| Persona-spezifische Provider | `backend/onyx/server/manage/llm/api.py:721-817` | `list_llm_providers_for_persona()` |
| User-Gruppen laden | `backend/onyx/db/llm.py:79-98` | `fetch_user_group_ids()` |

---

## 3. Gap-Analyse

### 3.1 Kern-Problem: Keine modellgranulare Zugriffssteuerung

**Aktuell:** 1 Provider → 3 Modelle → `is_public=true` → jeder User sieht und nutzt jedes Modell.

**Gewuenscht:** Abteilungs-basierte Modellzuweisung. Beispiele:
- Marketing bekommt GPT-OSS zugewiesen
- Vertrieb bekommt ein anderes Modell
- Entwickler bekommen Claude (eigener Provider, Anthropic API)
- Ein Basis-Modell steht allen zur Verfuegung

**Onyx-Loesung:** 1:1 Provider-Modell-Mapping. Jedes Modell wird als eigener Provider angelegt. Pro Provider koennen dann Gruppen (= Abteilungen) zugewiesen werden.

### 3.2 Nicht genutzte Features

| Feature | Risiko durch Nicht-Nutzung | Prioritaet |
|---------|---------------------------|------------|
| Provider Private/Public Toggle | Alle User haben Zugriff auf alle Modelle — keine abteilungsspezifische Steuerung | **Hoch** |
| User Group Restrictions | Keine Abteilungs-basierte LLM-Zuweisung moeglich | **Hoch** |
| Persona Whitelist | Kein Agent-basiertes Modell-Routing | **Niedrig** |
| 1:1 Provider-Modell-Mapping | Voraussetzung fuer modellgranulare Zugriffssteuerung | **Hoch** |

### 3.3 Sicherheits- und Kostenrisiken

| # | Risiko | Eintritt | Schwere | Aktuelle Mitigation | Empfehlung |
|---|--------|----------|---------|---------------------|------------|
| R-01 | **Kein Least Privilege** — Alle 150 User koennen jedes Modell nutzen, keine Differenzierung nach Abteilung/Rolle | Hoch | Mittel | ext-token Per-User-Limits (konfigurierbar) | 1:1 Provider-Mapping + Abteilungsgruppen |
| R-02 | **Unkontrollierte Kosten** — Grosse Modelle (235B) fuer alle verfuegbar ohne Steuerung | Hoch | Mittel | ext-token Tracking (aber kein Enforcement auf Modellebene) | Provider-Restrictions pro Abteilung |
| R-03 | **Compliance-Risiko bei externen Providern** — Zukuenftige Provider (z.B. Anthropic/Claude) haben andere DPAs als StackIT | Mittel | Hoch | Aktuell nur StackIT (EU01, BSI C5) | Externe Provider nur fuer berechtigte Gruppen |
| R-04 | **Shadow-Agents** — User koennen Personas mit LLM-Overrides erstellen | Mittel | Niedrig | Persona `is_public` Default, Admin-only fuer Provider-Config | Persona-Erstellung einschraenken (ext-access Phase 4g) |
| R-05 | **Kein Modell-Level Auditing** — ext-token trackt per Modell, aber Access-Entscheidungen werden nicht geloggt | Mittel | Niedrig | ext-token Usage Logs | Access-Decision-Logging (spaeter, nicht dringend) |

---

## 4. Bewertung

### 4.1 Zusammenfassung

| Kategorie | Score | Kommentar |
|-----------|-------|-----------|
| Verfuegbarkeit der Features | 10/10 | Alle Access-Control-Features sind FOSS und funktional |
| Nutzung der Features | 2/10 | Keine Restrictions konfiguriert (alles public) |
| Dokumentation | 3/10 | LLM-Konfig dokumentiert, Access Control fehlt |
| Kosten-Kontrolle | 5/10 | ext-token aktiv, aber keine Modell-basierte Steuerung |
| Compliance | 7/10 | Aktuell nur StackIT (EU01) = kein DPA-Risiko. Risiko steigt mit externen Providern. |
| **Gesamt** | **5.4/10** | Gute Basis, Konfiguration fehlt |

### 4.2 Empfohlene Massnahmen

| # | Massnahme | Aufwand | Prioritaet | Abhaengigkeit |
|---|-----------|---------|------------|---------------|
| M-01 | 1:1 Provider-Modell-Mapping: Jedes Modell als eigener Provider | 30 Min (UI) | **P1** | Keine |
| M-02 | Abteilungs-Gruppen in ext-rbac anlegen (Marketing, Vertrieb, Entwicklung, ...) | 1h (UI) | **P1** | ext-rbac aktiv ✅, Abteilungsliste von VÖB noetig |
| M-03 | Provider-Gruppen-Zuweisung: Welche Abteilung sieht welches Modell | 15 Min (UI) pro Provider | **P1** | M-01 + M-02 |
| M-04 | Basis-Modell als public belassen (Default fuer alle) | 5 Min (UI) | **P1** | M-01 |
| M-05 | SOLL-Konzept dokumentieren (`docs/referenz/llm-access-control.md`) | 1h (Doku) | **P1** | M-01 |
| M-06 | Runbook erstellen (`docs/runbooks/llm-provider-management.md`) | 1h (Doku) | **P2** | M-05 |
| M-07 | Sicherheitskonzept aktualisieren (Autorisierung-Abschnitt) | 30 Min (Doku) | **P2** | M-05 |
| M-08 | Neuen Provider fuer externe LLMs (z.B. Claude/Anthropic) anlegen — private, nur Entwickler | 15 Min (UI) | **P2** | M-02 + Anthropic API-Key |
| M-09 | Persona-LLM-Whitelisting fuer spezielle Agents | nach Bedarf | **P3** | M-01 |
| M-10 | Access-Decision-Logging (ext-Erweiterung) | 4h (Code) | **P3** | — |

---

## 5. Naechste Schritte

1. **Sofort (P1):** 1:1 Provider-Mapping + Abteilungsgruppen + Zuweisung in Admin-UI
2. **Diese Woche (P2):** Externe Provider (Claude), Doku-Updates
3. **Spaeter (P3):** Persona-Whitelisting, Access-Logging, Entra ID Gruppen-Sync

> **Hinweis:** Alle P1-Massnahmen sind reine UI-Konfiguration — kein Code, kein Deployment, kein Feature-Branch noetig. Voraussetzung: VÖB liefert Abteilungsliste.

---

## Anhang A: Relevante Code-Dateien

| Datei | Inhalt |
|-------|--------|
| `backend/onyx/db/models.py:2925-2973` | LLMProvider SQLAlchemy Model |
| `backend/onyx/db/models.py:4018-4047` | Junction Tables (LLMProvider__Persona, LLMProvider__UserGroup) |
| `backend/onyx/db/llm.py:79-147` | `fetch_user_group_ids()`, `can_user_access_llm_provider()` |
| `backend/onyx/llm/factory.py:84-138` | `get_llm_for_persona()` (Chat-Flow Enforcement) |
| `backend/onyx/server/manage/llm/api.py:634-817` | Provider-Liste + Persona-Provider API |
| `backend/ext/services/token_tracker.py` | ext-token Usage Tracking |
| `backend/ext/routers/rbac.py` | ext-rbac Gruppen-Endpoints |

## Anhang B: DB-Verifikation (manuell durchzufuehren)

Die folgenden Queries sollten auf DEV und PROD ausgefuehrt werden um den IST-Zustand zu verifizieren:

```sql
-- LLM-Provider und Access Control
SELECT id, name, provider, default_model_name, is_public, is_default_provider
FROM llm_provider ORDER BY id;

-- Provider ↔ Gruppen (erwartet: leer)
SELECT lp.name AS provider, ug.name AS group_name
FROM llm_provider__user_group lpug
JOIN llm_provider lp ON lpug.llm_provider_id = lp.id
JOIN user__group ug ON lpug.user_group_id = ug.id;

-- Provider ↔ Personas (erwartet: leer)
SELECT lp.name AS provider, p.name AS persona
FROM llm_provider__persona lpp
JOIN llm_provider lp ON lpp.llm_provider_id = lp.id
JOIN persona p ON lpp.persona_id = p.id;

-- User-Gruppen
SELECT id, name, is_up_to_date FROM user__group ORDER BY id;

-- Gruppen-Mitgliedschaften
SELECT ug.name AS group_name, COUNT(uug.user_id) AS members
FROM user__group ug
LEFT JOIN user__user_group uug ON ug.id = uug.user_group_id
GROUP BY ug.name;

-- Personas mit LLM-Overrides
SELECT id, name, llm_model_provider_override, llm_model_version_override, is_public
FROM persona WHERE deleted = false ORDER BY id;
```
