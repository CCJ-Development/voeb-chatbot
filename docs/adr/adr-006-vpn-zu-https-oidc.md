# ADR-006: HTTPS + OIDC statt VPN-Tunnel

**Status**: Proposed
**Datum**: 2026-03-14
**Author**: CCJ / Coffee Studios (Nikolaj Ivanov)
**Bezug**: Kickoff-Meeting (2026-01-24, KICKOFF-006: "VPN-Tunnel zu StackIT")

---

## Context

Im Kickoff-Meeting (2026-01-24) wurde ein VPN-Tunnel als Zugangsmechanismus für den VÖB Service Chatbot beschlossen. Während der Implementierung wurde stattdessen öffentliches HTTPS mit geplanter OIDC-Authentifizierung via Microsoft Entra ID umgesetzt. Diese Entscheidung war nicht formell dokumentiert.

### Anforderungen

1. **Sicherer Zugang** — Transportverschlüsselung für alle Daten zwischen Client und Server
2. **Benutzerfreundlichkeit** — 150 Mitarbeiter an verschiedenen Standorten müssen ohne zusätzliche Software zugreifen können
3. **SSO-Integration** — Nutzung der vorhandenen Microsoft-365-Infrastruktur (Entra ID)
4. **Compliance** — BSI TR-02102-2 konforme TLS-Konfiguration
5. **Wartbarkeit** — Minimaler operativer Aufwand für Zugangsmanagement

### Ausgangslage

- Kickoff-Beschluss: VPN-Tunnel zu StackIT
- Implementiert: HTTPS (TLSv1.3, Let's Encrypt, ECDSA P-384) auf DEV + TEST (seit 2026-03-09)
- Geplant: OIDC-Authentifizierung via Microsoft Entra ID (blockiert, wartet auf Entra-ID-Zugangsdaten von VÖB)

---

## Decision

**Zugang über HTTPS (TLSv1.3, Let's Encrypt, ECDSA P-384) mit OIDC-Authentifizierung via Microsoft Entra ID. Kein VPN-Tunnel.**

### Implementierungs-Details

```
┌─────────────────────────────────────────────────────────────────┐
│ Zugangsarchitektur                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client (Standard-Browser)                                     │
│       │                                                        │
│       │ HTTPS (TLSv1.3, ECDSA P-384)                          │
│       │ BSI TR-02102-2 konform                                 │
│       ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ NGINX Ingress Controller (StackIT SKE)                   │   │
│  │ - TLS Termination (Let's Encrypt, cert-manager)         │   │
│  │ - HSTS Header                                           │   │
│  │ - HTTP/2                                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                        │
│       ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Onyx Web Server                                          │   │
│  │ - OIDC via Microsoft Entra ID (geplant)                 │   │
│  │ - Basic Auth als Fallback (DEV/TEST)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### TLS-Konfiguration (aktiv auf DEV + TEST)

- **Protokoll**: TLSv1.3
- **Zertifikat**: Let's Encrypt, ECDSA P-384
- **Key Exchange**: X25519 / X448
- **HTTP-Version**: HTTP/2
- **cert-manager**: DNS-01 Challenge via Cloudflare API, ACME-CNAME-Delegation über GlobVill
- **Erneuerung**: Automatisch (cert-manager, 60 Tage vor Ablauf)

---

## Rationale

### Warum HTTPS + OIDC statt VPN?

#### 1. Benutzerfreundlichkeit

- VPN erfordert Client-Software auf jedem Endgerät (150 Mitarbeiter)
- VPN-Setup und -Troubleshooting erzeugt erheblichen Support-Aufwand
- HTTPS + OIDC: Standard-Browser reicht, keine Installation nötig

#### 2. SSO-Integration

- VÖB nutzt bereits Microsoft 365 mit Entra ID
- OIDC via Entra ID ermöglicht Single Sign-On ohne separate Credentials
- VPN bietet kein SSO — Benutzer müssten VPN-Credentials UND Anwendungs-Credentials verwalten

#### 3. Äquivalente Sicherheit

- TLSv1.3 mit ECDSA P-384 bietet äquivalente Transportverschlüsselung wie VPN
- BSI TR-02102-2 Compliance für TLS-Konfiguration nachgewiesen
- HSTS erzwingt HTTPS-Nutzung

#### 4. Geringerer Verwaltungsaufwand

- VPN: Zertifikats-Management, Routing-Konfiguration, Client-Rollout, Firewall-Regeln
- HTTPS + OIDC: cert-manager (automatisch), Entra ID (zentral verwaltet durch VÖB IT)

#### 5. Branchenstandard

- HTTPS + OIDC ist der Standard für moderne Web-Applikationen im Banking-Sektor
- Vergleichbare Lösungen (interne Portale, SaaS-Tools) nutzen dasselbe Muster

---

## Alternatives Considered

### Alternative 1: VPN-Tunnel (Original-Beschluss)

**Ansatz**: VPN-Tunnel (z.B. WireGuard, OpenVPN) zwischen Endgeräten und StackIT-Cluster

**Vorteile**:
- Netzwerk-Isolation (Anwendung nicht öffentlich erreichbar)
- Zusätzliche Netzwerkschicht als Defense-in-Depth

**Nachteile**:
- Client-Software auf 150 Endgeräten installieren und warten
- VPN-Zertifikate/Credentials verwalten (Rotation, Revocation)
- Kein SSO — separate VPN-Credentials neben Entra ID
- Support-Aufwand bei Verbindungsproblemen (NAT, Firewalls, Split-Tunneling)
- Erhöhte Latenz durch VPN-Overhead
- Keine Integration mit vorhandener Microsoft-365-Infrastruktur

**Entscheidung**: Abgelehnt wegen unverhältnismäßigem Verwaltungsaufwand und fehlender SSO-Integration

---

### Alternative 2: Zero Trust Network Access (ZTNA)

**Ansatz**: ZTNA-Lösung (z.B. Zscaler, Cloudflare Access, Tailscale) vor der Anwendung

**Vorteile**:
- Modern, identity-aware Zugang
- Kein klassischer VPN-Client nötig
- Integrierbar mit Entra ID

**Nachteile**:
- Zusätzliche Infrastruktur und Kosten (Drittanbieter)
- Vendor Lock-In bei ZTNA-Anbieter
- Komplexität: Zusätzlicher Service zwischen Client und Anwendung
- Für 150 Benutzer überdimensioniert

**Entscheidung**: Abgelehnt wegen zusätzlicher Infrastruktur, Kosten und Komplexität

---

### Alternative 3: IP-Whitelisting

**Ansatz**: Zugriff nur von bestimmten IP-Adressen erlauben (VÖB-Büronetze)

**Vorteile**:
- Einfach umzusetzen (NGINX/Firewall-Regeln)
- Keine Client-Software nötig

**Nachteile**:
- Nicht praktikabel für 150 Mitarbeiter an verschiedenen Standorten und im Home-Office
- Dynamische IPs bei vielen Internetanschlüssen
- Kein mobiler Zugriff möglich
- Verwaltungsaufwand bei IP-Änderungen

**Entscheidung**: Abgelehnt wegen mangelnder Praktikabilität für verteilte Mitarbeiter

---

## Consequences

### Positive Auswirkungen

1. **Kein VPN-Client nötig** — Standard-Browser auf jedem Endgerät reicht
2. **SSO-Integration** — Single Sign-On über vorhandene Microsoft-365-Infrastruktur
3. **Einfacherer Support** — Keine VPN-Verbindungsprobleme, Standard-HTTPS
4. **Geringerer Verwaltungsaufwand** — Automatische Zertifikatserneuerung, zentrales Identity-Management
5. **BSI-konform** — TLSv1.3 mit ECDSA P-384 erfüllt BSI TR-02102-2

### Negative Auswirkungen / Mitigation

1. **Anwendung ist öffentlich erreichbar**
   - Mitigation: OIDC-Authentifizierung (kein anonymer Zugriff), HSTS, Rate Limiting (geplant)
   - Impact: Akzeptables Risiko bei korrekter Authentifizierung

2. **Bei Entra-ID-Ausfall kein Zugang**
   - Mitigation: Basic Auth als Fallback in DEV/TEST konfiguriert
   - Impact: PROD-Ausfall bei Entra-ID-Ausfall — akzeptiertes Restrisiko (Entra ID SLA > 99.9%)

3. **Kein VPN als zusätzliche Netzwerkschicht**
   - Mitigation: TLSv1.3, NetworkPolicies, Kubernetes RBAC, PG ACL — mehrere Sicherheitsschichten aktiv
   - Impact: Defense-in-Depth durch andere Maßnahmen kompensiert

---

## Implementation Notes

### Aktueller Stand

- **DEV**: HTTPS aktiv seit 2026-03-09 (`https://dev.chatbot.voeb-service.de`)
- **TEST**: HTTPS aktiv seit 2026-03-09 (`https://test.chatbot.voeb-service.de`)
- **PROD**: HTTPS wartet auf DNS-Einträge (A-Record + ACME-CNAME bei GlobVill angefragt)
- **Auth**: Basic Auth aktiv (DEV/TEST), OIDC blockiert (wartet auf Entra ID von VÖB)

### Offene Schritte

1. DNS-Einträge für PROD (wartet auf GlobVill)
2. TLS/HTTPS auf PROD aktivieren
3. Entra ID Zugangsdaten von VÖB erhalten
4. OIDC-Integration implementieren (Phase 3)

---

## Related ADRs

- **ADR-003**: StackIT als Cloud Provider — Infrastruktur-Basis
- **ADR-004**: Umgebungstrennung — DEV/TEST/PROD mit separaten TLS-Zertifikaten

---

## Approval & Sign-off

| Rolle | Name | Datum | Signatur |
|-------|------|-------|----------|
| Author (CCJ) | Nikolaj Ivanov | 2026-03-14 | [x] |
| Auftraggeber (VÖB) | [TBD] | [TBD] | [ ] |

---

**ADR Status**: Proposed
**Letzte Aktualisierung**: 2026-03-14
**Version**: 1.0
