# Whitelabel / Branding-Setup für neuen Kunden

**Zielgruppe:** Tech Lead beim Kunden-Klon
**Dauer:** 1 h
**Phase:** 9 im [Master-Playbook](./kunden-klon-onboarding.md)

Dieses Runbook beschreibt, wie die Onyx-Standard-UI auf das Branding des Kunden angepasst wird (Logo, App-Name, Texte, Consent-Popup, Browser-Tab-Titel).

**Modulspezifikation:** `docs/technisches-feinkonzept/ext-branding.md`

---

## Voraussetzungen

- Helm-Release deployed (Phase 5)
- HTTPS aktiv (Phase 4)
- Admin-Zugang zur Onyx-UI
- Logo vom Kunden: PNG oder JPEG, maximal 2 MB, bevorzugt quadratisch (wird auf 256×256 gecroppt)
- Texte vom Kunden: App-Name, Login-Text, Greeting, Disclaimer, Consent-Text

---

## Architektur-Überblick

Branding ist **zweistufig** angelegt:

1. **Build-Zeit-Feature-Flags** im Frontend (Next.js): Einige Branding-Entscheidungen müssen beim `next build` feststehen, weil sie SSR-Inhalt beeinflussen.
2. **Runtime-Konfiguration** über die Admin-UI: Logo, Texte, Consent-Popup werden in der Postgres-Datenbank abgelegt (`ext_branding_config`) und pro Session geladen.

Feature-Flag: `EXT_BRANDING_ENABLED` (Backend) + `NEXT_PUBLIC_EXT_BRANDING_ENABLED` (Frontend Build-Zeit).

---

## 1. Build-Zeit-Konfiguration

### 1.1 `web/Dockerfile` prüfen

Beide Build-Stages (builder + runner) müssen den Flag durchreichen:

```dockerfile
ARG NEXT_PUBLIC_EXT_BRANDING_ENABLED=true
ENV NEXT_PUBLIC_EXT_BRANDING_ENABLED=${NEXT_PUBLIC_EXT_BRANDING_ENABLED}
```

Das ist bereits gesetzt aus dem Template-Fork. Prüfung mit:

```bash
grep NEXT_PUBLIC_EXT_BRANDING_ENABLED web/Dockerfile
# Erwartung: 2 ARG- + 2 ENV-Zeilen (eine pro Stage)
```

### 1.2 `.github/workflows/stackit-deploy.yml` Build-Args

```yaml
- name: Build & Push Frontend
  ...
  with:
    build-args: |
      NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=true
      NEXT_PUBLIC_EXT_I18N_ENABLED=true
      NEXT_PUBLIC_EXT_RBAC_ENABLED=true
      NEXT_PUBLIC_EXT_BRANDING_ENABLED=true
```

Alle vier Build-Args sollten auf `true` stehen.

### 1.3 Helm Values (`values-common.yaml`)

```yaml
configMap:
  EXT_ENABLED: "true"
  EXT_BRANDING_ENABLED: "true"
  NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED: "true"
  # weitere ext-Flags...
```

Der `EXT_BRANDING_ENABLED=true` aktiviert den Backend-Router. Der `NEXT_PUBLIC_*`-Flag wurde zum Build-Zeitpunkt in das Frontend-Bundle eingebacken.

### 1.4 Build auslösen

Wenn die Build-Args oder Dockerfile geändert wurden: CI/CD erneut triggern.

```bash
git push origin main   # löst auto-deploy DEV aus
# oder
gh workflow run stackit-deploy.yml -f environment=prod
```

---

## 2. Runtime-Konfiguration (Admin-UI)

### 2.1 Einmalige Erstkonfiguration

1. In Browser zur Admin-UI: `https://<DEV_DOMAIN>/admin/ext/branding`
2. Login mit Admin-Konto (erster OIDC-User wird automatisch Admin — JIT-Provisioning)
3. Folgende Felder ausfüllen:

| Feld | Beispiel VÖB | Hinweis |
|---|---|---|
| **App-Name** | „VÖB Service Chatbot" | Erscheint im Browser-Tab und Login-Screen |
| **Logo** | 256×256 PNG | Wird via Drag&Drop oder Upload-Button geladen; Magic-Byte-Validierung prüft PNG/JPEG |
| **Login-Tagline** | „Your enterprise AI platform" ersetzen durch Kunden-Tagline | Leer lassen für keine Tagline |
| **Greeting** | Begrüßungstext im leeren Chat | z. B. „Willkommen beim VÖB Service Chatbot" |
| **Disclaimer** | Haftungsausschluss / rechtlicher Hinweis | Wird unter jeder Chat-Antwort angezeigt |
| **Consent-Popup** | Initial-Popup nach Login | Optional: Einverständnis mit Nutzungsbedingungen einholen |

4. **Speichern** klicken. Die Konfiguration wird in `ext_branding_config` persistiert.

### 2.2 Logo-Editor nutzen

Der Logo-Upload hat einen integrierten Crop/Zoom-Editor:
- Bild hochladen
- Bereich auswählen (Crop-Handle ziehen)
- Zoom per Slider
- Transparenter Hintergrund optional (Checkbox)
- Speichern → wird auf 256×256 PNG normalisiert

---

## 3. Weitere Whitelabel-Stellen

### 3.1 Browser-Tab-Titel (Core #16)

Core-Datei-Patch #16 (`web/src/providers/DynamicMetadata.tsx`) sorgt dafür, dass der Browser-Tab-Titel nach Soft-Navigation den App-Namen aus `ext_branding_config` behält und nicht auf „Onyx" zurückfällt.

Kein Setup nötig — läuft automatisch bei `EXT_BRANDING_ENABLED=true`.

### 3.2 User-Menu aufräumen (Core #17)

Core-Datei-Patch #17 (`web/src/sections/sidebar/AccountPopover.tsx`) blendet im User-Menu (Klick auf eigenen Namen) die Einträge „Notifications" und „Help & FAQ" aus (Verweis auf `docs.onyx.app` wäre Branding-Verstoß).

Kein Setup nötig — Feature-Flag-gesteuert.

### 3.3 Powered-by-Onyx entfernen

`values-common.yaml`:
```yaml
configMap:
  NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED: "true"
```

Plus Build-Arg im Frontend-Build. Damit verschwindet der „Powered by Onyx"-Footer.

### 3.4 Domain / URL

`values-{env}.yaml`:
```yaml
configMap:
  DOMAIN: "<DEV_DOMAIN>"
  WEB_DOMAIN: "https://<DEV_DOMAIN>"
```

Zusätzlich Ingress-Host:
```yaml
ingress:
  api:
    host: "<DEV_DOMAIN>"
  webserver:
    host: "<DEV_DOMAIN>"
```

---

## 4. Deutsche Lokalisierung (ext-i18n)

Falls gewünscht (bei DE-sprachigen Kunden sinnvoll):

```yaml
# values-common.yaml
configMap:
  NEXT_PUBLIC_EXT_I18N_ENABLED: "true"
  EXT_I18N_ENABLED: "true"
```

Plus Build-Arg `NEXT_PUBLIC_EXT_I18N_ENABLED=true` in `web/Dockerfile` + `stackit-deploy.yml`.

Dictionary liegt unter `web/src/ext/i18n/translations.ts` (~250 Core-Strings + ~115 Admin-Strings). Eigene Strings für Kunden ergänzen:

```typescript
// web/src/ext/i18n/translations.ts
export const translations: Record<string, string> = {
  "Your enterprise AI platform": "<Kunden-spezifische Tagline>",
  // weitere Overrides...
};
```

---

## 5. Validierung

### 5.1 Frontend

- [ ] Browser-Tab-Titel zeigt Kunden-App-Name (nicht „Onyx")
- [ ] Logo oben links in der Sidebar sichtbar
- [ ] Login-Screen zeigt Kunden-Branding (Logo + Tagline)
- [ ] Bei leerem Chat: Greeting-Text sichtbar
- [ ] Disclaimer unter Chat-Antworten
- [ ] User-Menu zeigt nur „Einstellungen" + „Abmelden" (keine Onyx-Links)
- [ ] Kein „Powered by Onyx"-Footer

### 5.2 Admin-UI

- [ ] `/admin/ext/branding` erreichbar
- [ ] Änderungen werden persistiert (reload → sichtbar)
- [ ] Audit-Log zeigt Branding-Änderungen (falls ext-audit aktiv)

### 5.3 Backend

- [ ] `/api/ext/branding/config` liefert 200 mit aktueller Config
- [ ] Magic-Byte-Validierung beim Logo-Upload funktioniert (versuche z. B. `.txt`-Datei umzubenennen, sollte abgelehnt werden)

---

## 6. Typische Fehler

### „404 /api/enterprise-settings/custom-analytics-script" im Browser-Konsolen

Das ist der **Core-#15-Fallstrick**: Der Gate darf nur `useEnterpriseSettings()` aktivieren, **nicht** `useCustomAnalyticsScript()`. Andernfalls sucht SWR nach einem Endpoint, der nur in `backend/ee/` existiert (EE-only), und erzeugt einen Endlos-Retry-Loop.

**Lösung:** `web/src/hooks/useSettings.ts` (Core-Patch #15) prüfen — `useCustomAnalyticsScript` muss auf Upstream-Original bleiben (`EE_ENABLED || eeEnabledRuntime`).

### Browser-Tab zeigt „Onyx" nach Chat-Wechsel

Core-#16 nicht deployed oder `pathname`/`searchParams` fehlen in der `useEffect`-Dep-Liste. Prüfe `web/src/providers/DynamicMetadata.tsx`.

### Logo-Upload liefert 400 „Invalid file type"

Magic-Byte-Validierung erkennt kein PNG/JPEG. Prüfe: ist das File wirklich ein PNG/JPEG (nicht z. B. ein umbenanntes TXT)? `file <datei>` auf der Shell zeigt das echte Format.

### Frontend zeigt immer noch „Onyx" statt Kunden-Namen

Wahrscheinlich ist der Frontend-Build mit `NEXT_PUBLIC_EXT_BRANDING_ENABLED=true` nicht erfolgt. Lösung:
1. `web/Dockerfile` prüfen (beide Stages)
2. `.github/workflows/stackit-deploy.yml` Build-Args prüfen
3. Image neu bauen und deployen
4. Cache-Miss im Browser erzwingen (Hard-Refresh)

---

## 7. Rollback

Whitelabel komplett deaktivieren:

```yaml
# values-common.yaml
configMap:
  EXT_BRANDING_ENABLED: "false"
  NEXT_PUBLIC_EXT_BRANDING_ENABLED: "false"
```

Plus Build-Arg auf `false` + Frontend neu bauen.

Ergebnis: Onyx läuft wieder mit Default-Branding („Onyx" überall).

**Achtung:** Die `ext_branding_config`-Tabelle in der DB bleibt erhalten — bei Wieder-Aktivierung ist die Config sofort da.

---

## 8. Checkliste

- [ ] `EXT_BRANDING_ENABLED=true` in `values-common.yaml`
- [ ] Frontend-Build mit `NEXT_PUBLIC_EXT_BRANDING_ENABLED=true`
- [ ] Core-Dateien #5, #6, #8, #9, #15, #16, #17 aktiv (Pre-commit prüft Whitelist)
- [ ] Admin-UI `/admin/ext/branding` erreichbar
- [ ] Logo hochgeladen (256×256)
- [ ] App-Name gesetzt
- [ ] Login-Tagline angepasst
- [ ] Greeting + Disclaimer eingetragen
- [ ] Browser-Tab zeigt Kunden-Name
- [ ] Kein „Powered by Onyx" sichtbar
- [ ] Bei Bedarf: ext-i18n aktiviert + Dictionary angepasst

---

## 9. Nächster Schritt

→ [ci-cd-pipeline.md](./ci-cd-pipeline.md) — GitHub Actions + Environment Secrets einrichten
