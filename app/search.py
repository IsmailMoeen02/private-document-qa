"""Local search over the chunks a person is allowed to read. BM25 on stemmed words, plus character n-gram similarity for spelling and word forms, plus a company glossary
(editable) for words people use that the documents do not. An index is built per set of readable documents, so text a person may not read is never in the index they query."""
from __future__ import annotations
import math, re
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

STOP = set("a an the of to in on at for from by with and or but if is are was were be been am do does did can could should would will shall may might i me my we our you your it its this that these those there here what which who whom whose when where why how any some much many about into over under than then so as not no yes also just more most other up out off per get got have has had having tell please charge need want use make let staff employee company colleague people".split())
IRREGULAR = {"kept": "keep", "held": "hold", "paid": "pay", "taken": "take", "took": "take", "spent": "spend", "bought": "buy", "left": "leave", "gave": "give", "given": "give", "sent": "send", "lost": "lose", "begun": "begin", "written": "write", "wrote": "write", "men": "man", "children": "child"}
def stem(w: str) -> str:
    if w in IRREGULAR: return IRREGULAR[w]
    for suf, rep in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", ""), ("ly", "")):
        if len(w) > len(suf) + 2 and w.endswith(suf) and not w.endswith("ss"): return _noe(w[: -len(suf)] + rep)
    return _noe(w)
def _noe(w): return w[:-1] if len(w) > 4 and w.endswith("e") else w          # change and changed meet at "chang"
def tokens(text: str, keep_stop=False) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9][a-z0-9'.,\-]*[a-z0-9]|[a-z0-9]", text.lower().replace("’", "'")):
        w = w.strip(".,'-")
        for part in ([w] if re.fullmatch(r"[\d][\d,.]*", w) else re.split(r"[-']", w)):
            if part and (keep_stop or part not in STOP): out.append(stem(part) if not part[0].isdigit() else part.replace(",", ""))
    return out

class Index:
    def __init__(self, chunks: list[dict], glossary: dict[str, str] | None = None):
        """chunks: dicts with id, doc, title, heading, text. glossary: phrase -> words that mean the same here."""
        self.chunks = chunks; self.gloss = {tuple(tokens(k)): tokens(v) for k, v in (glossary or {}).items() if tokens(k)}
        self.docs = [tokens(f"{c['title']} {c['heading']} {c['heading']} {c['text']}") for c in chunks]; self.n = len(chunks)
        self.df = Counter(t for d in self.docs for t in set(d)); self.avg = (sum(len(d) for d in self.docs) / self.n) if self.n else 1
        self.tf = [Counter(d) for d in self.docs]
        self.vec = None
        if self.n:
            self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1); self.mat = self.vec.fit_transform([f"{c['heading']} {c['text']}" for c in chunks])
    def idf(self, t): return math.log(1 + (self.n - self.df.get(t, 0) + .5) / (self.df.get(t, 0) + .5))
    def expand(self, q: list[str]) -> dict[str, float]:
        """Query words with weights: the person's own words at 1.0, glossary words at 0.7."""
        w = {t: 1.0 for t in q}; self._used = []
        for phrase, means in self.gloss.items():
            k = len(phrase)
            if any(tuple(q[i:i + k]) == phrase for i in range(len(q) - k + 1)):
                self._used.append((phrase, means))
                for m in means: w.setdefault(m, 0.7)
        return w
    def bm25(self, i, w, k1=1.4, b=.75):
        tf = self.tf[i]; dl = len(self.docs[i]); s = 0.0
        for t, wt in w.items():
            f = tf.get(t, 0)
            if f: s += wt * self.idf(t) * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avg))
        return s
    def search(self, question: str, k: int = 4) -> list[dict]:
        q = tokens(question)
        if not q or not self.n: return []
        w = self.expand(q); used = list(self._used); mass = sum(self.idf(t) * wt for t, wt in w.items()) or 1.0
        qs = Counter(t for t in q if not t[0].isdigit())     # numbers in the question are parameters, not topic words, so they do not count against coverage
        own_mass = sum(self.idf(t) for t in qs) or 1.0
        bm = np.array([self.bm25(i, w) for i in range(self.n)]); cos = (self.mat @ self.vec.transform([" ".join(question.lower().split())]).T).toarray().ravel()
        rows = []
        for i in range(self.n):
            have = set(self.docs[i]); cov = sum(self.idf(t) for t in qs if t in have) / own_mass          # share of the person's own words found here
            said = sum(self.idf(t) for ph, means in used for t in set(ph) if t not in have and any(m in have for m in means))      # a word the documents lack, but whose glossary meaning is here, counts as found
            cov_x = (sum(self.idf(t) * wt for t, wt in w.items() if t in have) + said) / mass                  # the same, counting glossary words
            rows.append((i, bm[i], cos[i], max(cov, min(cov_x, 1.0) * .9)))
        mb = max(r[1] for r in rows) or 1.0; mc = max(r[2] for r in rows) or 1.0
        out = []
        for i, b, c, cov in rows:
            fused = .55 * b / mb + .25 * c / mc + .2 * cov
            out.append({"i": i, "chunk": self.chunks[i], "bm25": float(b), "cos": float(c), "coverage": float(cov), "fused": float(fused),
                        "confidence": float(.6 * cov + .4 * min(1.0, c * 2))})
        out.sort(key=lambda r: -r["fused"]); return out[:k]
