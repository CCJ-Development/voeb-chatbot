# Analyse: Rollenkonzept VÖB Chatbot

**Stand:** 2026-03-23
**Autor:** COFFEESTUDIOS (Nikolaj Ivanov)
**Zweck:** Entscheidungsgrundlage fuer ext-rbac Implementierung
**Vorarbeit:** `docs/referenz/rbac-rollenmodell.md` (Entwurf vom 2026-03-07, Branch `feature/rbac-rollenmodell`)

---

## 1. Onyx Rollen-System (Ist-Zustand)

### 1.1 Rollen

| Rolle | FOSS? | Web-Login | Beschreibung |
|-------|-------|-----------|-------------|
| **ADMIN** | Ja | Ja | Voller Systemzugriff. User-Verwaltung, Connectoren, LLM-Config, Gruppen. |
| **BASIC** | Ja | Ja | Standard-User. Chat, Suche, zugewiesene Agents nutzen. |
| **CURATOR** | Enum: Ja, Logik: EE | Ja | Admin-Aktionen NUR fuer zugewiesene Gruppen. Braucht EE-Gruppen-Code. |
| **GLOBAL_CURATOR** | Enum: Ja, Logik: EE | Ja | Wie CURATOR, aber automatisch fuer ALLE Gruppen des Users. |
| **LIMITED** | Ja | Ja | Eingeschraenkter API-Zugriff. Wird von `current_user()` blockiert. |
| **SLACK_USER** | Ja | Nein | Nur Slack-Zugang. Nicht relevant fuer VÖB. |
| **EXT_PERM_USER** | Ja | Nein | Externe Permission-Sync User. Nicht relevant fuer VÖB. |

**Default bei OIDC-Login:** BASIC (erster User wurde manuell auf ADMIN gesetzt).

### 1.2 Gruppen

| Aspekt | DB-Schema (FOSS) | CRUD/API (EE) | Status fuer VÖB |
|--------|-------------------|---------------|-----------------|
| `UserGroup` Tabelle | Ja | — | Vorhanden, nutzbar |
| `User__UserGroup` (mit `is_curator` Flag) | Ja | — | Vorhanden, nutzbar |
| `UserGroup__ConnectorCredentialPair` | Ja | — | Vorhanden, nutzbar |
| `Persona__UserGroup` | Ja | — | Vorhanden, nutzbar |
| `DocumentSet__UserGroup` | Ja | — | Vorhanden, nutzbar |
| **`LLMProvider__UserGroup`** | Ja | — | Vorhanden, nutzbar |
| `TokenRateLimit__UserGroup` | Ja | — | Vorhanden, nutzbar |
| Gruppen-Verwaltungs-API | — | `backend/ee/onyx/db/user_group.py` | **Muss in ext-rbac nachgebaut werden** |
| Gruppen-Frontend (Admin UI) | `web/src/refresh-pages/admin/GroupsPage/` vorhanden | — | Vorhanden, moeglicherweise nutzbar |

**Zentrale Erkenntnis:** Das komplette DB-Schema fuer Gruppen ist FOSS. Was fehlt, ist ausschliesslich die CRUD-Geschaeftslogik in `backend/ee/`. Wir muessen eigene API-Endpoints in `backend/ext/` bauen, die auf denselben Tabellen operieren.

### 1.3 Berechtigungs-Matrix

| Feature | ADMIN | BASIC | CURATOR (EE) | Steuerbar pro Gruppe? | In FOSS funktional? |
|---------|-------|-------|-------------|----------------------|-------------------|
| Admin-Panel Zugriff | Ja | Nein | Teilweise | — | Ja |
| User-Verwaltung | Ja | Nein | Nein | — | Ja |
| Rollen zuweisen | Ja | Nein | Nein | — | Ja |
| Connector erstellen | Ja | Nein | Eigene Gruppe | Ja | Nein (EE) |
| Connector nutzen | Ja | Zugewiesene | Zugewiesene | Ja | Nein (EE) |
| Dokumente sehen | Alle | Zugewiesene | Zugewiesene | Ja | Nein (EE, `access.py` setzt `groups=[]`) |
| Agent/Persona erstellen | Ja | Konfigurierbar | Eigene Gruppe | Ja | Teilweise |
| Agent/Persona nutzen | Alle | Zugewiesene | Zugewiesene | Ja | Nein (EE) |
| **LLM-Modell nutzen** | Alle | Public oder Gruppen | Public oder Gruppen | **Ja** | **Ja** (`can_user_access_llm_provider` ist FOSS) |
| LLM-Provider konfigurieren | Ja | Nein | Nein | — | Ja |
| Chat-History anderer sehen | Nein | Nein | Nein | — | — |
| System-Prompts aendern | Ja | Nein | Nein | — | Ja (ext-prompts) |
| Branding aendern | Ja | Nein | Nein | — | Ja (ext-branding) |
| Token Usage sehen | Ja | Eigene | Eigene Gruppe | Ja | Ja (ext-token) |

### 1.4 Modell-Zugriffskontrolle

**Onyx hat native LLM-Zugriffskontrolle pro Gruppe!**

Die Tabelle `LLMProvider__UserGroup` (`backend/onyx/db/models.py:4034`) verknuepft LLM-Provider mit Gruppen:

| Konfiguration | Verhalten |
|--------------|-----------|
| Keine Eintraege fuer Provider | Provider ist **public** — alle User koennen ihn nutzen |
| Eintraege fuer bestimmte Gruppen | Provider ist **private** — nur diese Gruppen + Admins |

Die Pruefungsfunktion `can_user_access_llm_provider()` in `backend/onyx/db/llm.py` ist **FOSS** und funktioniert sofort, sobald die Gruppen-Zuordnungen in der DB existieren.

**Zusaetzlich:** `LLMProvider__Persona` ermoeglicht Modell-Einschraenkung pro Agent (unabhaengig von Gruppen, funktioniert in FOSS).

**Fazit fuer VÖB:** Sobald ext-rbac Gruppen verwalten kann, funktioniert Modell-Zugriff pro Gruppe automatisch.

---

## 2. Entra ID Integration

### 2.1 Was Onyx aus dem OIDC-Token liest

| Claim | Gelesen? | Verwendet fuer |
|-------|----------|---------------|
| `email` | Ja | User-Identifikation (Primary Key) |
| `sub` / `oid` | Ja | OAuth Account ID |
| `access_token` | Ja | Gespeichert fuer Token-Refresh |
| `refresh_token` | Ja | Offline-Access |
| `expires_at` | Ja | Optional: Session-Expiry Tracking |
| **`groups`** | **Nein** | **Nicht implementiert** |
| `roles` | Nein | Nicht implementiert |

### 2.2 Gruppen-Sync Moeglichkeiten

| Methode | Status | Beschreibung |
|---------|--------|-------------|
| **Manuell (Admin UI)** | Moeglich mit ext-rbac | Admin weist User manuell zu Gruppen zu |
| **OIDC `groups` Claim** | Muss gebaut werden | Entra ID sendet Gruppen-IDs im Token, ext-rbac mappt sie |
| **Microsoft Graph API** | Muss gebaut werden | Backend fragt Gruppen per Graph API ab (zuverlaessiger als Claim) |
| **SCIM Provisioning** | EE-only | Automatischer Sync. Onyx hat `EntraProvider` in EE. |

**Empfehlung fuer VÖB:** Start mit manueller Zuordnung, spaeter OIDC `groups` Claim oder Graph API.

### 2.3 Limitierungen

- Entra ID sendet `groups` Claim nur wenn als **Optional Claim** in der App Registration konfiguriert
- Bei >200 Gruppen: kein Claim, stattdessen Overage-Indicator (Graph API noetig)
- B2B-Gaeste (CCJ/Niko) bekommen gleiche Group-Claims wie regulaere User

---

## 3. VÖB-spezifisches Konzept

### 3.1 Vorgeschlagene Rollen

| VÖB-Rolle | Onyx-Mapping | Wer | Anzahl |
|-----------|-------------|-----|--------|
| **System-Admin** | ADMIN | CCJ (Niko) + Rechenzentrum (Leif Rasch) | 2-3 |
| **Gruppen-Admin** | CURATOR (via ext-rbac) | Abteilungsleiter (16 Personen) | ~16 |
| **Standard-User** | BASIC | Alle Mitarbeitenden | ~85 |

### 3.2 Massnahmengruppe

**Problem:** Temporaeres Projekt-Team braucht Admin-Rechte waehrend Einfuehrungsphase.

**Empfehlung: Option A (manuell)**
- Massnahmengruppe bekommt ADMIN-Rolle
- Nach Abschluss: Rolle auf BASIC/CURATOR zuruecksetzen, neue Admins zuweisen
- Kein Custom Code noetig, funktioniert sofort
- Aufwand: 5 Minuten per Admin UI

### 3.3 Organisationsstruktur (Organigramm Stand 01.02.2026)

**~100 Mitarbeitende, 2 Standorte (Bonn + Berlin), 16 Gruppen:**

| # | Gruppe | Abteilungsleiter/in | MA | Standort |
|---|--------|--------------------|----|----------|
| 1 | Geschaeftsleitung | Stephan Henkel (GF) | 3 | Bonn |
| 2 | Academy of Finance | Kathleen Weigelt | 7 | Bonn |
| 3 | Regulatory Compliance Redaktion | Frank Reiff | 7 | Bonn |
| 4 | Regulatory Compliance Produkt | Daniel Tsubaki | 5 | Bonn |
| 5 | Non-Financial Risk | Olaf Zissner | 5 | Bonn |
| 6 | Marketing & Kommunikation | Pascal Witthoff | 5 | Bonn |
| 7 | Rechnungsw./Controlling & int. Services | Andreas Kuester | 8 | Bonn+Berlin |
| 8 | Rechenzentrum | Leif Rasch | 7 | Bonn+Berlin |
| 9 | Recht | Holger Heuschen | 6 | Bonn |
| 10 | Wertpapieraufsicht & Derivate | Beatrice Wirz | 7 | Bonn |
| 11 | Vergabemanagement & Software Service | Andreas Wolf | 5 | Bonn |
| 12 | Foerdermittel Kreditsoftware | Bjoern Schmidt | 12 | Bonn |
| 13 | Foerdermittel Beratungssoftware | Burkhard Heling | 10 | Berlin |
| 14 | Foerdermittel Redaktion | Katrin Owesen | 8 | Berlin |
| 15 | Versicherungen | Yvonne Biedermann (interim) | 4 | Bonn |
| 16 | Stabsstellen | (ISB, Revision, DSB, Azubis) | ~6 | Bonn |

**Quelle:** VÖB-Service GmbH Organigramm, Dokumentenklassifizierung: Vertraulich.

**Hinweis:** VÖB hat keine Entra ID Gruppen fuer Abteilungen. Gruppenzuordnung erfolgt manuell durch Admin im Chatbot. Jeder Abteilungsleiter wird CURATOR seiner Gruppe.

### 3.4 Modell-Zugriff

Onyx unterstuetzt Modell-Zugriff pro Gruppe nativ (DB-Schema vorhanden, Pruefungslogik FOSS). Sobald ext-rbac Gruppen verwaltet, kann per Admin UI:
- Modelle als "public" oder "private" markiert werden
- Private Modelle bestimmten Gruppen zugewiesen werden
- Z.B.: GPT-OSS 120B nur fuer Power-User, Llama 8B fuer alle

---

## 4. Gap-Analyse

### 4.1 Was sofort funktioniert (kein Code noetig)

| Feature | Status |
|---------|--------|
| Admin/Basic Rollen | Ja — funktioniert seit Entra ID Login |
| Rollen manuell aendern | Ja — per Admin UI oder DB |
| LLM Provider konfigurieren | Ja — per Admin UI |
| Agents/Personas erstellen | Ja — per Admin UI |
| Connectoren erstellen | Ja — per Admin UI |

### 4.2 Was ext-rbac liefern muss

| Feature | Prioritaet | Aufwand | Beschreibung |
|---------|-----------|---------|-------------|
| **Gruppen-CRUD API** | Must-Have | Mittel | Endpoints: Create, Read, Update, Delete Gruppen in `backend/ext/` |
| **User-zu-Gruppe Zuordnung** | Must-Have | Mittel | User Gruppen zuweisen/entfernen, `is_curator` setzen |
| **Gruppen-Frontend** | Must-Have | Mittel | Admin UI fuer Gruppenverwaltung (oder bestehende GroupsPage nutzen) |
| **Connector-zu-Gruppe** | Should-Have | Niedrig | Connectoren Gruppen zuweisen (M2M Tabelle existiert) |
| **LLM-Provider-zu-Gruppe** | Should-Have | Niedrig | Modelle Gruppen zuweisen (M2M Tabelle existiert) |
| **Agent-zu-Gruppe** | Should-Have | Niedrig | Personas Gruppen zuweisen (M2M Tabelle existiert) |
| **Entra ID Gruppen-Mapping** | Nice-to-Have | Mittel | `groups` Claim lesen und auf Onyx-Gruppen mappen |
| **SCIM** | Nice-to-Have | Hoch | Automatischer User+Gruppen Sync. Wahrscheinlich nicht noetig bei 150 Usern. |

### 4.3 Was ext-access liefern muss (Phase 4g, nach ext-rbac)

| Feature | Beschreibung |
|---------|-------------|
| Document-Level Access Check | `access.py` Hook: `user_groups` befuellen statt `[]` |
| Connector-Sichtbarkeit | Nur Connectoren der eigenen Gruppen anzeigen |

### 4.4 Sicherheitshinweis (CVE-2025-51479)

Onyx EE hatte eine **Authorization Bypass Vulnerability** in der Gruppen-API: Der PATCH-Endpoint validierte nicht, ob ein Curator die Berechtigung fuer die spezifische Gruppe hat. Bei ext-rbac implementieren wir das von Anfang an korrekt.

---

## 5. Informationsbedarf (VÖB)

### Geklaert

- ✅ **Abteilungsstruktur:** 16 Gruppen aus Organigramm (Stand 01.02.2026), siehe Abschnitt 3.3
- ✅ **~100 Mitarbeitende**, 2 Standorte (Bonn + Berlin)
- ✅ **Keine Entra ID Gruppen** vorhanden — Zuordnung manuell durch Admin im Chatbot
- ✅ **Ansprechpartner:** Pascal Witthoff (Marketing, Massnahmengruppe), Leif Rasch (Rechenzentrum/IT)

### Noch offen (mit VÖB zu klaeren)

- 1. Sollen alle Abteilungen alle Datenquellen und Agenten sehen, oder soll es Trennung geben?
- 2. Gibt es vertrauliche Bereiche (z.B. Recht, Geschaeftsfuehrung)?
- 3. Wer gehoert zur Massnahmengruppe und wer uebernimmt Admin-Rechte danach?
- 4. Wird ein Login-Audit-Log benoetigt? Vorgaben zur Session-Dauer?

---

## 6. Empfehlung

### Was sofort umgesetzt werden kann (ohne VÖB-Input)

1. **OIDC Error-Logging** (P1) — Enterprise-Pflicht, heute validiert
2. **Auth Alert in Prometheus** (P2) — AlertRule fuer Login-Fehler
3. **Massnahmengruppe als ADMINs** — Rollen manuell per Admin UI setzen
4. **LLM-Modelle konfigurieren** — Sind bereits auf DEV vorhanden

### Was VÖB-Input braucht

1. **Abteilungsliste** → Gruppen-Struktur definieren
2. **Zugriffsanforderungen** → ext-rbac Scope festlegen
3. **Entra ID Gruppen** → Sync-Strategie entscheiden

### Aufwandsschaetzung ext-rbac

| Phase | Aufwand | Abhaengigkeit |
|-------|---------|--------------|
| Gruppen-CRUD API (Must-Have) | 3-5 PT | Keine |
| Gruppen-Frontend | 2-3 PT | CRUD API |
| Connector/LLM/Agent Zuordnung | 2-3 PT | CRUD API |
| Entra ID Gruppen-Mapping | 3-5 PT | VÖB-Input (Gruppen-Namen) |
| **Gesamt** | **10-16 PT** | |

### Naechste Schritte

1. Fragenkatalog (Abschnitt 5) an VÖB senden
2. P1 + P2 (OIDC Hardening) implementieren
3. PROD OIDC Rollout
4. VÖB-Antworten einarbeiten → ext-rbac `/modulspec`
5. ext-rbac implementieren
