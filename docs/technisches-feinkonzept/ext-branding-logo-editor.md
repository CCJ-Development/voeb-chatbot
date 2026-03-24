# Modulspezifikation: ext-branding Logo-Editor

**Dokumentstatus**: Entwurf
**Version**: 0.1
**Autor**: Nikolaj Ivanov (CCJ / Coffee Studios)
**Datum**: 2026-03-24
**Status**: [x] Entwurf | [ ] Review | [ ] Freigegeben
**Prioritaet**: [ ] Kritisch | [x] Hoch | [ ] Normal | [ ] Niedrig

---

## Moduluebersicht

| Feld | Wert |
|------|------|
| **Modulname** | ext-branding Logo-Editor |
| **Modul-ID** | `ext_branding` (Erweiterung, kein neues Modul) |
| **Version** | 1.1.0 (erweitert ext-branding 1.0) |
| **Feature Flag** | `EXT_BRANDING_ENABLED` (bestehend, kein neues Flag) |
| **Abhaengigkeiten** | ext-branding 1.0 (Basis) |

---

## Zweck und Umfang

### Zweck

Admins koennen aktuell nur ein Logo hochladen — ohne Moeglichkeit es zuzuschneiden, zu zoomen oder zu positionieren. Das fuehrt dazu, dass Logos in der UI (Sidebar 24px, Login 44px, Favicon 32px) abgeschnitten oder falsch dargestellt werden. Der Logo-Editor gibt Admins ein interaktives Crop/Zoom-Tool direkt auf der Branding-Seite, damit das Logo vor dem Speichern optimal zugeschnitten werden kann.

### Im Umfang enthalten

- Interaktives Crop-Tool nach Logo-Upload (Drag zum Positionieren, Slider zum Zoomen)
- Live-Vorschau in allen 3 Darstellungsgroessen (Sidebar 24px, Login 44px, Favicon 32px)
- Client-seitiges Cropping via HTML5 Canvas API (kein Server-seitiges Image Processing)
- Gecropptes Bild wird als finale Version an Backend gesendet (ersetzt das Original)
- Quadratischer Crop-Bereich (1:1 Aspect Ratio, passend fuer alle UI-Kontexte)
- Option fuer transparenten Hintergrund (Checkbox, Default: weiss)
- "Logo entfernen"-Button zum Zuruecksetzen auf OnyxIcon-Default

### Nicht im Umfang

- SVG-Upload (weiterhin nur PNG/JPEG)
- Separates Favicon-Upload (Favicon nutzt weiterhin das gleiche Logo)
- Bildfilter, Rotation, Farbkorrekturen
- Logo-Versionshistorie / Rollback
- Server-seitige Bildverarbeitung (Pillow/sharp)
- Neue npm-Dependencies (react-easy-crop o.ae.) — nur native Canvas API

### Abhaengige Module

- [x] ext-branding 1.0 (Upload-Endpoint, DB-Modell, Serving-Endpoint — alles vorhanden)

---

## Architektur

### Komponenten-Uebersicht

```
Admin Branding Page (/admin/ext-branding)
         |
         v
┌─────────────────────────────────────┐
│  1. Logo-Upload (bestehend)         │
│     <input type="file" />           │
└─────────────┬───────────────────────┘
              |  File ausgewaehlt
              v
┌─────────────────────────────────────┐
│  2. LogoCropModal (NEU)             │
│  ┌─────────────────────────────┐    │
│  │  Crop-Bereich               │    │
│  │  - Drag: Bild verschieben   │    │
│  │  - Slider: Zoom 1x-3x      │    │
│  │  - 1:1 Aspect Ratio         │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │  Vorschau                   │    │
│  │  [24px] [44px] [32px]       │    │
│  │  Sidebar  Login  Favicon    │    │
│  └─────────────────────────────┘    │
│  [Abbrechen]  [Uebernehmen]        │
└─────────────┬───────────────────────┘
              |  "Uebernehmen" geklickt
              v
┌─────────────────────────────────────┐
│  3. Canvas-Crop (client-seitig)     │
│  - <canvas> mit crop-Ausschnitt     │
│  - canvas.toBlob("image/png")       │
│  - Output: 256x256 PNG              │
└─────────────┬───────────────────────┘
              |
              v
┌─────────────────────────────────────┐
│  4. Upload (bestehend)              │
│  PUT /api/admin/enterprise-settings │
│       /logo                         │
│  - Gecropptes 256x256 PNG           │
│  - Bestehende Validierung greift    │
└─────────────────────────────────────┘
```

### Datenfluss

1. Admin waehlt Bilddatei ueber `<input type="file" />`
2. Statt sofort hochzuladen: `LogoCropModal` oeffnet sich mit dem Bild
3. Admin positioniert (Drag) und zoomt (Slider) das Bild im quadratischen Crop-Bereich
4. Live-Vorschau zeigt das Ergebnis in 24px, 44px und 32px
5. Bei "Uebernehmen": Canvas rendert den sichtbaren Crop-Bereich als 256x256 PNG
6. `canvas.toBlob()` erzeugt die Bilddatei
7. Upload via bestehenden `PUT /api/admin/enterprise-settings/logo` Endpoint
8. Backend validiert (2 MB, PNG Magic Bytes) und speichert in `ext_branding_config.logo_data`
9. Logo ist sofort an allen UI-Stellen aktualisiert (Sidebar, Login, Favicon)

---

## Datenbankschema

**Keine Aenderungen.** Das gecroppte Bild ersetzt das Original in der bestehenden `logo_data`-Spalte. Keine neuen Tabellen, Spalten oder Migrationen noetig.

Bestehende Tabelle `ext_branding_config` (unveraendert):

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `logo_data` | BYTEA | Gecropptes PNG (max 2 MB) |
| `logo_content_type` | VARCHAR(50) | "image/png" (immer PNG nach Crop) |
| `logo_filename` | VARCHAR(255) | Original-Dateiname (Referenz) |

---

## API-Spezifikation

### Bestehender Endpoint: `PUT /admin/enterprise-settings/logo`

| Feld | Wert |
|------|------|
| Pfad | `/api/admin/enterprise-settings/logo` |
| Methode | PUT |
| Auth | Admin required (`current_admin_user`) |
| Request Body | `multipart/form-data` mit `file` (UploadFile) |
| Response | 200 (kein Body) oder 400 mit `{"detail": "..."}` |

**Aenderung gegenueber Status quo:** Statt des Original-Bildes wird jetzt das client-seitig gecroppte 256x256 PNG hochgeladen. Der Backend-Code bleibt identisch — die Validierung (2 MB, PNG Magic Bytes) greift weiterhin.

### Neuer Endpoint: `DELETE /admin/enterprise-settings/logo`

| Feld | Wert |
|------|------|
| Pfad | `/api/admin/enterprise-settings/logo` |
| Methode | DELETE |
| Auth | Admin required (`current_admin_user`) |
| Request Body | keiner |
| Response | 200 (kein Body) |

**Funktion:** Setzt `logo_data = None`, `logo_content_type = None`, `logo_filename = None`, `use_custom_logo = False`. Stellt das OnyxIcon-Default wieder her.

**Implementierung:**
- `backend/ext/services/branding.py`: Neue Funktion `delete_logo(db_session)`
- `backend/ext/routers/branding.py`: Neuer `@admin_router.delete("/logo")` Handler

---

## Frontend-Komponenten

### Neue Komponente: `LogoCropModal`

**Location**: `web/src/ext/components/LogoCropModal.tsx`

**Beschreibung**: Modales Fenster mit interaktivem Crop/Zoom-Tool und Live-Vorschau.

#### Props

```typescript
interface LogoCropModalProps {
  imageFile: File;               // Ausgewaehlte Bilddatei
  onCrop: (blob: Blob) => void;  // Callback mit gecropptem Bild
  onCancel: () => void;          // Abbrechen
}
```

#### Interner State

```typescript
// Crop-Steuerung
const [zoom, setZoom] = useState(1);          // 1x - 3x
const [offset, setOffset] = useState({ x: 0, y: 0 });  // Drag-Offset
const [isDragging, setIsDragging] = useState(false);
const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

// Bild-Daten
const [imageSrc, setImageSrc] = useState<string>("");  // Data-URL
const [imageSize, setImageSize] = useState({ w: 0, h: 0 });  // Natuerliche Groesse

// Refs
const canvasRef = useRef<HTMLCanvasElement>(null);
const imageRef = useRef<HTMLImageElement>(null);
```

#### UI-Layout

```
┌──────────────────────────────────────────────┐
│  Logo zuschneiden                        [X] │
│──────────────────────────────────────────────│
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │                                        │  │
│  │     ┌──────────────┐                   │  │
│  │     │ //////////// │  <- Sichtbarer    │  │
│  │     │ // CROP  /// │     Bereich       │  │
│  │     │ // AREA //// │     (quadratisch) │  │
│  │     │ //////////// │                   │  │
│  │     └──────────────┘                   │  │
│  │                                        │  │
│  │  (Drag zum Verschieben)                │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Zoom: [──●────────────────] 1.2x            │
│                                              │
│  Vorschau:                                   │
│  ┌────┐  ┌──────┐  ┌─────┐                  │
│  │24px│  │ 44px │  │32px │                   │
│  └────┘  └──────┘  └─────┘                   │
│  Sidebar  Login    Favicon                   │
│                                              │
│          [Abbrechen]  [Uebernehmen]          │
└──────────────────────────────────────────────┘
```

#### Crop-Mechanismus (Canvas API)

```typescript
function cropImage(): Promise<Blob> {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d")!;
  const img = imageRef.current!;

  // Output: immer 256x256 PNG
  const OUTPUT_SIZE = 256;
  canvas.width = OUTPUT_SIZE;
  canvas.height = OUTPUT_SIZE;

  // Berechne den sichtbaren Bildausschnitt
  // basierend auf zoom + offset
  const cropSize = Math.min(img.naturalWidth, img.naturalHeight) / zoom;
  const sx = (img.naturalWidth / 2) - (cropSize / 2) - (offset.x * (img.naturalWidth / containerSize));
  const sy = (img.naturalHeight / 2) - (cropSize / 2) - (offset.y * (img.naturalHeight / containerSize));

  // Weisser Hintergrund (fuer transparente PNGs)
  ctx.fillStyle = "#FFFFFF";
  ctx.fillRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);

  // Bild in Canvas zeichnen
  ctx.drawImage(img, sx, sy, cropSize, cropSize, 0, 0, OUTPUT_SIZE, OUTPUT_SIZE);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob!), "image/png", 1.0);
  });
}
```

#### Drag-Handling

```typescript
// Mouse Events auf dem Crop-Container
onMouseDown: (e) => {
  setIsDragging(true);
  setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
};

onMouseMove: (e) => {
  if (!isDragging) return;
  const maxOffset = containerSize * (zoom - 1) / 2;
  setOffset({
    x: clamp(e.clientX - dragStart.x, -maxOffset, maxOffset),
    y: clamp(e.clientY - dragStart.y, -maxOffset, maxOffset),
  });
};

onMouseUp: () => setIsDragging(false);
```

#### Touch-Support

```typescript
// Identisch zu Mouse Events, aber mit e.touches[0]
onTouchStart, onTouchMove, onTouchEnd
```

### Aenderung bestehender Komponente: `ExtBrandingAdminPage`

**Location**: `web/src/ext/pages/admin/branding/page.tsx`

**Aenderungen**:

1. `handleLogoUpload` oeffnet `LogoCropModal` statt sofort hochzuladen
2. Neuer State: `cropFile: File | null` (Bild im Editor)
3. `onCrop`-Callback sendet gecropptes Blob an bestehenden Upload-Endpoint

```typescript
// Bisheriger Flow:
// File ausgewaehlt → sofort PUT /logo

// Neuer Flow:
// File ausgewaehlt → setCropFile(file) → Modal oeffnet sich
// → User croppt → onCrop(blob) → PUT /logo mit gecropptem Blob
// → Modal schliesst sich
```

---

## Fehlerbehandlung

| Fehlerfall | Behandlung |
|------------|-----------|
| Bild zu gross (> 2 MB nach Crop) | Kann nicht vorkommen: 256x256 PNG < 300 KB |
| Ungültiges Bildformat | `<input accept="image/png,image/jpeg">` filtert vor; Backend validiert Magic Bytes |
| Canvas API nicht verfuegbar | Fallback: Bild ohne Crop hochladen (aktuelles Verhalten) |
| Browser unterstuetzt kein `toBlob` | Alle modernen Browser unterstuetzen es (IE11 nicht, aber irrelevant) |
| Drag ausserhalb des Containers | `clamp()` begrenzt Offset auf gueltigen Bereich |
| Sehr kleines Quellbild (< 32px) | Warnung anzeigen: "Bild ist zu klein fuer optimale Darstellung" |
| Upload-Fehler (Netzwerk) | Bestehende Fehlerbehandlung in `handleLogoUpload` greift |

---

## Feature Flag Verhalten

**Kein neues Feature Flag.** Nutzt bestehendes `EXT_BRANDING_ENABLED`:

- **Flag = true**: Logo-Upload oeffnet den Crop-Editor (neues Verhalten)
- **Flag = false**: Branding-Seite nicht verfuegbar (bestehendes Verhalten)

---

## Betroffene Core-Dateien

**Keine.** Alle Aenderungen in ext/-Code:

| Datei | Aenderung |
|-------|-----------|
| `web/src/ext/components/LogoCropModal.tsx` | **NEU** — Crop/Zoom-Komponente |
| `web/src/ext/pages/admin/branding/page.tsx` | **AENDERN** — Crop-Modal statt direktem Upload |

Die bereits vorgenommenen CSS-Fixes (Core #9 AuthFlowContainer.tsx, Core #15 Logo.tsx) sind unabhaengig von diesem Feature und bleiben bestehen.

---

## Tests

### Unit Tests

| Test | Beschreibung |
|------|-------------|
| `clamp()` Funktion | Werte innerhalb/ausserhalb der Grenzen |
| Zoom-Grenzen | zoom >= 1.0, zoom <= 3.0 |
| Offset-Begrenzung | Offset darf Bild nicht ausserhalb des Crop-Bereichs schieben |
| Canvas Output | 256x256 PNG, weisser Hintergrund |

### Manuelle Tests

| Test | Schritte | Erwartetes Ergebnis |
|------|----------|-------------------|
| Logo Upload + Crop | Upload → Zoom auf 1.5x → Drag nach links → Uebernehmen | Gecropptes Logo in Sidebar, Login, Favicon sichtbar |
| Abbrechen | Upload → Crop-Modal → Abbrechen | Kein Upload, altes Logo bleibt |
| Quadratisches Bild | 500x500 PNG hochladen | Crop-Bereich zeigt ganzes Bild, Zoom 1x |
| Breites Bild | 1000x200 PNG hochladen | Crop-Bereich zeigt Mitte, Zoom anpassbar |
| Hohes Bild | 200x1000 PNG hochladen | Crop-Bereich zeigt Mitte, Zoom anpassbar |
| Kleines Bild | 30x30 PNG hochladen | Warnung "Bild zu klein", Crop trotzdem moeglich |
| JPEG Upload | JPEG hochladen + croppen | Wird als PNG gespeichert (Canvas Output) |
| Vorschau | Bild positionieren | 24px, 44px, 32px Vorschau aktualisiert live |
| Touch (Tablet) | Bild mit Finger verschieben | Drag funktioniert |

### Feature Flag Tests

| Flag | Ergebnis |
|------|---------|
| `EXT_BRANDING_ENABLED=true` | Crop-Modal erscheint nach Dateiauswahl |
| `EXT_BRANDING_ENABLED=false` | Branding-Seite nicht erreichbar (404) |

---

## Technische Entscheidungen

### Warum Canvas API statt npm-Library?

- **Keine neue Dependency** — reduziert Bundle-Groesse und Supply-Chain-Risiko
- **Canvas API ist stabil** — seit 2010 in allen Browsern verfuegbar
- **Einfacher Anwendungsfall** — nur quadratisches Crop + Zoom, keine komplexen Transformationen
- **Kein Server-seitiges Processing** — Bild wird client-seitig fertig zugeschnitten

### Warum 256x256 Output?

- **Groesste Darstellung: 88px** (Sidebar unfolded) — 256px bietet 3x Aufloesung (Retina)
- **Favicon: 32px** — 256px bietet 8x Aufloesung
- **Dateigroesse: < 300 KB** — weit unter dem 2 MB Limit
- **Einheitliche Groesse** — vermeidet Probleme mit verschiedenen Seitenverhaeltnissen

### Warum immer PNG Output?

- **Transparenz-Support** — Logo kann transparenten Hintergrund haben
- **Verlustfrei** — keine JPEG-Artefakte bei kleinen Groessen
- **Canvas-Standard** — `canvas.toBlob("image/png")` ist der zuverlaessigste Output

---

## Geklärte Punkte

- [x] **[OPEN-1]** Reset-Button: Ja. Setzt `logo_data = None`, `use_custom_logo = false`. Bestehender PUT-Endpoint, neuer "Logo entfernen"-Button in der UI.
- [x] **[OPEN-2]** Transparenter Hintergrund: Ja, als Option. Checkbox "Transparenter Hintergrund" im Crop-Modal. Default: weiss. Wenn aktiviert: `ctx.fillRect()` wird uebersprungen → PNG mit Alpha-Kanal.

---

## Aufwand

| Komponente | Geschaetzter Aufwand |
|------------|---------------------|
| `LogoCropModal.tsx` | ~200 Zeilen |
| `page.tsx` Anpassung | ~30 Zeilen (inkl. Logo-entfernen-Button) |
| `services/branding.py` Erweiterung | ~10 Zeilen (`delete_logo()`) |
| `routers/branding.py` Erweiterung | ~10 Zeilen (DELETE Endpoint) |
| Tests | ~60 Zeilen |
| **Gesamt** | ~310 Zeilen, reiner ext/-Code |

---

## Approvals

| Rolle | Name | Datum | Status |
|-------|------|-------|--------|
| Technical Lead | Nikolaj Ivanov | TBD | Ausstehend |

---

## Revisions-Historie

| Version | Datum | Autor | Aenderungen |
|---------|-------|-------|-------------|
| 0.1 | 2026-03-24 | Claude (CCJ) | Initialer Entwurf |
