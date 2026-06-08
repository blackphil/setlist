from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import json
from pathlib import Path
from datetime import datetime
import subprocess
import sys
import os
import tempfile
import shutil

app = FastAPI(title="Setlist Manager")

# Template-Verzeichnis
templates = Jinja2Templates(directory="templates")

# Pfad zu den Setlists
SETLISTS_DIR = Path(__file__).parent.parent / "setlists"


def load_setlists():
    """Laden aller Setlist-Metainformationen"""
    setlists = []
    
    if not SETLISTS_DIR.exists():
        return setlists
    
    for json_file in SETLISTS_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Meta-Informationen extrahieren
            meta = data.get("meta", {})
            setlists.append({
                "filename": json_file.stem,
                "band": meta.get("band", "N/A"),
                "event": meta.get("event", "N/A"),
                "date": meta.get("date", "N/A"),
                "sets_count": len(data.get("sets", []))
            })
        except Exception as e:
            print(f"Fehler beim Laden von {json_file}: {e}")
    
    # Sortieren nach Datum (neueste zuerst)
    setlists.sort(key=lambda x: x["date"], reverse=True)
    return setlists


def extract_all_tags():
    """Extrahiert alle eindeutigen Tags aus den Setlists"""
    tags = set()
    
    if not SETLISTS_DIR.exists():
        return sorted(list(tags))
    
    for json_file in SETLISTS_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Durch alle Sets gehen
            for set_item in data.get("sets", []):
                # Durch alle Songs gehen
                for song in set_item.get("songs", []):
                    # Durch alle Sheets gehen
                    for sheet in song.get("sheets", []):
                        tag = sheet.get("tag")
                        if tag:
                            tags.add(tag)
        except Exception as e:
            print(f"Fehler beim Extrahieren von Tags aus {json_file}: {e}")
    
    return sorted(list(tags))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Hauptseite mit Setlist-Übersicht"""
    setlists = load_setlists()
    tags = extract_all_tags()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "setlists": setlists,
            "total_setlists": len(setlists),
            "available_tags": tags
        }
    )


@app.get("/api/setlists")
async def api_setlists():
    """API Endpoint für alle Setlists"""
    return {
        "setlists": load_setlists()
    }


@app.get("/generate-pdf/{setlist_name}")
async def generate_pdf(setlist_name: str, sheet_tag: str = None):
    """PDF für eine Setlist generieren und herunterladen"""
    temp_dir = None
    try:
        # Setlist-Datei finden
        setlist_file = SETLISTS_DIR / f"{setlist_name}.json"
        
        if not setlist_file.exists():
            return {"error": f"Setlist '{setlist_name}' nicht gefunden"}
        
        # Meta-Informationen laden
        with open(setlist_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        pdf_filename = data.get("meta", {}).get("event", "setlist") + ".pdf"
        
        # Temporäres Verzeichnis erstellen
        temp_dir = tempfile.mkdtemp(prefix="setlist_")
        print(f"DEBUG: Temp-Verzeichnis erstellt: {temp_dir}")
        
        try:
            app_dir = Path(__file__).parent
            setlist_gen_script = app_dir / "setlist_gen.py"
            
            # Kommando zusammenstellen
            cmd = [sys.executable, str(setlist_gen_script), "--json", str(setlist_file)]
            
            # Sheet-Tag hinzufügen, wenn vorhanden
            if sheet_tag:
                cmd.extend(["--sheet-tag", sheet_tag])
                print(f"DEBUG: Sheet-Tag: {sheet_tag}")
            
            # setlist_gen.py Skript aufrufen (mit temp_dir als Working Directory)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=temp_dir  # Arbeite im temp-Verzeichnis
            )
            
            print(f"DEBUG: Return Code: {result.returncode}")
            print(f"DEBUG STDOUT:\n{result.stdout}")
            print(f"DEBUG STDERR:\n{result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"Fehler bei PDF-Generierung:\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}"
                print(f"ERROR: {error_msg}")
                return {"error": error_msg}
            
            # PDF-Datei im temp-Verzeichnis finden
            pdf_path = Path(temp_dir) / pdf_filename
            
            print(f"DEBUG: Suche nach PDF: {pdf_path}")
            print(f"DEBUG: PDF existiert: {pdf_path.exists()}")
            
            if not pdf_path.exists():
                # Alle Dateien im temp-Verzeichnis auflisten
                files = list(Path(temp_dir).glob("*"))
                print(f"DEBUG: Dateien im temp-Verzeichnis: {files}")
                return {"error": f"PDF konnte nicht erstellt werden. Generierte Dateien: {[f.name for f in files]}"}
            
            # PDF-Inhalt in Memory laden
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()
            
            print(f"DEBUG: PDF geladen ({len(pdf_content)} bytes)")
            
            # Temp-Verzeichnis NICHT löschen (zu Testzwecken)
            print(f"DEBUG: Temp-Verzeichnis behalten (zu Testzwecken): {temp_dir}")
            # shutil.rmtree(temp_dir)
            temp_dir = None  # Markiert als nicht zu löschen
            
            # PDF zurückgeben
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={pdf_filename}"}
            )
        
        except subprocess.TimeoutExpired:
            return {"error": "PDF-Generierung hat zu lange gedauert (>30 Sekunden)"}
        except Exception as e:
            error_msg = f"Fehler: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}
    
    finally:
        # Sicherstellen, dass das temp-Verzeichnis gelöscht wird
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"DEBUG: Cleanup - Temp-Verzeichnis gelöscht: {temp_dir}")
            except Exception as e:
                print(f"WARNING: Konnte temp-Verzeichnis nicht löschen: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
