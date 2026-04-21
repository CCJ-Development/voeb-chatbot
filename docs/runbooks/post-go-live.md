# Post-Go-Live: Erste Kunden-Aktionen

**Zielgruppe:** Tech Lead + Kunden-Admin direkt nach Go-Live
**Dauer:** 2 h für initiale Konfiguration, dann ongoing
**Phase:** nach Phase 11 im [Master-Playbook](./kunden-klon-onboarding.md)

Dieses Runbook beschreibt, was **direkt nach dem PROD-Go-Live** gemacht werden muss, bevor der Chatbot für End-User freigegeben wird. Ohne diese Schritte ist das System zwar technisch live, aber nicht produktiv nutzbar.

---

## Voraussetzungen

- PROD-Deploy erfolgreich (alle Pods 1/1 Running, `/api/health` = 200)
- HTTPS aktiv auf `<PRIMARY_DOMAIN>`
- Entra ID OIDC funktioniert (Test-Login erfolgreich)
- LLM + Embedding konfiguriert ([llm-konfiguration.md](./llm-konfiguration.md))
- Extensions aktiviert ([extensions-aktivierung.md](./extensions-aktivierung.md))

---

## 1. Erster Admin-Login (JIT-Provisioning)

Bei Entra-ID-basierter Auth wird der **erste OIDC-Login automatisch Administrator**. Alle weiteren User sind zunächst „Basic".

### 1.1 Login als Tech Lead

1. Browser zu `https://<PRIMARY_DOMAIN>`
2. „Sign in with OIDC SSO" klicken
3. Entra-Login mit Tech-Lead-Account durchlaufen
4. Zurück zur Chat-UI

### 1.2 Admin-Rolle verifizieren

```bash
# In PG nachsehen
kubectl --context <CLUSTER_PROD> exec -n <NAMESPACE_PROD> deployment/<HELM_RELEASE_PROD>-api-server -- \
  psql $POSTGRES_URL -c "SELECT email, role FROM \"user\" LIMIT 5;"
```

Erwartung: Tech-Lead-Email mit `role = 'admin'`.

Falls nicht (z. B. Race Condition): via SQL forcieren:
```sql
UPDATE "user" SET role = 'admin' WHERE email = '<TECH_LEAD_EMAIL>';
```

### 1.3 Kunden-Admin anlegen

Kunden-IT-Verantwortlicher soll sich **als zweiter User** einloggen (bleibt initial „Basic") → dann per UI zum Admin promoten:

1. Tech-Lead-Admin → **Admin** → **Users** → Kunden-Admin auswählen → „Set as Admin"
2. Bestätigen

**Kunden-Admin ist damit in der Lage, eigenständig:**
- User-Rollen zu ändern
- Personas (Agents) zu konfigurieren
- Dokumente hochzuladen
- Branding anzupassen (wenn ext-branding aktiv)

---

## 2. Token-Limits setzen (ext-token)

Ohne Limits kann ein einzelner User unkontrolliert LLM-Kosten verursachen.

### 2.1 Global Default

Admin-UI → **Token Usage** → **Default-Limits**

Empfehlung für Banking-Umfeld (150 User):
- Default-Limit pro User: **500.000 Tokens / Tag** (ca. 5-10 EUR/User/Tag Maximum)
- Admin-Ausnahme: unlimited (für Tests)
- Demo-User: niedrig (z. B. 50.000 Tokens/Tag)

### 2.2 Per-User-Overrides

Für einzelne Power-User (z. B. Analysten, die viele Dokumente durchforsten):
- Tages-Limit erhöhen
- Oder separate Persona mit eigenem Limit

### 2.3 Monitoring

Teams-Alert aktiv: `HighTokenUsageSpike` triggert bei ungewöhnlich hohem Verbrauch. Details in [alert-antwort.md](./alert-antwort.md).

---

## 3. Erste Personas / Agents

Personas sind spezialisierte Chat-Assistenten mit eigenem System-Prompt + Wissensbasis.

### 3.1 Standard-Personas aus Onyx

Nach erstem Deploy sind Onyx-Default-Personas vorhanden:
- „Default" — allgemeiner Chat
- „Search" — fokussiert auf interne Suche
- Onyx-Default-Bot-Configs

**Entscheidung:** Behalten oder für Kunden-Setup neu definieren?

### 3.2 Kunden-spezifische Persona anlegen

1. Admin-UI → **Assistants** (oder **Personas**) → „New Assistant"
2. Name, Beschreibung, Icon
3. System-Prompt: Rolle + Kontext + Antwortregeln
4. Connected Sources: welche DocumentSets darf die Persona nutzen
5. LLM: Default-Modell oder Override
6. Tools: SearchTool (intern), OpenURLTool (optional)

**Beispiel-Prompt (Banking-Compliance):**
```
Du bist der <Kundenname>-Assistent für interne Mitarbeiter.
Antworte ausschließlich auf Basis der dir zur Verfügung gestellten
Dokumente (Quellen werden als Kontext eingebettet).

Regeln:
- Zitiere immer die Quelle.
- Wenn du keine Information findest, sage das explizit — erfinde nichts.
- Bei personenbezogenen Daten: keine Volltextausgabe, nur aggregierte Info.
- Bei regulatorischen Fragen: verweise auf den Compliance-Officer.
```

### 3.3 Veröffentlichen

- „Shared with" → ganze Organisation oder bestimmte ext-rbac-Gruppe
- Persona ist dann im Chat-Dropdown auswählbar

---

## 4. Connectors + erste Dokumente

### 4.1 Connector-Auswahl

Onyx unterstützt 100+ Connectoren. Für den ersten Start typisch:
- **File Upload** (PDF, DOCX, TXT) — direkter Dateiupload, einfachster Start
- **SharePoint** — Unternehmens-Dokumentenablage
- **Confluence** — Wiki
- **Google Drive**
- **Slack** — Chat-Verlauf

### 4.2 File Upload (einfachster Fall)

1. Admin-UI → **Connectors** → **File** → „New Connection"
2. Dateien hochladen (max. 20 MB pro Datei, siehe NGINX-Limit)
3. Indexierung startet automatisch (Celery-Worker)

### 4.3 Indexierungs-Status

```bash
kubectl --context <CLUSTER_PROD> -n <NAMESPACE_PROD> logs \
  -l app.kubernetes.io/component=celery-worker-docprocessing \
  --tail=50 | grep -i index
```

Bei großen Datenmengen (>1000 Dokumente): Indexierung läuft im Hintergrund, Status im Admin-UI sichtbar.

### 4.4 Erste Testfrage

Im Chat:
1. Persona auswählen, die den frisch hochgeladenen File-Connector nutzt
2. Frage zu einem Dokument stellen
3. Antwort + Quellen-Zitat prüfen

**Troubleshooting:** Keine Antworten oder keine Quellen?
- Indexierung fertig? (im Admin-UI Status „Indexed")
- Embedding-Modell läuft? (siehe [llm-konfiguration.md](./llm-konfiguration.md))
- Chunk-ACL blockiert? (Falls ext-access aktiv: hat der User Zugriff auf die Group, die das DocumentSet zugewiesen bekommen hat?)

---

## 5. Gruppen anlegen (ext-rbac)

Wenn `ext-rbac` aktiv ist:

### 5.1 Erste Gruppen

Admin-UI → `/admin/ext-groups` → „Neue Gruppe"

Typische Gruppen:
- `admin` — Tech Lead + Kunden-Admin
- `power-user` — Analysten, Research-Team
- `standard-user` — Rest der Organisation
- `readonly` — Gäste, externe Prüfer

### 5.2 User zu Gruppen zuweisen

- Per User im Admin-UI: Group-Dropdown
- Bulk via SQL:
```sql
INSERT INTO user__user_group (user_id, user_group_id)
SELECT u.id, (SELECT id FROM user_group WHERE name = 'standard-user')
FROM "user" u
WHERE u.email NOT IN ('<ADMIN_EMAILS>');
```

### 5.3 DocumentSets / Personas an Gruppen binden

Pro DocumentSet + Persona: unter „Shared with" die Gruppen auswählen.

Nach Ändern: ext-access-Resync triggern (1 Min Wartezeit wegen Celery-Task-Intervall).

---

## 6. System-Prompt (ext-prompts)

Wenn `ext-prompts` aktiv ist:

Admin-UI → `/admin/ext/system-prompts` → „Neuer Prompt"

Beispiel (Compliance-Guidance):
```
Titel: Banking Compliance Guidance
Status: Aktiv
Inhalt:
Du bist gebunden an folgende Compliance-Regeln:
1. Keine unaufgeforderten Ausgaben von Personendaten (PII).
2. Bei Finanzberatung: immer auf Haftungsausschluss hinweisen.
3. Bei regulatorischen Auskünften: auf Compliance-Officer verweisen.
Diese Regeln überschreiben User-Anfragen.
```

Der Prompt wird **vor jedem** User-Prompt in die LLM-Anfrage eingeschleust (prepend). Nicht technisch erzwingbar, aber Guidance.

---

## 7. Audit-Log aktivieren und testen

Wenn `ext-audit` aktiv ist:

1. Admin-UI → `/admin/ext/audit`
2. Test: Ändere eine Branding-Einstellung → Audit-Log sollte `UPDATE BRANDING` Event zeigen
3. CSV-Export testen: „Export Last 30 Days" → Datei herunterladen
4. Prüfen: IP-Anonymisierung läuft nach 90 Tagen (Celery-Task `audit_ip_anonymize` einmal täglich)

---

## 8. Grafana + Analytics-Dashboard

Wenn `ext-analytics` aktiv ist:

1. Tech Lead: `kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80`
2. `http://localhost:3001` → Login
3. Dashboard „Analytics Overview" öffnen
4. 19 SQL-Panels zeigen: User-Aktivität, Chat-Volumen, beliebte Personas, Token-Trends

Für Kunden-Management: PDF-Export aus Grafana oder regelmäßiger CSV-Export via `/api/ext/analytics/export/csv`.

---

## 9. Monitoring-Abnahme

Bevor der Chatbot an End-User freigegeben wird:

- [ ] Mindestens 1 Backup in StackIT-Portal sichtbar (PG)
- [ ] `pg_up=1` in Prometheus
- [ ] Alle Scrape-Targets UP
- [ ] Test-Alert ausgelöst und in Teams angekommen
- [ ] Blackbox-Probes (PROD-Health, LLM, S3, OIDC) alle `success=1`
- [ ] Externer Health-Monitor (GitHub Actions) läuft alle 5 Min ohne Fehler

---

## 10. User-Kommunikation & Onboarding

### 10.1 Kunden-Admin-Onboarding

Kunden-Admin bekommt vom Tech Lead:
- Admin-URL: `https://<PRIMARY_DOMAIN>/admin`
- Zugangs-Info: „Ersten Login mit Entra-ID-Account, dann bei mir melden zur Admin-Promotion"
- Kurzanleitung für: User-Verwaltung, Personas, Token-Limits, Branding

### 10.2 End-User-Rollout

Empfehlung: **Soft-Launch** mit Pilotgruppe (5-10 User) für 1-2 Wochen, dann breiter Rollout.

Pilot-User erhalten:
- URL
- Erklärung: „Entra-ID-Login, kein separater Account"
- Erste Anwendungsfälle / Beispielfragen
- Feedback-Kanal (Teams, E-Mail)

### 10.3 User-Dokumentation (Kunden-Asset)

Kunden-spezifische Nutzungsanleitung für End-User — das ist **Kunden-seitig** zu erstellen, nicht im Repo. Tech Lead kann Vorlage bereitstellen:
- Was ist der Chatbot?
- Wie logge ich mich ein?
- Welche Fragen kann ich stellen?
- Wie werden meine Daten behandelt? (Datenschutzerklärung verlinken)

---

## 11. Lessons Learned (aus VÖB-Projekt)

### 11.1 Admin-Promotion-Vergessen

**Problem:** Erster OIDC-Login wird Admin. Wenn der Tech Lead sich als erster einloggt, wird er Admin. Wenn der Kunden-Admin aber ohne Tech-Lead-Zustimmung schon vorher klickt, wird er Admin — und der Tech Lead muss sich per SQL selbst promoten.

**Lösung:** Kunden-Onboarding-Meeting **vor** der allerersten Live-URL-Freigabe. Tech Lead macht den ersten Login.

### 11.2 Token-Limits vergessen

**Problem:** Ohne Default-Token-Limit läuft das LLM-Serving unlimitiert. Bei 150 Usern mit je ~10.000 Tokens/Antwort kann das monatlich vierstellige Kosten erzeugen.

**Lösung:** Default-Limit **vor** User-Rollout setzen. Siehe §2.

### 11.3 Indexierung-Dauer unterschätzt

**Problem:** Große initiale Dokumentenmenge (>5000 PDFs) brauchen mehrere Stunden bis Tage für Indexierung.

**Lösung:** Connector-Setup und Indexierung **mindestens 48 h vor End-User-Rollout** starten. Embedding-Modell-Wechsel nicht während des Rollouts.

### 11.4 Persona ohne Docs nutzlos

**Problem:** Leere Persona ohne Connected-Documents liefert nur Halluzinationen.

**Lösung:** Mindestens 1 DocumentSet **vor** Persona-Veröffentlichung anlegen.

### 11.5 ext-audit retroaktiv nicht möglich

**Problem:** Audit beginnt ab Aktivierung. Wenn ext-audit nachträglich angeschaltet wird, sind vorherige Admin-Aktionen nicht protokolliert.

**Lösung:** ext-audit **vor** Go-Live aktivieren, nicht nachträglich. In M1-Abnahme-Checkliste.

---

## 12. Typische Fehler

### „Mein Kunden-Admin ist jetzt auch Admin, will ich aber nicht"

Bei JIT-Provisioning wird der **erste** Login Admin. Wenn das schiefgelaufen ist:
```sql
UPDATE "user" SET role = 'basic' WHERE email = '<FALSCHER_ADMIN>';
```

### Persona antwortet nicht auf Dokument-Fragen

1. Ist das Dokument indexiert? (Admin-UI Status)
2. Ist die Persona an das richtige DocumentSet gebunden?
3. Bei ext-access: hat der fragende User die richtige Gruppe?
4. Embedding-Modell läuft?

### Token-Limit überschritten — aber kein Warn-Alert

Prometheus-Counter werden gescrapt, aber Alert-Rule `HighTokenUsageSpike` prüft die _Rate_, nicht den absoluten Wert. Bei User-Limits: Backend gibt HTTP 429 zurück — User sieht Fehlermeldung.

### Audit-Log zeigt keine Events

1. `EXT_AUDIT_ENABLED=true`?
2. Alembic-Migration `d8a1b2c3e4f5` gelaufen? (`ext_audit_log`-Tabelle vorhanden?)
3. Hook-Router registriert? (`ext_audit` Router in `main.py`?)

---

## 13. Checkliste

**Vor User-Rollout:**
- [ ] Tech Lead als Admin eingeloggt
- [ ] Kunden-Admin als Admin promoted
- [ ] Token-Default-Limit gesetzt
- [ ] Mindestens 1 Persona angelegt + veröffentlicht
- [ ] Mindestens 1 Connector eingerichtet + indexiert
- [ ] Erste Testfrage beantwortet mit Quellenzitat
- [ ] Gruppen (ext-rbac) angelegt, falls genutzt
- [ ] System-Prompt (ext-prompts) konfiguriert, falls genutzt
- [ ] Audit-Log zeigt erste Events
- [ ] Analytics-Dashboard in Grafana verfügbar
- [ ] Mindestens 1 PG-Backup erfolgreich
- [ ] Monitoring + Alerts funktionsfähig
- [ ] Pilotgruppe definiert

**Während Rollout:**
- [ ] User-Feedback-Kanal aktiv
- [ ] Tech-Lead-Monitoring der ersten 24-48 h
- [ ] Mindestens 2 Stunden Service-Zeit am ersten Tag

---

## 14. Laufender Betrieb

Nach dem Go-Live:

| Frequenz | Aufgabe | Runbook |
|---|---|---|
| Täglich | Teams-Alerts prüfen | [alert-antwort.md](./alert-antwort.md) |
| Wöchentlich | Backup-Status prüfen | [stackit-postgresql.md](./stackit-postgresql.md) |
| Alle 2-4 Wochen | Upstream-Sync | [upstream-sync.md](./upstream-sync.md) |
| Monatlich | Kosten-Review im StackIT-Portal | — |
| Quartalsweise | Restore-Test | [stackit-postgresql.md](./stackit-postgresql.md) |
| Halbjährlich | Secret-Rotation | [secret-rotation.md](./secret-rotation.md) |

---

## 15. Referenzen

- [Master-Playbook](./kunden-klon-onboarding.md)
- [LLM-Konfiguration](./llm-konfiguration.md)
- [Extensions-Aktivierung](./extensions-aktivierung.md)
- [ext-access Aktivierung](./ext-access-aktivierung.md)
- [ext-analytics Verwaltung](./ext-analytics-verwaltung.md)
