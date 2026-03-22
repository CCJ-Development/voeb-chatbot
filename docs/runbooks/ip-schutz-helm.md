# Runbook: Load-Balancer-IP bei Helm-Reinstallation sichern

**Erstellt**: 2026-03-22
**Status**: Aktiv
**Verantwortlich**: Nikolaj Ivanov (CCJ)

---

## Zweck

`helm uninstall` loescht standardmaessig ALLE Kubernetes-Ressourcen des Releases — einschliesslich des `LoadBalancer`-Service des NGINX Ingress Controllers. StackIT erstellt daraufhin eine **neue Load-Balancer-IP**. Das erfordert einen DNS-Update bei GlobVill/Leif, der Tage dauern kann.

Dieses Runbook beschreibt, wie der NGINX-Service von Helm entkoppelt wird, sodass er `helm uninstall` ueberlebt.

**Aufgetreten bei:** Upstream-Sync #3 (2026-03-18) — Helm-Neuinstallation DEV notwendig wegen Chart-Inkompatibilitaet → neue LB-IP `188.34.118.222` → DNS-Update angefragt bei Leif.

---

## Aktuelle Load-Balancer-IPs

| Umgebung | LB-IP | DNS | Status |
|----------|-------|-----|--------|
| DEV | `188.34.118.222` | `dev.chatbot.voeb-service.de` | ✅ DNS korrekt (aktualisiert 2026-03-22) |
| PROD | `188.34.92.162` | `chatbot.voeb-service.de` | ✅ DNS gesetzt (2026-03-17) |

---

## Lesson Learned (WICHTIG)

> `helm upgrade` behält die LB-IP. `helm uninstall + install` erstellt eine neue LB-IP.
>
> **Faustregel:** Immer `helm upgrade --install` verwenden. Nur wenn ein Release wirklich nicht upgradefahig ist (z.B. neue CRD-Inkompatibilitaet), auf dieses Runbook zurueckgreifen.

---

## Methode: Service von Helm entkoppeln

### Schritt 1: Helm-Ownership-Annotation entfernen

Dadurch uebernimmt Helm den Service bei kuenftigen `helm upgrade`-Aufrufen nicht mehr und loescht ihn auch nicht bei `helm uninstall`.

```bash
# ENV = dev | prod
ENV=dev
NS=onyx-${ENV}
SVC_NAME=onyx-${ENV}-nginx-controller  # Exakten Namen pruefen: kubectl get svc -n $NS

# Helm-Ownership-Annotation setzen (Resource Policy = keep):
kubectl annotate svc $SVC_NAME -n $NS "helm.sh/resource-policy=keep" --overwrite

# Helm-Labels entfernen (damit Helm den Service nicht mehr trackt):
kubectl label svc $SVC_NAME -n $NS \
  "app.kubernetes.io/managed-by-" \
  "helm.sh/chart-" 2>/dev/null || true

# Verifizieren:
kubectl get svc $SVC_NAME -n $NS -o yaml | grep -A5 "annotations:"
```

### Schritt 2: Aktuelle LB-IP notieren

```bash
kubectl get svc $SVC_NAME -n $NS -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### Schritt 3: `helm uninstall` durchfuehren

Der Service bleibt erhalten, da er nicht mehr Helm-verwaltet ist.

```bash
helm uninstall onyx-${ENV} -n $NS
# → Service wird NICHT geloescht (wegen resource-policy=keep)
```

### Schritt 4: Neues Helm-Release installieren

```bash
# Beispiel DEV:
helm install onyx-dev deployment/helm/charts/onyx \
  -n onyx-dev \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-dev.yaml \
  -f deployment/helm/values/values-dev-secrets.yaml \
  --wait --timeout 15m
```

Das neue Release erstellt einen neuen NGINX-Service, der versucht eine neue LB-IP zu erhalten. **Den neuen Service loeschen** und den alten (entkoppelten) behalten:

```bash
# Neuen Service identifizieren und loeschen:
kubectl get svc -n $NS | grep nginx
# → Der neue Service hat Helm-Labels, der alte nicht

# Neuen loeschen (schreibt sich eigene LB-IP):
kubectl delete svc <NEUER_SERVICE_NAME> -n $NS

# Alten Service wieder mit Helm verbinden (optional, damit er kuenftig wieder verwaltet wird):
kubectl annotate svc $SVC_NAME -n $NS "helm.sh/resource-policy-" --overwrite
kubectl label svc $SVC_NAME -n $NS \
  "app.kubernetes.io/managed-by=Helm" \
  "meta.helm.sh/release-name=onyx-${ENV}" \
  "meta.helm.sh/release-namespace=${NS}"
```

### Schritt 5: IP verifizieren

```bash
kubectl get svc $SVC_NAME -n $NS -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
# → Muss identisch mit der IP aus Schritt 2 sein
```

---

## Alternativmethode: `loadBalancerIP` in Helm Values

StackIT unterstuetzt das Anfordern einer spezifischen LB-IP. Das ist jedoch keine Garantie (IP muss verfuegbar sein).

```yaml
# In values-dev.yaml oder values-common.yaml:
nginx:
  controller:
    service:
      loadBalancerIP: "188.34.118.222"  # DEV
```

**Vorteil:** Einfacher als Service-Entkopplung.
**Nachteil:** Keine Garantie; funktioniert nur wenn die IP im selben StackIT-Projekt verfuegbar ist und nicht von einem anderen Service belegt wird.

---

## Falls LB-IP sich trotzdem geaendert hat

### DNS-Update bei GlobVill beauftragen

```
An: leif@globvill.de (oder aktueller GlobVill-Kontakt)
Betreff: DNS-Update fuer VÖB Chatbot

Bitte folgenden A-Record aktualisieren:

dev.chatbot.voeb-service.de  →  <NEUE_IP>   (vorher: <ALTE_IP>)

Cloudflare Proxy: DNS-only (kein Proxy)
```

### Temporaerer Workaround (lokales /etc/hosts)

```bash
# Direkt auf neue IP zugreifen (nur auf eigenem Rechner):
sudo sh -c 'echo "<NEUE_IP>  dev.chatbot.voeb-service.de" >> /etc/hosts'

# Pruefen:
curl -sk https://dev.chatbot.voeb-service.de/api/health

# Entfernen wenn DNS aktualisiert:
sudo sed -i '' '/<NEUE_IP>/d' /etc/hosts
```

---

## Referenzen

- Helm Rollback Runbook: `docs/runbooks/rollback-verfahren.md`
- DNS/TLS Setup: `docs/runbooks/dns-tls-setup.md`
- Proj-Status (aktueller DNS-Stand): `.claude/rules/voeb-projekt-status.md`
- Lesson Learned Upstream-Sync #3: `memory/feedback_upstream-sync-lessons.md`
