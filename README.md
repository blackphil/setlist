# Setlist Manager Web Frontend

Ein FastAPI-basiertes Web Frontend zur Verwaltung von Band-Setlists.

## Installation

1. **Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

## Starten

```bash
cd app
python main.py
```

Das Frontend ist dann verfügbar unter: **http://localhost:8000**

## Struktur

- `app/main.py` - FastAPI Anwendung
- `app/templates/` - HTML Templates mit Jinja2
- `setlists/` - JSON-Dateien mit Setlist-Daten

## Features

### Aktuell
- ✅ Übersicht aller Setlists
- ✅ Anzeige von Event-Name, Band und Datum
- ✅ Anzeige der Anzahl von Sets pro Setlist
- ✅ Responsive Grid-Layout

### Geplant
- 🔄 Detail-Ansicht einzelner Setlists mit Songs
- 🔄 HTMX Integration für dynamische Interaktionen
- 🔄 SortableJS für Drag-and-Drop Funktionalität
- 🔄 Bearbeitung von Setlists
- 🔄 Export-Funktionen

## API Endpoints

- `GET /` - Hauptseite
- `GET /api/setlists` - API für alle Setlists (JSON)

## JSON Struktur Setlist

```json
{
  "meta": {
    "band": "Bandname",
    "event": "Event Name",
    "date": "YYYY-MM-DD"
  },
  "sets": [
    {
      "name": "Set 1",
      "songs": [
        {
          "title": "Song Title",
          "key": "C",
          "tempo": 120,
          "sheets": []
        }
      ]
    }
  ]
}
```
