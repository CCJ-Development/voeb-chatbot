# Runbook: ext-access Aktivierung (Document Access Control)

> **Wann:** Erstmalige Aktivierung auf einer Umgebung (DEV/PROD).
> **Voraussetzung:** ext-rbac aktiv, Gruppen mit CC-Pair-Zuordnungen angelegt.
> **Dauer:** ~10 Minuten.
> **Risiko:** Niedrig — Flag ist sofort abschaltbar.

---

## Vorbedingungen pruefen

```bash
# 1. ext-rbac muss aktiv sein (Gruppen muessen existieren)
curl -s https://<DOMAIN>/api/manage/admin/user-group | python3 -m json.tool | head -5

# 2. Gruppen muessen CC-Pairs zugewiesen haben
# (ohne CC-Pair-Zuordnung hat der Resync keinen Effekt)
```

Falls keine Gruppen mit CC-Pairs existieren: Erst in der Admin-UI unter
`/admin/ext-groups` Gruppen anlegen und Connectoren zuweisen.

---

## Aktivierung

### Schritt 1: Flag setzen

**DEV** (`values-dev.yaml`):
```yaml
configMap:
  EXT_DOC_ACCESS_ENABLED: "true"
```

**PROD** (`values-prod.yaml`):
```yaml
configMap:
  EXT_DOC_ACCESS_ENABLED: "true"
```

### Schritt 2: Deployen

```bash
# DEV
gh workflow run stackit-deploy.yml -f environment=dev -R CCJ-Development/voeb-chatbot

# PROD (nur nach DEV-Validierung!)
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot
```

Warten bis Deploy abgeschlossen (~8-10 Min).

### Schritt 3: Server-Restart verifizieren

```bash
# Pruefen ob der API-Server neugestartet hat (wegen fetch_versioned_implementation LRU-Cache)
kubectl logs -n <NAMESPACE> deploy/<RELEASE>-api-server --tail=5 | grep "ext"
# Erwartete Ausgabe: "Extension doc-access router + sync task registered"
```

### Schritt 4: Full Re-Sync ausloesen

**WICHTIG:** Bestehende Dokumente haben keine `group:` ACLs im OpenSearch-Index.
Ohne Resync sind Dokumente fuer Gruppen-Mitglieder unsichtbar.

```bash
# Resync ausloesen (als Admin eingeloggt)
curl -X POST https://<DOMAIN>/api/ext/doc-access/resync \
  -H "Cookie: <SESSION_COOKIE>"

# Erwartete Antwort:
# {"status":"started","groups_queued":5,"estimated_documents":601}
```

### Schritt 5: Sync-Status pruefen

```bash
# Status abfragen (alle Gruppen muessen synced sein)
curl https://<DOMAIN>/api/ext/doc-access/status \
  -H "Cookie: <SESSION_COOKIE>"

# Erwartete Antwort:
# {"enabled":true,"groups_total":5,"groups_synced":5,"groups_pending":0}
```

Wenn `groups_pending > 0`: Warten (Celery-Task laeuft alle 60s) und erneut pruefen.

### Schritt 6: Funktionstest

1. Als User einloggen der in **Gruppe A** ist
2. Suche ausfuehren → sollte nur Dokumente von CC-Pairs sehen die **Gruppe A** zugewiesen sind
3. Dokumente von CC-Pairs die **Gruppe B** zugewiesen sind: **nicht sichtbar**
4. Oeffentliche Dokumente (`is_public=true`): **immer sichtbar**

---

## Deaktivierung (Rollback)

```yaml
# Flag zuruecksetzen
configMap:
  EXT_DOC_ACCESS_ENABLED: "false"
```

Deploy ausloesen. Server-Restart → Hooks inaktiv → alle Dokumente wieder fuer alle sichtbar (FOSS-Verhalten).

**Kein Datenverlust:** Die `group:` ACLs bleiben im OpenSearch-Index, werden aber nicht mehr bei Suchanfragen genutzt.

---

## Troubleshooting

| Problem | Ursache | Loesung |
|---------|--------|---------|
| Dokumente nach Aktivierung unsichtbar | Resync nicht gelaufen | `POST /ext/doc-access/resync` |
| `groups_pending` bleibt >0 | Celery-Task laeuft nicht | Celery-Worker Logs pruefen, Pod-Restart |
| Alle Dokumente sichtbar trotz Flag=true | Server nicht neugestartet | Pod-Restart erzwingen: `kubectl rollout restart deploy/<RELEASE>-api-server` |
| 404 auf `/ext/doc-access/resync` | Flag nicht gesetzt oder ext nicht geladen | `EXT_DOC_ACCESS_ENABLED` + `EXT_ENABLED` in ConfigMap pruefen |
