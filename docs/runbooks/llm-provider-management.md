# Runbook: LLM Provider Management

> Operatives Runbook fuer das Anlegen, Aendern und Einschraenken von LLM-Providern.
> SSOT fuer Access Control: [`docs/referenz/llm-access-control.md`](../referenz/llm-access-control.md)
> Letzte Aktualisierung: 2026-03-24

---

## 1. Architektur: 1:1 Provider-Modell-Mapping

Onyx steuert Zugriff auf **Provider-Ebene**. Fuer modellgranulare Steuerung wird jedes Modell als eigener Provider angelegt:

```
Provider "GPT-OSS 120B"   → 1 Modell  → private → Gruppen: [Abteilung X, Y]
Provider "Qwen3-VL 235B"  → 1 Modell  → private → Gruppen: [Abteilung Z]
Provider "Llama 3.3 70B"  → 1 Modell  → public  → Alle User
Provider "Claude"          → 1 Modell  → private → Gruppen: [Entwicklung]
```

Alle StackIT-Provider teilen sich API-Key und API-Base. Externe Provider (Claude, etc.) haben eigene Credentials.

---

## 2. Provider anlegen (1:1 Mapping)

### 2.1 StackIT-Modell als Provider anlegen

**Pfad:** Admin Panel → Configuration → LLM → Add Custom LLM Provider

| Feld | Wert | Bemerkung |
|------|------|-----------|
| Provider Name | Modellname, z.B. "GPT-OSS 120B" | Eindeutig, wird in UI angezeigt |
| Provider | `Custom` | OpenAI-kompatibler Endpoint |
| API Key | StackIT AI Model Serving Token | Identisch fuer alle StackIT-Provider |
| API Base URL | `https://api.openai-compat.model-serving.eu01.onstackit.cloud/v1` | Identisch fuer alle StackIT-Provider |
| Default Model | Die Model-ID, z.B. `openai/gpt-oss-120b` | **Nur 1 Modell pro Provider** |
| Display Model Names | Gleiche Model-ID | Nur dieses eine Modell anzeigen |

Wiederholen fuer jedes Modell das einzeln steuerbar sein soll.

### 2.2 Externen Provider anlegen (z.B. Claude)

| Feld | Wert | Bemerkung |
|------|------|-----------|
| Provider Name | "Claude" | |
| Provider | `Custom` | |
| API Key | Anthropic API Key | **Eigener Key, nicht StackIT** |
| API Base URL | `https://api.anthropic.com/v1` | Anthropic Endpoint |
| Default Model | z.B. `claude-sonnet-4-6` | |

### 2.3 Basis-Modell (public, fuer alle)

Mindestens ein Provider muss `is_public=true` sein — das ist das Basis-Modell das alle User sehen.

**Empfehlung:** Llama 3.3 70B als Basis (schnell, kosteneffizient, 128K Context).

### 2.4 Provider bearbeiten / loeschen

**Bearbeiten:** Admin Panel → Configuration → LLM → Provider auswaehlen → Edit
**Loeschen:** Admin Panel → Configuration → LLM → Provider auswaehlen → Delete

**Vorsicht beim Loeschen:**
- Entfernt alle Gruppen- und Persona-Verknuepfungen
- Personas mit LLM-Override auf diesen Provider fallen auf Default-Provider zurueck
- **Vor dem Loeschen:** Pruefen ob Personas den Provider referenzieren

---

## 3. Access Control konfigurieren

### 3.1 Provider auf Private setzen

**Pfad:** Admin Panel → Configuration → LLM → Provider auswaehlen → Advanced Options

1. "Make Public" Toggle → **OFF**
2. Save

**Ergebnis:** Provider ist nur fuer Admins und explizit berechtigte Gruppen sichtbar.

### 3.2 Abteilungs-Gruppe zuweisen

**Voraussetzung:** Gruppe muss in ext-rbac existieren (`/admin/ext-groups`).

**Pfad:** Admin Panel → Configuration → LLM → Provider → Advanced Options → Access Controls

1. "User Group Access" → Abteilungs-Gruppe(n) auswaehlen
2. Save

**Verhalten:**
- Nur User in den ausgewaehlten Gruppen sehen den Provider (= das Modell)
- Admins umgehen Gruppen-Restrictions (sehen den Provider immer)
- Ein User kann in mehreren Gruppen sein → sieht Vereinigung aller Provider

### 3.3 Persona Whitelist (optional)

**Pfad:** Admin Panel → Configuration → LLM → Provider → Advanced Options → Access Controls

1. "Agent Whitelist" → Persona(s) auswaehlen
2. Save

**Verhalten:**
- Provider ist NUR ueber die whitelisted Personas nutzbar
- Gilt fuer ALLE User, inklusive Admins
- Persona-Restriction + Group-Restriction = AND-Logik

**Beispiel-Use-Case:** Claude-Provider nur ueber "Code-Agent" nutzbar, nicht im freien Chat.

### 3.4 Access Control entfernen

1. Provider → Advanced Options → Access Controls
2. Gruppen/Personas abwaehlen
3. "Make Public" → ON (falls gewuenscht)
4. Save

---

## 4. Abteilungs-Gruppen verwalten (ext-rbac)

### 4.1 Gruppe anlegen

**Pfad:** Admin Panel → Permissions → Gruppen (`/admin/ext-groups`)

1. "Neue Gruppe" klicken
2. Gruppenname = Abteilungsname (z.B. "Marketing", "Vertrieb", "Entwicklung")
3. Mitglieder hinzufuegen
4. Save

### 4.2 Gruppe mit Provider verknuepfen

Nach Anlage der Gruppe → Provider Access Control konfigurieren (siehe 3.2).

### 4.3 Neuen Mitarbeiter hinzufuegen

1. Mitarbeiter loggt sich erstmals ein (OIDC → automatischer User-Account)
2. Admin → Permissions → Gruppen → passende Gruppe oeffnen
3. Mitarbeiter hinzufuegen
4. Mitarbeiter sieht sofort die Provider seiner Gruppe(n)

### 4.4 API-Endpoints (ext-rbac)

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/manage/admin/user-group` | GET | Alle Gruppen auflisten |
| `/manage/admin/user-group` | POST | Gruppe anlegen |
| `/manage/admin/user-group/{id}` | PATCH | Gruppe aktualisieren |
| `/manage/admin/user-group/{id}` | DELETE | Gruppe loeschen |
| `/manage/admin/user-group/{id}/add-users` | POST | Mitglieder hinzufuegen |
| `/manage/admin/user-group/{id}/set-curator` | POST | Curator-Status setzen |
| `/manage/user-groups/minimal` | GET | Lightweight Gruppenliste |

---

## 5. Validierung

### 5.1 Nach Provider-Split: Modellsichtbarkeit pruefen

| Test | User-Rolle | Erwartung |
|------|-----------|-----------|
| Basis-Modell sichtbar | Standard-User (keine Gruppe) | ✅ Llama 3.3 70B sichtbar |
| Private Modelle unsichtbar | Standard-User (keine Gruppe) | ❌ GPT-OSS, Qwen3-VL, Claude NICHT sichtbar |
| Gruppen-Modell sichtbar | Marketing-User | ✅ Llama 3.3 + GPT-OSS sichtbar |
| Andere Gruppen-Modelle unsichtbar | Marketing-User | ❌ Qwen3-VL, Claude NICHT sichtbar |
| Admin sieht alles | Admin | ✅ Alle Provider sichtbar |

### 5.2 Fallback testen

1. Persona mit LLM-Override auf GPT-OSS 120B Provider erstellen
2. Als User OHNE GPT-OSS-Zugriff die Persona nutzen
3. **Erwartung:** Chat funktioniert (stiller Fallback auf Llama 3.3 70B)

### 5.3 DB-Verifikation

```sql
-- Alle Provider mit Access-Control-Status
SELECT id, name, is_public,
       (SELECT COUNT(*) FROM llm_provider__user_group WHERE llm_provider_id = lp.id) AS group_count,
       (SELECT COUNT(*) FROM llm_provider__persona WHERE llm_provider_id = lp.id) AS persona_count
FROM llm_provider lp;

-- Welche Gruppe sieht welchen Provider?
SELECT lp.name AS provider, ug.name AS group_name
FROM llm_provider__user_group lpug
JOIN llm_provider lp ON lpug.llm_provider_id = lp.id
JOIN user__group ug ON lpug.user_group_id = ug.id
ORDER BY lp.name, ug.name;
```

---

## 6. Troubleshooting

### User sieht Modell nicht

| Symptom | Ursache | Loesung |
|---------|---------|---------|
| Modell fehlt im Model Selector | Provider `is_public=false` und User nicht in Gruppe | User zur richtigen Abteilungsgruppe hinzufuegen |
| Modell fehlt nur bei bestimmter Persona | Provider hat Persona-Whitelist, Persona nicht enthalten | Persona zur Whitelist hinzufuegen |
| Admin sieht Modell nicht bei Persona | Persona-Whitelist aktiv (gilt auch fuer Admins!) | Persona zur Whitelist hinzufuegen |
| Neuer Mitarbeiter sieht nur Basis-Modell | User ist noch in keiner Abteilungsgruppe | Zur Abteilungsgruppe hinzufuegen |

### Chat nutzt falsches Modell

| Symptom | Ursache | Loesung |
|---------|---------|---------|
| Persona nutzt Basis-Modell statt Spezial-Modell | User hat keinen Zugriff auf Persona's Provider → Fallback | User zur passenden Gruppe hinzufuegen |
| Modell-Wechsel ohne User-Aktion | User wurde aus Gruppe entfernt | Gruppenzugehoerigkeit pruefen |

### API-Fehler

| Symptom | Ursache | Loesung |
|---------|---------|---------|
| 403 auf `/api/admin/llm/provider` | User ist kein Admin | Admin-Rechte oder `/api/manage/llm/provider` nutzen |
| Provider-Liste leer | Alle Provider private + User in keiner Gruppe | Mindestens einen Provider public lassen |

---

## 7. Rollback

Falls nach Umstellung User keinen Zugriff mehr haben:

### Sofort-Massnahme (< 1 Minute)

1. Admin Panel → Configuration → LLM → betroffenen Provider oeffnen
2. Advanced Options → "Make Public" → **ON**
3. Save

### Gruppen-Zuordnung pruefen (< 5 Minuten)

1. Admin Panel → Permissions → Gruppen
2. Betroffene Gruppe oeffnen → Mitglieder pruefen
3. Fehlende User hinzufuegen

### DB-Rollback (Notfall)

```sql
-- Alle Provider auf public setzen (Sofort-Fix)
UPDATE llm_provider SET is_public = true;

-- Alle Gruppen-Restrictions entfernen
DELETE FROM llm_provider__user_group;

-- Alle Persona-Restrictions entfernen
DELETE FROM llm_provider__persona;
```

> **Achtung:** DB-Rollback nur als letzte Massnahme. Danach Admin-UI-Zustand mit DB synchronisieren (jeden Provider oeffnen + speichern).

---

## 8. Checkliste: Neues Modell hinzufuegen

- [ ] Provider in Admin-UI anlegen (1:1 Mapping, siehe 2.1/2.2)
- [ ] `is_public` entscheiden (true = alle, false = nur Gruppen)
- [ ] Falls private: Gruppen zuweisen (siehe 3.2)
- [ ] Falls externer Provider: DPA pruefen, eigene API-Credentials
- [ ] Validierung als Nicht-Admin-User (siehe 5.1)
- [ ] `docs/referenz/llm-access-control.md` aktualisieren (Provider-Matrix)
- [ ] `docs/runbooks/llm-konfiguration.md` aktualisieren (Modell-Liste)

---

## 9. Referenzen

| Dokument | Pfad |
|----------|------|
| LLM Access Control SOLL-Konzept | `docs/referenz/llm-access-control.md` |
| LLM Access Control Audit | `docs/audit/2026-03-24-llm-access-control-audit.md` |
| LLM Konfiguration Runbook | `docs/runbooks/llm-konfiguration.md` |
| ext-rbac Feinkonzept | `docs/technisches-feinkonzept/ext-rbac.md` |
| Sicherheitskonzept | `docs/sicherheitskonzept.md` |
| Onyx FOSS Access Control Code | `backend/onyx/db/llm.py:79-147` |
| Onyx Doku LLM Access Controls | `https://docs.onyx.app/admins/advanced_configs/llm_access_controls` |
