from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium


BASE = Path(__file__).resolve().parent
PDFS = sorted(BASE.glob("0*-*.pdf"))
OUT = BASE / "word_preview"
OUT.mkdir(exist_ok=True)


def render_pdf(pdf_path: Path):
    doc = pdfium.PdfDocument(str(pdf_path))
    thumbs = []
    page_paths = []
    for idx in range(len(doc)):
        page = doc[idx]
        bitmap = page.render(scale=1.4)
        pil = bitmap.to_pil().convert("RGB")
        page_path = OUT / f"{pdf_path.stem}-page-{idx + 1}.png"
        pil.save(page_path)
        page_paths.append(page_path)

        thumb = pil.copy()
        thumb.thumbnail((360, 480))
        thumbs.append((idx + 1, thumb))

    cols = 2
    cell_w, cell_h = 420, 550
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, max(1, rows) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    for n, thumb in thumbs:
        slot = n - 1
        x = (slot % cols) * cell_w + 30
        y = (slot // cols) * cell_h + 34
        draw.text((x, y - 26), f"Page {n}", fill=(40, 40, 40), font=font)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y, x + thumb.width, y + thumb.height), outline=(180, 180, 180), width=1)

    sheet_path = OUT / f"{pdf_path.stem}-contact.png"
    sheet.save(sheet_path)
    print(f"{pdf_path.name}: {len(doc)} pages -> {sheet_path}")


def main():
    for pdf in PDFS:
        render_pdf(pdf)


if __name__ == "__main__":
    main()
