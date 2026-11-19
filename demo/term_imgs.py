"""Terminal-style images of the real test and evaluation output.
  pytest -v > /tmp/pytest_pq.txt ; (eval outputs saved in eval/*_now.txt) ; python demo/term_imgs.py"""
import html
from collections import Counter
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent.parent; A = ROOT / "assets"
def page(title, text, w):
    return f"""<body style="margin:0;background:linear-gradient(135deg,#e5ede0,#f6f3e8 60%,#f1e6d6);display:grid;place-items:center;height:100vh">
    <div style="width:{w - 80}px;border-radius:14px;overflow:hidden;box-shadow:0 18px 50px rgba(47,93,70,.25);background:#22302a">
    <div style="background:#33443b;padding:11px 16px;display:flex;gap:8px;align-items:center"><i style="width:12px;height:12px;border-radius:50%;background:#e29b94"></i><i style="width:12px;height:12px;border-radius:50%;background:#e9c46a"></i><i style="width:12px;height:12px;border-radius:50%;background:#7fbf9f"></i><span style="color:#b9c8bd;font:600 14px 'DejaVu Sans',sans-serif;margin-left:10px">{title}</span></div>
    <pre style="margin:0;padding:20px 24px;color:#eef3ea;font:15px/1.55 'DejaVu Sans Mono',monospace;white-space:pre-wrap">{text}</pre></div></body>"""
G = lambda t: f'<b style="color:#8fd3b0">{t}</b>'; Y = lambda t: f'<b style="color:#f0c987">{t}</b>'
with sync_playwright() as pw:
    b = pw.chromium.launch()
    lines = Path("/tmp/pytest_pq.txt").read_text().splitlines()
    tests = [l for l in lines if l.startswith("tests/")]; summary = [l for l in lines if " passed" in l and not l.startswith("tests/")][-1]
    per = Counter(l.split("::")[0].replace("tests/", "") for l in tests)
    body = "$ pytest -v\n\n" + "\n".join(f'{G("PASSED")}  {html.escape(f):<22} {n:>3} tests' for f, n in per.items()) + f"\n\n{G(html.escape(summary.strip('= ')))}"
    pg = b.new_page(viewport={"width": 1280, "height": 150 + 26 * len(per) + 60}, device_scale_factor=2); pg.set_content(page("pytest: automated tests, offline", body, 1280)); pg.screenshot(path=str(A / "14_tests_passing.png"))
    rd = lambda n: (ROOT / "eval" / n).read_text().strip()
    body = "$ python eval/run_eval.py\n\n" + "DEVELOPMENT SET (tuned on)\n" + rd("dev_now.txt").split("\n", 1)[1] + "\n\nHELD-OUT SET, FIRST RUN (before any change)\n" + "\n".join(rd("heldout_first_run.txt").split("\n")[:5]).split("\n", 1)[1] + "\n\nHELD-OUT SET, AFTER GENERIC FIXES (no longer a clean test)\n" + rd("heldout_now.txt").split("\n", 1)[1] + "\n\nFRESH SET (written after the fixes, run once)\n" + rd("fresh_now.txt").split("\n", 1)[1]
    body = html.escape(body)
    for k in ("DEVELOPMENT SET", "HELD-OUT SET, FIRST RUN", "HELD-OUT SET, AFTER", "FRESH SET"): body = body.replace(k, Y(k), 1)
    pg = b.new_page(viewport={"width": 1280, "height": 130 + 25 * (body.count("\n") + 3)}, device_scale_factor=2); pg.set_content(page("Evaluation: dummy documents against hand-written answers", body, 1280)); pg.screenshot(path=str(A / "15_evaluation.png"))
    b.close()
print("ok")
