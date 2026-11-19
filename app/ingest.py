"""Reading documents (PDF, Word, text) into chunks, with safety checks on the upload."""
from __future__ import annotations
import hashlib, io, re, zipfile
from . import config

class Rejected(ValueError): pass
def kind_of(data: bytes) -> str | None:
    """From the first bytes, never from the file name."""
    if data[:5] == b"%PDF-": return "pdf"
    if data[:4] == b"PK\x03\x04":
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
            return "docx" if any(n.startswith("word/") for n in names) else None
        except zipfile.BadZipFile: return None
    if b"\x00" not in data[:4096]:
        try: data[:4096].decode("utf-8"); return "txt"
        except UnicodeDecodeError: return None
    return None
def safe_name(name: str) -> str: return re.sub(r"[^A-Za-z0-9._ -]", "_", (name or "document").split("/")[-1].split("\\")[-1])[:80] or "document"
def check_upload(name: str, data: bytes) -> str:
    if not data: raise Rejected("The file is empty")
    if len(data) > config.MAX_UPLOAD: raise Rejected(f"The file is larger than {config.MAX_UPLOAD // 1048576} MB")
    k = kind_of(data)
    if not k: raise Rejected("Only PDF, Word (.docx) and plain text files are accepted")
    if k == "docx":
        z = zipfile.ZipFile(io.BytesIO(data))
        if sum(i.file_size for i in z.infolist()) > config.MAX_UNZIPPED: raise Rejected("The Word file expands to an unreasonable size")
    return k

# ---- reading: every reader returns blocks of (heading, page, text) and the document's own title
def read_docx(data):
    import docx
    d = docx.Document(io.BytesIO(data)); title = None; blocks = []; heading = ""
    for p in d.paragraphs:
        t = p.text.strip(); st = (p.style.name or "").lower()
        if not t: continue
        if st == "title": title = t
        elif st.startswith("heading"): heading = t
        else: blocks.append((heading, 1, t))
    return title, blocks, 1
def read_pdf(data):
    import pdfplumber
    blocks = []; heading = ""; title = None
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        n = len(pdf.pages)
        if n > config.MAX_PAGES: raise Rejected(f"The PDF has more than {config.MAX_PAGES} pages")
        sizes = []
        for pg in pdf.pages: sizes += [round(c["size"]) for c in pg.chars]
        body = max(set(sizes), key=sizes.count) if sizes else 10
        for i, pg in enumerate(pdf.pages, 1):
            for ln in pg.extract_text_lines():
                t = ln["text"].strip(); ch = ln["chars"]
                if not t or not ch: continue
                sz = max(c["size"] for c in ch); bold = "bold" in ch[0]["fontname"].lower()
                if sz >= body * 1.7 and title is None: title = t
                elif (bold or sz > body * 1.15) and len(t) < 80 and not t.endswith("."): heading = t
                else: blocks.append((heading, i, t))
    return title, blocks, n
def read_txt(data):
    text = data.decode("utf-8", "replace"); lines = text.splitlines(); title = None; heading = ""; blocks = []
    for i, ln in enumerate(lines):
        t = ln.strip()
        if not t or re.fullmatch(r"[=\-]{3,}", t): continue
        if i == 0 and not t.startswith("#"): title = t
        elif t.startswith("#"): heading = t.lstrip("# ").strip()
        else: blocks.append((heading, 1, t))
    return title, blocks, 1
READERS = {"pdf": read_pdf, "docx": read_docx, "txt": read_txt}

def sentences(text: str) -> list[str]:
    t = re.sub(r"\b(No|St|Inc|Ltd|Co|e\.g|i\.e)\.", r"\1", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]
def chunk(blocks, max_words=110):
    """One chunk per heading; a long heading is split on sentence boundaries. PDF lines are joined into paragraphs first."""
    groups = []
    for h, pg, t in blocks:
        if groups and groups[-1][0] == h and groups[-1][1] == pg and not re.search(r"[.!?]$", groups[-1][2][-1:] or "."): groups[-1][2] += " " + t
        else: groups.append([h, pg, t])
    by = {}
    for h, pg, t in groups: by.setdefault((h, pg), []).append(t)
    out = []
    for (h, pg), paras in by.items():
        cur = []; n = 0
        for s in [s for p in paras for s in sentences(p)]:
            w = len(s.split())
            if cur and n + w > max_words: out.append((h, pg, " ".join(cur))); cur, n = [], 0
            cur.append(s); n += w
        if cur: out.append((h, pg, " ".join(cur)))
    return out
def read_document(name: str, data: bytes):
    k = check_upload(name, data); title, blocks, pages = READERS[k](data)
    chunks = chunk(blocks)
    if not chunks: raise Rejected("No readable text was found in the file. Scanned documents need OCR first")
    return {"kind": k, "title": title or safe_name(name).rsplit(".", 1)[0], "pages": pages, "chunks": chunks, "sha": hashlib.sha256(data).hexdigest()}
