# Runbook: Entra ID (OIDC) Konfiguration

**Projekt:** VÖB Chatbot
**Stand:** 2026-03-22
**Autor:** COFFEESTUDIOS (Nikolaj Ivanov)

---

## Voraussetzungen

- HTTPS aktiv auf der Ziel-Umgebung (Pflicht fuer OIDC)
- Entra ID App Registration durch VÖB IT erstellt
- 3 Credentials von VÖB erhalten: Client ID, Tenant ID, Client Secret
- Niko als User in Entra ID aufgenommen (B2B-Gastbenutzer)

## Architektur

### Auth-Flow

```
User → Login-Seite → "Continue with OIDC SSO"
  → /api/auth/oidc/authorize (State + PKCE generieren, Cookies setzen)
  → Redirect zu login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
  → User authentifiziert sich bei Microsoft
  → Callback zu /auth/oidc/callback?code=...&state=...
  → Backend: Code Exchange → Access Token → Userinfo → User erstellen/aktualisieren
  → Session Cookie → Redirect zu /
```

### Wichtige Architektur-Entscheidungen

| Aspekt | Entscheidung | Begruendung |
|--------|-------------|-------------|
| AUTH_TYPE | `oidc` (exklusiv) | Onyx unterstuetzt nur einen AUTH_TYPE gleichzeitig. E-Mail/Passwort ist NICHT gleichzeitig moeglich. |
| PKCE | Aktiviert (`OIDC_PKCE_ENABLED=true`) | Security Best Practice, verhindert Authorization Code Interception |
| User Provisioning | JIT (Just-In-Time) | OIDC/SAML User werden beim ersten Login automatisch in Onyx angelegt |
| Erster User | Wird automatisch ADMIN | Alle weiteren User werden BASIC. Steuerbar ueber Admin UI. |
| Session-Dauer | 7 Tage (Default) | `SESSION_EXPIRE_TIME_SECONDS=604800`. Aenderbar per Env Var. |
| IDP Expiry Tracking | Deaktiviert (Default) | `TRACK_EXTERNAL_IDP_EXPIRY=false`. Bei Aktivierung: Session endet wenn Entra-Token ablaeuft. |
| Claims→Roles Mapping | Nicht vorhanden | Onyx liest keine Gruppen/Rollen aus dem OIDC-Token. Rollen werden manuell zugewiesen. |

## Redirect URI

**KRITISCH:** Diese URI muss EXAKT in der Entra ID App Registration eingetragen sein.

| Umgebung | Redirect URI |
|----------|-------------|
| DEV | `https://dev.chatbot.voeb-service.de/auth/oidc/callback` |
| PROD | `https://chatbot.voeb-service.de/auth/oidc/callback` |

**Typ in Entra ID:** Web (nicht SPA, nicht Mobile)

Code-Referenz: `backend/onyx/main.py:622` — `redirect_url=f"{WEB_DOMAIN}/auth/oidc/callback"`

## Entra ID App Registration — Checkliste

### Von VÖB IT zu konfigurieren

- [ ] **Redirect URI** (unter Authentifizierung → Plattformkonfigurationen → Web)
  - DEV: `https://dev.chatbot.voeb-service.de/auth/oidc/callback`
  - PROD: `https://chatbot.voeb-service.de/auth/oidc/callback`
- [ ] **Unterstuetzte Kontotypen:** Nur Konten in diesem Organisationsverzeichnis (Single-Tenant)
- [ ] **API-Berechtigungen** (mit Admin Consent):
  - Microsoft Graph → `openid` (delegiert)
  - Microsoft Graph → `email` (delegiert)
  - Microsoft Graph → `profile` (delegiert)
  - Microsoft Graph → `offline_access` (delegiert, fuer Refresh Tokens)
- [ ] **Token-Konfiguration:**
  - ID-Token aktiviert
  - Optional Claims: `email`, `preferred_username`
- [ ] **Client Secret:** Erstellt, Ablaufdatum dokumentiert
- [ ] **User Assignment:** Entscheidung ob "Required" (nur zugewiesene User) oder offen

### Von VÖB IT zu bestaetigen

- [ ] Niko (B2B-Gastbenutzer) ist in Entra ID aufgenommen
- [ ] Keine Conditional Access Policies die den Zugriff blockieren
  - Falls doch: StackIT Egress-IP `188.34.93.194` (DEV) / `188.34.73.72` (PROD) whitelisten
- [ ] MFA-Anforderungen dokumentiert (beeinflusst Login-Flow)

## GitHub Secrets

### DEV Environment

| Secret | Beschreibung | Wert |
|--------|-------------|------|
| `ENTRA_CLIENT_ID` | Anwendungs-ID (Client ID) aus App Registration | UUID von VÖB |
| `ENTRA_CLIENT_SECRET` | Geheimer Schluessel (Client Secret Value) | String von VÖB |
| `ENTRA_TENANT_ID` | Verzeichnis-ID (Tenant ID) | UUID von VÖB |
| `USER_AUTH_SECRET` | JWT Signing Secret fuer OIDC State Tokens | `openssl rand -hex 32` |

### Befehle

```bash
# USER_AUTH_SECRET generieren
openssl rand -hex 32

# GitHub Secrets setzen (Werte interaktiv eingeben)
gh secret set ENTRA_CLIENT_ID -R CCJ-Development/voeb-chatbot --env dev
gh secret set ENTRA_CLIENT_SECRET -R CCJ-Development/voeb-chatbot --env dev
gh secret set ENTRA_TENANT_ID -R CCJ-Development/voeb-chatbot --env dev
gh secret set USER_AUTH_SECRET -R CCJ-Development/voeb-chatbot --env dev
```

**ACHTUNG:** Werte NIEMALS in Logs, Commits oder Prompts. Immer interaktiv eingeben.

## Helm Values

### ConfigMap (in values-dev.yaml, committed)

```yaml
configMap:
  AUTH_TYPE: "oidc"
  OIDC_PKCE_ENABLED: "true"
  # OPENID_CONFIG_URL wird per --set im CI/CD konstruiert (enthaelt Tenant ID)
  # VALID_EMAIL_DOMAINS: "voeb.de"  # Optional: Einschraenkung auf VÖB-Domains
```

### Secrets (per --set im CI/CD, nicht committed)

```yaml
auth:
  oauth:
    enabled: true
    secretName: "onyx-oauth"
    values:
      oauth_client_id: ""       # per --set
      oauth_client_secret: ""   # per --set
  userauth:
    enabled: true
    secretName: "onyx-userauth"
    values:
      user_auth_secret: ""      # per --set
```

### CI/CD --set Flags (in stackit-deploy.yml, deploy-dev Job)

```bash
--set "auth.oauth.values.oauth_client_id=${{ secrets.ENTRA_CLIENT_ID }}"
--set "auth.oauth.values.oauth_client_secret=${{ secrets.ENTRA_CLIENT_SECRET }}"
--set "auth.userauth.values.user_auth_secret=${{ secrets.USER_AUTH_SECRET }}"
--set "configMap.OPENID_CONFIG_URL=https://login.microsoftonline.com/${{ secrets.ENTRA_TENANT_ID }}/v2.0/.well-known/openid-configuration"
```

## Manueller Deploy (erster Test)

```bash
# Nur fuer den ersten Test — danach CI/CD nutzen.
# ACHTUNG: Werte NICHT in Shell-History speichern!
# Empfehlung: read -s Variablen verwenden.

read -s -p "ENTRA_CLIENT_ID: " CLIENT_ID && echo
read -s -p "ENTRA_CLIENT_SECRET: " CLIENT_SECRET && echo
read -s -p "ENTRA_TENANT_ID: " TENANT_ID && echo
read -s -p "USER_AUTH_SECRET: " AUTH_SECRET && echo

helm upgrade onyx-dev deployment/helm/charts/onyx/ \
  -n onyx-dev \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-dev.yaml \
  --set "global.version=latest" \
  --set "auth.postgresql.values.password=<PG-PW>" \
  --set "auth.redis.values.redis_password=<REDIS-PW>" \
  --set "auth.objectstorage.values.s3_aws_access_key_id=<S3-KEY>" \
  --set "auth.objectstorage.values.s3_aws_secret_access_key=<S3-SECRET>" \
  --set "auth.dbreadonly.values.db_readonly_password=<RO-PW>" \
  --set "auth.oauth.values.oauth_client_id=${CLIENT_ID}" \
  --set "auth.oauth.values.oauth_client_secret=${CLIENT_SECRET}" \
  --set "auth.userauth.values.user_auth_secret=${AUTH_SECRET}" \
  --set "configMap.OPENID_CONFIG_URL=https://login.microsoftonline.com/${TENANT_ID}/v2.0/.well-known/openid-configuration" \
  --wait --timeout 15m

# Variablen sofort loeschen
unset CLIENT_ID CLIENT_SECRET TENANT_ID AUTH_SECRET
```

## Validierung

### 1. Pods pruefen

```bash
kubectl get pods -n onyx-dev
# Erwartet: Alle Pods restarten (neue ConfigMap + neue Secrets)

# API-Server Logs — Auth-Konfiguration pruefen
kubectl logs -n onyx-dev -l app=api-server --tail=50 | grep -i "oauth\|oidc\|auth"
```

### 2. ConfigMap verifizieren

```bash
kubectl get configmap env-configmap -n onyx-dev -o jsonpath='{.data.AUTH_TYPE}'
# Erwartet: oidc

kubectl get configmap env-configmap -n onyx-dev -o jsonpath='{.data.OPENID_CONFIG_URL}'
# Erwartet: https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration
```

### 3. Secrets verifizieren

```bash
kubectl get secret onyx-oauth -n onyx-dev -o jsonpath='{.data.oauth_client_id}' | base64 -d
# Erwartet: Die Entra ID Client ID

kubectl get secret onyx-userauth -n onyx-dev
# Erwartet: Secret existiert
```

### 4. Login testen

```
1. Oeffne: https://dev.chatbot.voeb-service.de
2. Login-Seite zeigt "Continue with OIDC SSO" Button
3. Klick → Microsoft Login-Seite (login.microsoftonline.com)
4. Anmelden mit Entra ID Credentials
5. Redirect zurueck zum Chatbot
6. User ist eingeloggt
```

## Troubleshooting

### "redirect_uri mismatch" / "AADSTS50011: Reply URL does not match"

**Ursache:** Redirect URI in Entra ID App Registration stimmt nicht mit der von Onyx gesendeten ueberein.

**Diagnose:**
```bash
# Browser DevTools → Network → Filter "authorize"
# Suche nach redirect_uri Parameter in der Authorization URL
```

**Fix:** Die exakte URI `https://dev.chatbot.voeb-service.de/auth/oidc/callback` in Entra ID eintragen (Typ: Web).

### "AADSTS7000218: Request body must contain client_assertion or client_secret"

**Ursache:** Client Secret fehlt oder falsch konfiguriert.

**Diagnose:**
```bash
kubectl get secret onyx-oauth -n onyx-dev -o yaml
# Pruefen ob oauth_client_secret gesetzt ist
```

### "AADSTS700016: Application not found in tenant"

**Ursache:** Client ID oder Tenant ID falsch, oder App Registration in falschem Tenant.

**Diagnose:**
```bash
# OPENID_CONFIG_URL pruefen — ist die Tenant ID korrekt?
kubectl get configmap env-configmap -n onyx-dev -o jsonpath='{.data.OPENID_CONFIG_URL}'

# URL manuell aufrufen — muss JSON zurueckgeben
curl -s "https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration" | jq .issuer
```

### "AADSTS65001: Invalid grant" / Admin Consent fehlt

**Ursache:** API-Berechtigungen nicht mit Admin Consent erteilt.

**Fix:** VÖB IT muss in Azure Portal → App Registration → API-Berechtigungen → "Admin Consent erteilen" klicken.

### Login-Seite zeigt keinen SSO-Button

**Ursache:** AUTH_TYPE nicht korrekt gesetzt.

**Diagnose:**
```bash
kubectl exec -n onyx-dev deploy/onyx-dev-api-server -- env | grep AUTH_TYPE
# Erwartet: AUTH_TYPE=oidc

kubectl exec -n onyx-dev deploy/onyx-dev-api-server -- env | grep OAUTH_CLIENT_ID
# Erwartet: OAUTH_CLIENT_ID=<uuid>
```

### Nach Login: 403 Forbidden

**Ursache:** User existiert aber hat keine passende Rolle, oder User ist deaktiviert.

**Diagnose:**
```bash
# Onyx DB pruefen
docker exec -it onyx-relational_db-1 psql -U postgres -c "SELECT email, role, is_active FROM public.user_"
# Oder auf StackIT:
kubectl exec -n onyx-dev deploy/onyx-dev-api-server -- python -c "
from onyx.db.engine import get_session_context_manager
from onyx.db.models import User
with get_session_context_manager() as session:
    for u in session.query(User).all():
        print(f'{u.email} | role={u.role} | active={u.is_active}')
"
```

### Nach Login: Redirect-Loop

**Ursache:** Cookie-Problem (Secure-Flag, Domain, SameSite) oder WEB_DOMAIN falsch.

**Diagnose:**
```bash
kubectl get configmap env-configmap -n onyx-dev -o jsonpath='{.data.WEB_DOMAIN}'
# MUSS https:// sein, nicht http://

# Browser: DevTools → Application → Cookies → Pruefen ob Session Cookie gesetzt wird
```

### PKCE-Fehler: "invalid_grant" mit "code_verifier" im Log

**Ursache:** PKCE Code Verifier Cookie geht verloren (z.B. durch Proxy/WAF).

**Fix:**
```yaml
# Temporaer PKCE deaktivieren zum Testen:
configMap:
  OIDC_PKCE_ENABLED: "false"
```

## Rollenkonzept (Phase 4f, wartet auf VÖB)

### Onyx-Rollen (FOSS)

| Rolle | Beschreibung |
|-------|-------------|
| `ADMIN` | Voller Admin-Zugang (Personas, Connectors, Users, Settings) |
| `BASIC` | Standard-User (Chat, Suche) |
| `LIMITED` | Eingeschraenkter API-Zugang |
| `CURATOR` | Kann Gruppen kuratieren (EE — nachgebaut in ext-rbac) |
| `GLOBAL_CURATOR` | Kuratiert alle Gruppen (EE — nachgebaut in ext-rbac) |

### Rollen-Zuweisung

- **Erster OIDC-Login:** Automatisch `ADMIN`
- **Alle weiteren:** Automatisch `BASIC`
- **Aendern:** Per Admin UI (Settings → Users)
- **Kein automatisches Mapping** von Entra ID Gruppen auf Onyx-Rollen
- **Automatisches Mapping:** Kommt mit `ext-rbac` (Phase 4f, blockiert durch Entra ID)

### Was VÖB entscheiden muss (spaeter)

1. Welche Entra ID Gruppen sollen Zugang haben?
2. Welche Rolle bekommt ein neuer User standardmaessig?
3. Wer wird Admin? (Erster Login = Admin!)
4. Sollen Entra ID Gruppen auf Onyx-Rollen gemappt werden?
5. Soll `VALID_EMAIL_DOMAINS` gesetzt werden? (z.B. `voeb-service.de,scale42.de`)
   - **Aktuell leer** (keine Einschraenkung) — Niko nutzt `n.ivanov@scale42.de` als B2B-Gast
   - Falls aktiviert: BEIDE Domains noetig (`voeb-service.de,scale42.de`)

## Secret-Rotation

| Secret | Ablaufdatum | Verantwortlich | Rotation |
|--------|-----------|----------------|----------|
| Client Secret | **2028-03-13** (720 Tage, erstellt 2026-03-23) | VÖB IT | Neues Secret in Entra ID erstellen (VALUE kopieren!), GitHub Secret aktualisieren, re-deploy. **Reminder: 2028-02-20** (3 Wochen vorher) |
| USER_AUTH_SECRET | Kein Ablauf | CCJ | Bei Kompromittierung: `openssl rand -hex 32`, GitHub Secret aktualisieren |
| ENTRA_TENANT_ID | Permanent | VÖB | Aendert sich nie |
| ENTRA_CLIENT_ID | Permanent (solange App Registration existiert) | VÖB | Aendert sich nur bei Neuanlage |

## Lessons Learned (DEV-Aktivierung 2026-03-23)

### 1. Client Secret ID vs. Value
**Problem:** VÖB hat die **Secret ID** (Bezeichner) statt den **Secret Value** (eigentlicher Schluessel) uebergeben. Microsoft meldet `AADSTS7000215: Invalid client secret provided`.

**Hintergrund:** In Entra ID gibt es pro Client Secret zwei Werte:
- **ID:** Immer sichtbar, UUID-Format, identifiziert das Secret
- **Wert (Value):** Nur einmalig nach Erstellung sichtbar, der eigentliche Schluessel

**Diagnose:**
```bash
# Client Credentials Grant testen (braucht keinen User-Login):
kubectl exec -n onyx-dev deploy/onyx-dev-api-server -- python3 -c "
import os, urllib.request, urllib.parse, json
data = urllib.parse.urlencode({
    'grant_type': 'client_credentials',
    'client_id': os.environ['OAUTH_CLIENT_ID'],
    'client_secret': os.environ['OAUTH_CLIENT_SECRET'],
    'scope': 'https://graph.microsoft.com/.default',
}).encode()
req = urllib.request.Request(
    'https://login.microsoftonline.com/' + os.environ.get('OPENID_CONFIG_URL','').split('/')[3] + '/oauth2/v2.0/token',
    data=data)
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print('SECRET OK')
except urllib.error.HTTPError as e:
    body = json.loads(e.read().decode())
    print(f'{body[\"error\"]}: {body[\"error_description\"][:200]}')
    # invalid_client = Secret falsch
    # unauthorized_client = Secret korrekt, aber Grant Type nicht erlaubt
"
```

**Fix:** VÖB muss neues Secret erstellen und den **Wert** (nicht die ID) uebermitteln.

### 2. PKCE Cookie geht durch NGINX Proxy verloren
**Problem:** `OIDC_PKCE_ENABLED=true` fuehrt zu `Missing PKCE verifier cookie in OAuth callback` und Redirect-Loop.

**Ursache:** Der PKCE Code Verifier wird als Cookie gesetzt (`/auth/oidc/authorize`). Der Callback kommt aber ueber Next.js (Server-Side Fetch), das die Cookies zwar weiterleitet, aber das PKCE-Cookie erreicht den Backend-Callback nicht zuverlaessig.

**Entscheidung:** PKCE deaktiviert (`OIDC_PKCE_ENABLED=false`). Kein Security-Risiko — wir sind ein Confidential Client mit serverseitigem Client Secret. PKCE ist fuer Public Clients (Mobile Apps, SPAs ohne Secret) konzipiert.

### 3. Fehlende Error-Logs bei OIDC 500
**Problem:** Token Exchange Fehler werden als HTTP 500 zurueckgegeben, aber NICHT geloggt. Die `httpx-oauth` Library faengt `GetAccessTokenError` und wirft `OAuth2AuthorizeCallbackError(status_code=500)`, die von FastAPI als HTTPException behandelt wird — ohne Traceback.

**Workaround fuer Debugging:**
```bash
# Manuelle Token Exchange Simulation (zeigt Microsoft-Fehlermeldung):
kubectl exec -n onyx-dev deploy/onyx-dev-api-server -- python3 -c "
import os, urllib.request, urllib.parse, json
# ... (siehe Diagnose-Script oben)
"
```

### 4. Redirect URI Tippfehler
**Problem:** VÖB IT hat URIs mit `voebservice` statt `voeb-service` (Bindestrich fehlte) eingetragen. Fuehrt zu `AADSTS50011: Reply URL does not match`.

**Fix:** URIs in Entra ID bereinigen. Korrekte URIs:
- DEV: `https://dev.chatbot.voeb-service.de/auth/oidc/callback`
- PROD: `https://chatbot.voeb-service.de/auth/oidc/callback`

### 5. Debug-Env-Vars nach Troubleshooting entfernen
Nach erfolgreichem Login-Test muessen die temporaeren Debug-Variablen entfernt werden:
```bash
kubectl set env deploy/onyx-dev-api-server -n onyx-dev LOG_LEVEL=INFO UVICORN_LOG_LEVEL- FASTAPI_DEBUG-
```

## PROD-Rollout (nach erfolgreicher DEV-Validierung)

1. Gleiche GitHub Secrets im `prod` Environment setzen
2. `values-prod.yaml`: `AUTH_TYPE: "oidc"`, `OIDC_PKCE_ENABLED: "false"`, `auth.oauth` + `auth.userauth` aktivieren
3. `stackit-deploy.yml`: `--set` Flags im deploy-prod Job ergaenzen
4. Redirect URI `https://chatbot.voeb-service.de/auth/oidc/callback` in Entra ID eintragen (bereits vorhanden)
5. `VALID_EMAIL_DOMAINS` setzen (nach VÖB-Vorgabe)
6. `TRACK_EXTERNAL_IDP_EXPIRY` entscheiden (Standard vs. Strikt)
7. Deploy + Validierung

## Offene Punkte vor PROD-Rollout

### P1: OIDC Error-Logging (Kritisch)
**Problem:** Token Exchange Fehler (httpx-oauth `GetAccessTokenError`) werden als HTTP 500 zurueckgegeben aber NICHT geloggt. Debugging dauerte Stunden.
**Loesung:** Middleware in `backend/ext/` die 500er auf `/auth/oidc/callback` abfaengt und den Response-Body loggt (enthaelt Microsoft-Fehlercode).
**Aufwand:** Niedrig (1 Middleware-Datei in ext/).

### P2: Auth-spezifischer Prometheus Alert (Hoch)
**Problem:** Der bestehende `HighErrorRate` Alert (>5% 5xx) greift nicht zuverlaessig fuer Auth-Fehler — bei normalem API-Traffic gehen einzelne Login-500er im Rauschen unter.
**Loesung:** Dedizierter Alert auf `onyx_api_requests_by_tenant_total{handler="/auth/oidc/callback",status="500"}`.
```yaml
- alert: OIDCCallbackFailure
  expr: increase(onyx_api_requests_by_tenant_total{handler="/auth/oidc/callback",status="500"}[10m]) > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "OIDC Login fehlgeschlagen ({{ $labels.environment }})"
    description: "Token Exchange auf /auth/oidc/callback gibt 500 zurueck. Pruefen: Client Secret abgelaufen? Entra ID erreichbar?"
```
**Aufwand:** Niedrig (AlertRule in values-monitoring.yaml).

### P3: Client Secret Ablauf-Monitoring (Hoch) — TEILWEISE ERLEDIGT
**Problem:** Wenn das Entra ID Client Secret ablaeuft, bricht der Login ohne Vorwarnung.
**Ablaufdatum:** **2028-03-13** (720 Tage ab Erstellung 2026-03-23).
**Erledigt:** Ablaufdatum im Runbook dokumentiert (Secret-Rotation Tabelle).
**Offen:** Kalender-Reminder fuer 2028-02-20 setzen (3 Wochen vorher). Langfristig: Cronjob der den `client_credentials` Grant testet.
**Aufwand:** Niedrig (Reminder) / Mittel (Cronjob).

### P4: Login-Audit-Log (Mittel, Compliance)
**Problem:** Keine Aufzeichnung wer sich wann erfolgreich/erfolglos angemeldet hat. Fuer DSGVO/BSI-Grundschutz relevant.
**Loesung:** `on_after_login` Hook in `backend/ext/` der erfolgreiche Logins loggt (User-Email, Zeitpunkt, IP). Fehlgeschlagene Logins ueber P1 (Error-Logging) abgedeckt.
**Aufwand:** Mittel (ext/-Modul mit DB-Tabelle oder strukturiertem Log).

### P5: Debug-Env-Vars zuruecksetzen (nach Login-Test)
```bash
kubectl set env deploy/onyx-dev-api-server -n onyx-dev LOG_LEVEL=INFO UVICORN_LOG_LEVEL- FASTAPI_DEBUG-
```

## Aenderungshistorie

| Version | Datum | Autor | Aenderung |
|---------|-------|-------|----------|
| 1.3 | 2026-03-23 | COFFEESTUDIOS | DEV Login erfolgreich, Secret-Ablauf 2028-03-13 dokumentiert, Debug-Vars zurueckgesetzt |
| 1.2 | 2026-03-23 | COFFEESTUDIOS | 5 offene Punkte vor PROD dokumentiert (Error-Logging, Alert, Secret-Ablauf, Audit-Log, Debug-Vars) |
| 1.1 | 2026-03-23 | COFFEESTUDIOS | PKCE deaktiviert, Lessons Learned (Secret ID/Value, Logs, Redirect Tippfehler) |
| 1.0 | 2026-03-22 | COFFEESTUDIOS | Erstversion (DEV-Konfiguration) |
