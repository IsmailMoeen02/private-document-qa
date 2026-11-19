"""Writes the dummy documents to data/docs/ and a manifest.  python data/make_docs.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import DOCS
OUT = Path(__file__).resolve().parent / "docs"; OUT.mkdir(exist_ok=True)

def pdf(d, p):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    ss = getSampleStyleSheet(); doc = SimpleDocTemplate(str(p), pagesize=A4, leftMargin=60, rightMargin=60, topMargin=60, bottomMargin=60)
    st = [Paragraph(d["title"], ss["Title"]), Spacer(1, 12)]
    for i, (h, ps) in enumerate(d["sections"]):
        if i and i % 2 == 0: st.append(PageBreak())        # a section pair per page, so citations carry real page numbers
        st.append(Paragraph(h, ss["Heading2"]))
        for t in ps: st += [Paragraph(t.replace("&", "&amp;"), ss["BodyText"]), Spacer(1, 6)]
    doc.build(st)
def docx(d, p):
    import docx as dx
    doc = dx.Document(); doc.add_heading(d["title"], 0)
    for h, ps in d["sections"]:
        doc.add_heading(h, 1)
        for t in ps: doc.add_paragraph(t)
    doc.save(str(p))
def txt(d, p):
    p.write_text(d["title"] + "\n" + "=" * len(d["title"]) + "\n\n" + "\n\n".join(f"## {h}\n\n" + "\n\n".join(ps) for h, ps in d["sections"]) + "\n")
W = {"pdf": pdf, "docx": docx, "txt": txt}
manifest = []
for d in DOCS:
    p = OUT / f"{d['id']}.{d['format']}"; W[d["format"]](d, p); manifest.append({"file": p.name, "title": d["title"], "groups": d["groups"]})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1)); print(len(manifest), "documents written to", OUT)
