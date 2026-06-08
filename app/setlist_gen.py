import json
import os
import argparse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("Regular", r"C:\Windows\Fonts\segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("Bold", r"C:\Windows\Fonts\seguibl.ttf"))

#-----
#0. Syles

g_font_name_normal="Regular"
g_font_name_bold="Bold"

set_title_style = ParagraphStyle(
    name="SetTitle",
    fontName=g_font_name_bold,
    fontSize=28,
    alignment=1,
    spaceAfter=20
)

title_style = ParagraphStyle(
    name="SetTitle",
    fontName=g_font_name_bold,  # Schriftart
    fontSize=34,                # Schriftgröße
    alignment=1,                # Zentriert (0=links,1=mittel,2=rechts)
    spaceAfter=50               # Abstand nach unten
)

song_style = ParagraphStyle(
    name="Song",
    fontName=g_font_name_normal,
    fontSize=14,
    leading=16  # Zeilenhöhe
)

pause_style = ParagraphStyle(
    name="Pause",
    fontName=g_font_name_bold,
    fontSize=36,
    alignment=1,      # zentriert
    spaceAfter=200
)

# -------------------------
# 1. Argumente parsen
# -------------------------
parser = argparse.ArgumentParser(description="Setlist Generator")

parser.add_argument(
    "--json",
    help="Pfad zur Setlist-JSON-Datei",
    default="setlist.json"
)

parser.add_argument(
    "--sheets-dir",
    help="Basisverzeichnis für Sheet-PDFs",
    default="."
)

parser.add_argument(
    "--sheet-tag",
    help="Nur Sheets mit diesem Tag anhängen (z.B. Bass, Lead-Git)",
    default=None
)
args = parser.parse_args()
JSON_FILE = args.json
SHEETS_DIR = args.sheets_dir
SELECTED_TAG = args.sheet_tag

# -------------------------
# 2. JSON laden
# -------------------------
SETLIST_MAIN = "setlist_main.pdf"
FINAL_PDF = "setlist_complete.pdf"

if not os.path.exists(JSON_FILE):
    raise FileNotFoundError(f"{JSON_FILE} nicht gefunden!")

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# -------------------------
# 3. Hilfsfunktionen
# -------------------------
styles = getSampleStyleSheet()

def song_has_sheets(song, selected_tag):
    for sheet in song.get("sheets", []):
        if selected_tag is None or sheet["tag"] == selected_tag:
            return True
    return False



def add_title_page(story, meta, styles):

    """Erstellt die Titelseite mit Band, Event und Datum."""
    story.append(Spacer(1, 200))
    story.append(Paragraph(meta.get("band", ""), title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(meta.get("event", ""), styles["Heading2"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(meta.get("date", ""), styles["Normal"]))
    story.append(PageBreak())

def add_set_overview(story, set_name, songs, active_index, set_index, styles):
    
    # Anchor für diese Song-Seite
    anchor = f"song_{set_index}_{active_index}"
    story.append(Paragraph(f'<a name="{anchor}"/>', styles["Normal"]))
    
    """Erstellt eine Set-Seite mit allen Titeln.
    Der aktive Song wird schwarz, alle anderen grau.
    """
    story.append(Paragraph(set_name, set_title_style))
    story.append(Spacer(1, 20))
    
    for idx, song in enumerate(songs):
        
        has_sheet = song_has_sheets(song, SELECTED_TAG)
        star = " *" if has_sheet else ""
        target = f"song_{set_index}_{idx}"

        color = "black" if idx == active_index else "grey"
        
        text = (
            f'<font color="{color}">'
            f'<a href="#{target}">{idx+1}. {song["title"]}{star}</a>'
            f'</font>'
        )
        
        story.append(Paragraph(text, song_style))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

def add_pause_page(story, title="Pause"):

    story.append(Spacer(1, 250))
    story.append(Paragraph(title, pause_style))
    story.append(PageBreak())
    
def append_song_sheets(writer, song, selected_tag):
    """Fügt die Sheets eines Songs an das finale PDF an, optional gefiltert nach Tag."""
    for sheet in song.get("sheets", []):
        if selected_tag and sheet["tag"] != selected_tag:
            continue
        sheet_file = os.path.join(SHEETS_DIR, sheet["file"])
        print(f"Lese Sheet: {sheet_file}")
        if os.path.exists(sheet_file):
            pdf = PdfReader(sheet_file)
            for page in pdf.pages:
                writer.add_page(page)
        else:
            print(f"Warnung: Sheet {sheet_file} nicht gefunden!")

# -------------------------
# 4. Setlist-PDF erstellen (nur Übersichtseiten)
# -------------------------
story = []

# Titelseite
add_title_page(story, data.get("meta", {}), styles)

# Set-Übersichtsseiten für alle Songs vorbereiten
#for set_data in data["sets"]:
for set_index, set_data in enumerate(data["sets"]):
    songs = set_data["songs"]
    
    # 🔴 Sonderfall: Pause / leeres Set
    if not songs:
        add_pause_page(story, set_data["name"])
        continue
    
    # 🎵 Normales Set
    for active_index in range(len(songs)):
        add_set_overview(story, set_data["name"], songs, active_index, set_index, styles)

# PDF mit allen Übersichtsseiten erstellen
doc = SimpleDocTemplate(SETLIST_MAIN, pagesize=A4)
doc.build(story)
print(f"Haupt-Setlist PDF erstellt: {SETLIST_MAIN}")

# -------------------------
# 5. Haupt-PDF + Sheets zusammenführen
# -------------------------
writer = PdfWriter()
main_pdf = PdfReader(SETLIST_MAIN)
page_cursor = 0

writer.add_page(main_pdf.pages[page_cursor])
page_cursor += 1


for set_data in data["sets"]:
    
    songs = set_data["songs"]
    if not songs:
        writer.add_page(main_pdf.pages[page_cursor])
        page_cursor += 1
        continue
        
    
    for song in songs:
        # 1️⃣ Set-Übersichtsseite für diesen Song
        writer.add_page(main_pdf.pages[page_cursor])
        page_cursor += 1

        # 2️⃣ Sheets für aktuellen Song **nach der Set-Übersichtsseite**
        append_song_sheets(writer, song, SELECTED_TAG)

# Finale PDF schreiben

FINAL_PDF = data.get("meta").get("event") + ".pdf"
with open(FINAL_PDF, "wb") as f:
    writer.write(f)

print(f"Fertige Setlist inklusive Sheets erstellt: {FINAL_PDF}")
