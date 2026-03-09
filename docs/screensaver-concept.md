# Literature Clock — Screensaver Concept

## Übersicht

Die Literature Clock als nativer Screensaver für Windows, macOS und Linux.
Kern-Idee: Ein WebView-Container pro Plattform, der die bestehende HTML/CSS/JS-App fullscreen rendert — mit gebündelten lokalen Assets (kein Netzwerk nötig).

---

## Architektur-Entscheidung: Native Wrapper vs. Electron

### Option A: Plattform-native Wrapper (empfohlen)
Jede Plattform bekommt einen eigenen, minimalen WebView-Wrapper:
- **Windows:** C# WinForms + WebView2 → `.scr`
- **macOS:** Swift + WKWebView → `.saver` Bundle
- **Linux:** Python/GTK + WebKitGTK → XScreenSaver-Modul

**Vorteile:** Winzige Binaries (<5 MB), nutzt System-WebView, fühlt sich nativ an, kein Runtime-Overhead.
**Nachteile:** Drei separate Codebases, plattformspezifisches Build-Tooling.

### Option B: Electron (cross-platform)
Ein Electron-Wrapper für alle drei Plattformen.

**Vorteile:** Eine Codebase, bekanntes Tooling.
**Nachteile:** ~100 MB Paketgröße für einen Screensaver, Chromium-Runtime gebündelt, fühlt sich oversized an, Windows-`.scr`-Integration eingeschränkt (kein nativer Preview).

### Entscheidung
→ **Option A (Native Wrapper)** — ein Screensaver sollte federleicht sein. Drei kleine Wrapper schlagen einen aufgeblähten Electron-Container.

---

## Plattform-Details

### Windows (.scr)

**Technologie:** C# / .NET + WebView2 (Chromium-basiert, in Windows 10/11 vorinstalliert)

**Wie Screensaver auf Windows funktionieren:**
- Eine `.scr`-Datei ist eine umbenannte `.exe`
- Windows ruft sie mit Kommandozeilen-Argumenten auf:
  - `/s` → Screensaver starten (Fullscreen)
  - `/p <hwnd>` → Preview im Settings-Dialog
  - `/c` → Konfiguration öffnen
- Beendet sich bei Mausbewegung oder Tastendruck

**Aufbau:**
```
LiteratureClock.scr (= .exe)
├── WinForms App mit WebView2-Control
├── Embedded HTML/CSS/JS/JSON als Resources
├── Settings-Dialog (URL override, offline/online toggle)
└── Multi-Monitor-Support (ein WebView pro Screen)
```

**Voraussetzungen:**
- WebView2 Runtime (seit Windows 11 vorinstalliert, Win10 via Evergreen Installer)
- Visual Studio oder `dotnet` CLI zum Bauen
- Code-Signing optional (empfohlen für Distribution)

**Distribution:** `.scr` + Installer (oder ZIP) auf GitHub Releases

---

### macOS (.saver)

**Technologie:** Swift + WKWebView + ScreenSaver Framework

**Wie Screensaver auf macOS funktionieren:**
- Ein `.saver` Bundle ist ein Plugin-Paket
- Enthält eine `ScreenSaverView`-Subclass
- Wird per Doppelklick installiert → System Settings > Screen Saver
- macOS lädt das Bundle in den `legacyScreenSaver`-Prozess

**Aufbau:**
```
LiteratureClock.saver (Bundle)
├── Info.plist (Principal Class, Version)
├── Swift Code
│   └── LiteratureClockView.swift (ScreenSaverView + WKWebView)
├── Resources/
│   ├── index.html
│   ├── css/style.css
│   ├── js/clock.js
│   └── data/quotes.json
└── Optional: ConfigSheet.xib (Einstellungen)
```

**Besonderheiten:**
- `WKWebView` in ScreenSaver-Kontext erfordert Workarounds (Sandbox-Einschränkungen)
- Ab macOS 14+: ScreenSaver-API-Änderungen beachten
- Code-Signing + Notarization für Distribution außerhalb des App Store
- Gatekeeper blockiert unsignierte `.saver`-Bundles (Warnung für Nutzer dokumentieren)

**Distribution:** `.saver` als DMG oder ZIP auf GitHub Releases

---

### Linux (XScreenSaver-Modul)

**Technologie:** Python3 + GTK4 + WebKitGTK (webkit2gtk-4.1)

**Wie Screensaver auf Linux funktionieren:**
- XScreenSaver ist der de-facto Standard
- Jeder Screensaver ist ein eigenständiges Programm
- XScreenSaver setzt `$XSCREENSAVER_WINDOW` und startet das Programm
- Das Programm rendert in das bereitgestellte X-Window

**Aufbau:**
```
literature-clock-screensaver
├── literature-clock.py (Hauptprogramm)
│   └── GTK Window + WebKitWebView
│       └── Lädt lokale index.html
├── assets/
│   ├── index.html, css/, js/, data/
├── literature-clock.xml (XScreenSaver Metadata)
└── Makefile / install.sh
```

**Installation:**
```bash
# Script nach /usr/lib/xscreensaver/ oder ~/.local/lib/xscreensaver/
# XML nach /usr/share/xscreensaver/config/
# Assets nach /usr/share/literature-clock/
```

**Konfiguration in `~/.xscreensaver`:**
```
programs: \
  literature-clock \n\
  ...
```

**Alternativen für Wayland/GNOME:**
- GNOME Shell hat keinen klassischen Screensaver (nur Lock Screen)
- `gnome-screensaver` ist deprecated
- Mögliche Lösung: Eigenständige Fullscreen-App als "Desktop Idle Widget"
- KDE: Eigenes Screensaver-Framework, ähnlicher Ansatz möglich

**Distribution:** AUR-Paket, `.deb`, oder manuelles Install-Script

---

## Gemeinsame Anforderungen (alle Plattformen)

| Feature | Details |
|---|---|
| **Offline-fähig** | Alle Assets (HTML, CSS, JS, JSON) lokal gebündelt |
| **Minutengenaue Aktualisierung** | Zitat wechselt jede Minute mit Fade |
| **Screensaver-Exit** | Mausbewegung oder Tastendruck beendet |
| **Multi-Monitor** | Idealerweise unterschiedliche Zitate pro Monitor |
| **Konfiguration** | Optional: URL-Override für eigenen Server, Theme-Auswahl |
| **Update-Mechanismus** | Quotes-JSON unabhängig aktualisierbar |
| **Geringe Ressourcen** | <50 MB RAM, <2% CPU im Idle |

---

## Aufwandsschätzung

| Plattform | Aufwand | Schwierigkeit | Tooling |
|---|---|---|---|
| **Windows** | ~2–3 Tage | Mittel | Visual Studio / dotnet CLI, C# |
| **macOS** | ~3–4 Tage | Hoch (Sandbox, Signing) | Xcode, Swift |
| **Linux** | ~1–2 Tage | Niedrig | Python, GTK, WebKitGTK |
| **Shared** | ~1 Tag | Niedrig | Screensaver-optimierte HTML-Variante |

**Gesamt: ~8–10 Arbeitstage** (sequentiell), ~5–6 Tage bei Fokus auf eine Plattform.

---

## Risiken & Offene Fragen

1. **macOS Sandbox:** WKWebView innerhalb von ScreenSaverView hat bekannte Probleme. Eventuell WebView in separatem Prozess nötig.
2. **macOS Notarization:** Ohne Apple Developer Account ($99/Jahr) keine saubere Distribution.
3. **Windows WebView2 Runtime:** Auf Win10 nicht garantiert vorinstalliert — Fallback oder Bundling nötig?
4. **Linux Wayland:** XScreenSaver funktioniert unter Wayland nur eingeschränkt. GNOME hat kein Screensaver-Konzept mehr.
5. **Energieverbrauch:** WebView im Screensaver-Modus — muss WebView `requestAnimationFrame` intelligent drosseln?
6. **Quote-Updates:** Sollen neue Zitate nachladbar sein, ohne den Screensaver neu zu installieren?

---

## Empfehlung: Reihenfolge

1. **Linux zuerst** — geringster Aufwand, sofort nutzbar auf Wintermute
2. **macOS** — Uwes MacBook, höchster Wow-Faktor
3. **Windows** — Breiteste Zielgruppe, aber Uwe nutzt Windows weniger
