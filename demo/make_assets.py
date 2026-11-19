"""Records the product tour and takes the portfolio screenshots of the running Private Q&A app and its n8n version.

  python demo/make_assets.py shots | tour | n8nvideo | cover | arch
Needs: playwright with chromium, ffmpeg; n8n running on :5678 for shots and n8nvideo (n8n/README.md). The app is started here on :8796."""
import base64, json, os, shutil, subprocess, sys, threading, time, urllib.request, http.cookiejar
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"; A.mkdir(exist_ok=True)
PORT = 8796; URL = f"http://127.0.0.1:{PORT}"
N8N = "http://127.0.0.1:5678"; N8N_USER, N8N_PASS = "owner@leaddesk.example", "LeadDesk#2026"
NOW = "2026-11-05T09:30"; SLACK_LOG = "/tmp/fake_slack_pq.log"
INK, PRI, CLAY, BG, SAGE = "#22302a", "#2f5d46", "#b0704a", "#f6f3e8", "#e5ede0"

def start(tag, seeded=True):
    w = Path(f"/tmp/pq_{tag}"); shutil.rmtree(w, ignore_errors=True); w.mkdir()
    env = dict(os.environ, DB_PATH=str(w / "p.db"), DEMO_MODE="1", FAKE_NOW=NOW, LLM_PROVIDER="rules", INBOUND_KEY="demo-inbound-key", INBOUND_PER_MIN="100000", LOGIN_PER_MIN="1000", ASK_PER_MIN="1000")
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)], cwd=ROOT, env=env, stdout=open(f"/tmp/pq_{tag}.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(80):
        try: urllib.request.urlopen(URL + "/health", timeout=1); break
        except Exception: time.sleep(0.3)
    else: raise RuntimeError("server did not start")
    if seeded: subprocess.run([sys.executable, "scripts/seed.py", URL], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    return srv, env

INIT = """
(() => {
 function init(){
  if(document.getElementById('__cap')) return;
  const s=document.createElement('style'); s.textContent=`
  body{padding-top:64px!important;box-sizing:border-box}
  header{top:64px!important}
  #login{min-height:calc(100vh - 64px)!important}
  #__cur{position:fixed;z-index:99999;width:24px;height:24px;border-radius:50%;background:rgba(176,112,74,.3);border:2px solid #b0704a;pointer-events:none;transform:translate(-50%,-50%);left:-60px;top:-60px;transition:transform .08s}
  #__cur.dn{background:rgba(176,112,74,.75);transform:translate(-50%,-50%) scale(.75)}
  #__cap{position:fixed;left:0;right:0;top:0;height:64px;z-index:99998;background:#22302a;color:#fff;font:600 17px 'DejaVu Sans',system-ui,sans-serif;display:flex;align-items:center;justify-content:center;padding:0 24px;text-align:center}
  #__cap span{opacity:0;transition:opacity .35s}#__cap span.on{opacity:1}`;
  document.head.appendChild(s);
  const c=document.createElement('div');c.id='__cur';document.body.appendChild(c);
  const k=document.createElement('div');k.id='__cap';k.innerHTML='<span></span>';document.body.appendChild(k);
  document.addEventListener('mousemove',e=>{c.style.left=e.clientX+'px';c.style.top=e.clientY+'px'},true);
  document.addEventListener('mousedown',()=>c.classList.add('dn'),true);document.addEventListener('mouseup',()=>c.classList.remove('dn'),true);
 }
 if(document.readyState!=='loading')init();else document.addEventListener('DOMContentLoaded',init);
})();
"""
def cap(pg, text, wait=0):
    pg.evaluate("t=>{const s=document.querySelector('#__cap span');if(!s)return;s.classList.remove('on');setTimeout(()=>{s.textContent=t;s.classList.add('on')},200)}", text); pg.wait_for_timeout(wait)
def glide(pg, sel, steps=24, nth=0):
    el = pg.locator(sel).nth(nth); el.scroll_into_view_if_needed(); bb = el.bounding_box(); pg.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, steps=steps)
def click(pg, sel, nth=0):
    glide(pg, sel, nth=nth); pg.wait_for_timeout(220); pg.mouse.down(); pg.wait_for_timeout(90); pg.mouse.up(); pg.wait_for_timeout(300)
def typ(pg, sel, text, delay=38):
    click(pg, sel); pg.keyboard.type(text, delay=delay); pg.wait_for_timeout(250)
def card(pg, title, sub, foot=""):
    pg.set_content(f"""<body style="margin:0;height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,{SAGE},{BG} 60%,#f1e6d6);font-family:Inter,'DejaVu Sans',sans-serif;color:{INK};text-align:center">
    <div style="max-width:980px;padding:30px"><div style="width:84px;height:84px;margin:0 auto 26px;border-radius:24px;background:{PRI};box-shadow:0 14px 30px #2f5d4655;display:grid;place-items:center"><div style="width:34px;height:34px;border:6px solid #fff;border-radius:50%"></div></div>
    <div style="font-size:46px;font-weight:750;line-height:1.15;letter-spacing:-1px">{title}</div><div style="font-size:21px;color:#66736b;margin-top:18px;line-height:1.5">{sub}</div>
    <div style="font-size:15px;color:{PRI};margin-top:34px;letter-spacing:.4px;font-weight:600">{foot}</div></div></body>""")
def ask(pg, q, typed=True):
    if typed: typ(pg, "#aq", q)
    else: pg.fill("#aq", q)
    click(pg, "#ab"); pg.wait_for_selector(".thread .ans", timeout=15000); pg.wait_for_timeout(900)
def who(pg, u):
    pg.wait_for_selector("[data-d=" + u + "]") if pg.locator("#login:not(.hide)").count() else None
def sign_as(pg, u):
    if pg.locator("#out:visible").count(): click(pg, "#out"); pg.wait_for_timeout(400)
    click(pg, f"[data-d={u}]"); pg.wait_for_selector("#nav button"); pg.wait_for_timeout(900)

# ---------- n8n ----------
def n8n_login(pg):
    pg.goto(N8N + "/signin"); pg.wait_for_timeout(1800)
    pg.fill("input[type=email], input[name=emailOrLdapLoginId]", N8N_USER); pg.fill("input[type=password]", N8N_PASS); pg.keyboard.press("Enter"); pg.wait_for_timeout(3000)
def n8n_id():
    jar = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.open(urllib.request.Request(N8N + "/rest/login", data=json.dumps({"emailOrLdapLoginId": N8N_USER, "password": N8N_PASS}).encode(), headers={"Content-Type": "application/json"}))
    for w in json.load(op.open(N8N + "/rest/workflows"))["data"]:
        if w["name"].startswith("Staff questions") and w.get("active") and not w.get("isArchived"): return w["id"]
    raise RuntimeError("workflow not imported, run n8n/run_in_n8n.py --import-only")
def fire(path, user, question, wait=120):
    req = urllib.request.Request(N8N + path, data=json.dumps({"user": user, "question": question}).encode(), headers={"Content-Type": "application/json"}); return json.load(urllib.request.urlopen(req, timeout=wait))

def shots():
    srv, env = start("shots"); slack = subprocess.Popen([sys.executable, str(ROOT / "n8n" / "fake_slack.py"), "8799", SLACK_LOG])
    try:
        wid = n8n_id(); os.path.exists(SLACK_LOG) and os.remove(SLACK_LOG)
        with sync_playwright() as pw:
            b = pw.chromium.launch(); ctx = b.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=2); pg = ctx.new_page()
            n8n_login(pg); pg.goto(f"{N8N}/workflow/{wid}"); pg.wait_for_selector('[data-node-name="Reply with result"]', timeout=60000); pg.wait_for_timeout(1500); pg.screenshot(path=str(A / "11_n8n_workflow.png"))
            for u, q in [("ayesha", "How many days of annual leave do I get?"), ("ayesha", "What is the salary range for Band C?"), ("omar", "What is the salary range for Band C?")]: print("n8n:", u, fire("/webhook/ask-documents", u, q)["outcome"])
            pg.goto(f"{N8N}/workflow/{wid}/executions"); pg.wait_for_timeout(3500); pg.screenshot(path=str(A / "12_n8n_executions.png"))
            bb = pg.locator('[data-node-name="Ask the documents"]').first.bounding_box(); pg.mouse.dblclick(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(3000); pg.screenshot(path=str(A / "13_n8n_one_run.png"))
            b.close()
        print("chat messages:", [json.loads(l)["text"][:60] for l in open(SLACK_LOG).read().splitlines() if l.strip()] if os.path.exists(SLACK_LOG) else [])
        app_shots()
    finally: srv.terminate(); slack.terminate()

def app_shots():
    with sync_playwright() as pw:
        b = pw.chromium.launch(); ctx = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2); pg = ctx.new_page()
        pg.goto(URL + "/"); pg.wait_for_timeout(600); pg.screenshot(path=str(A / "01_login.png"))
        pg.click("[data-d=ayesha]"); pg.wait_for_selector("#aq"); pg.wait_for_timeout(400)
        ask(pg, "How many days of annual leave do I get?", typed=False); pg.screenshot(path=str(A / "02_answer_with_source.png"))
        ask(pg, "What is the salary range for Band C?", typed=False); pg.screenshot(path=str(A / "03_not_allowed_looks_like_not_found.png"))
        pg.click("#out"); pg.click("[data-d=omar]"); pg.wait_for_selector("#aq"); ask(pg, "What is the salary range for Band C?", typed=False); pg.screenshot(path=str(A / "04_hr_sees_it.png"))
        pg.click("#out"); pg.click("[data-d=admin]"); pg.wait_for_selector("#aq")
        for k, n in [("lib", "05_library_and_access"), ("log", "06_questions_and_gaps"), ("usr", "07_users_and_groups"), ("glo", "08_glossary")]:
            pg.click(f"nav [data-k={k}]"); pg.wait_for_timeout(900); pg.screenshot(path=str(A / f"{n}.png"))
        m = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True); mp = m.new_page()
        mp.goto(URL + "/"); mp.click("[data-d=ayesha]"); mp.wait_for_selector("#aq"); mp.fill("#aq", "How long do we keep invoices?"); mp.click("#ab"); mp.wait_for_selector(".thread .ans"); mp.wait_for_timeout(700); mp.screenshot(path=str(A / "09_mobile.png"))
        b.close()
    print("app screenshots done")

def tour():
    srv, env = start("tour"); vpath = None
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            ctx = b.new_context(viewport={"width": 1440, "height": 900}, record_video_dir=str(A / "_vid"), record_video_size={"width": 1440, "height": 900})
            ctx.add_init_script(INIT); pg = ctx.new_page()
            card(pg, "Private Q&amp;A", "Ask questions about your company's own documents.<br>Answers come with the source, and only from what you are allowed to read.", "Python  |  FastAPI  |  runs on your own machine"); pg.wait_for_timeout(4200)
            pg.goto(URL + "/"); pg.wait_for_selector("[data-d=ayesha]"); pg.wait_for_timeout(800)
            cap(pg, "1. Sign in. Each person sees only the documents their groups allow", 3200)
            click(pg, "[data-d=ayesha]"); pg.wait_for_selector("#aq"); pg.wait_for_timeout(900)
            cap(pg, "Ayesha is general staff. She can read 7 of the 12 documents", 3800)
            cap(pg, "2. Ask in plain words", 400); ask(pg, "How many days of annual leave do I get?")
            cap(pg, "The answer is taken from the document, not made up. The source is shown", 4200)
            cap(pg, "The exact sentence is highlighted in its passage, with the page", 4600)
            cap(pg, "3. Ask with different words from the document", 400); ask(pg, "Can I work from home on Fridays?"); cap(pg, "'Work from home' is matched to the policy's 'remote work' by the company glossary", 4600)
            cap(pg, "4. Ask something the documents do not cover", 400); ask(pg, "What is the dress code?"); cap(pg, "It says so. It does not guess", 4200)
            cap(pg, "5. Ask about a document she is not allowed to read", 400); ask(pg, "What is the salary range for Band C?"); cap(pg, "The same refusal. She cannot tell the document exists, and its text was never searched", 5200)
            cap(pg, "6. Omar is in HR. Same question, different access", 400); sign_as(pg, "omar"); ask(pg, "What is the salary range for Band C?"); cap(pg, "Omar gets the answer, with the HR-only document as the source", 4600)
            cap(pg, "7. The administrator sees the library and who may read each document", 400); sign_as(pg, "admin"); click(pg, "nav [data-k=lib]"); pg.wait_for_timeout(1000); cap(pg, "Groups can be changed per document, and take effect at once", 4200)
            cap(pg, "Add a document: upload a file and choose who can read it", 400); pg.set_input_files("#uff", "/tmp/bicycle.txt"); pg.wait_for_timeout(500); click(pg, "#ufb"); pg.wait_for_timeout(1500); cap(pg, "Added and searchable straight away", 3000)
            cap(pg, "8. Questions: what people asked and what the documents could not answer", 400); click(pg, "nav [data-k=log]"); pg.wait_for_timeout(1200); cap(pg, "Gaps show which documents are missing, and which words to add to the glossary", 5200)
            pg.mouse.wheel(0, 700); pg.wait_for_timeout(1400); cap(pg, "Every question is logged: who, when, what, and which document it used", 4200)
            cap(pg, "9. Users and groups, and the glossary of company words", 400); click(pg, "nav [data-k=usr]"); pg.wait_for_timeout(2400); click(pg, "nav [data-k=glo]"); pg.wait_for_timeout(3000)
            cap(pg, "10. Back as Ayesha: the document just uploaded can already be asked about", 500); sign_as(pg, "ayesha"); ask(pg, "Where are bicycles kept?"); cap(pg, "Answered from the new document", 3600)
            card(pg, "Private Q&amp;A", "Answers with sources, access by group,<br>and a refusal when the documents do not say.", "Code, tests and case study included"); pg.wait_for_timeout(3600)
            video = pg.video; ctx.close(); b.close(); vpath = video.path()
    finally: srv.terminate()
    encode(vpath, A / "Private_QA_Tour.mp4")

def encode(vpath, out, cut=None):
    vf = ["-filter_complex", f"[0:v]trim=0:{cut[0]:.2f},setpts=PTS-STARTPTS[a];[0:v]trim=start={cut[1]:.2f},setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]", "-map", "[v]"] if cut else []
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(vpath), *vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(A / "_vid", ignore_errors=True); print("wrote", out, f"{out.stat().st_size // 1024} KB")

def n8nvideo():
    srv, env = start("n8n"); slack = subprocess.Popen([sys.executable, str(ROOT / "n8n" / "fake_slack.py"), "8799", SLACK_LOG])
    try:
        wid = n8n_id()
        with sync_playwright() as pw:
            b = pw.chromium.launch(); c0 = b.new_context(viewport={"width": 1600, "height": 900}); p0 = c0.new_page(); n8n_login(p0); state = c0.storage_state(); c0.close()
            ctx = b.new_context(viewport={"width": 1600, "height": 900}, storage_state=state, record_video_dir=str(A / "_vid"), record_video_size={"width": 1600, "height": 900})
            ctx.add_init_script(INIT.replace("header{top:64px!important}", "")); t0 = time.time(); pg = ctx.new_page()
            card(pg, "The same questions, from chat", "A workflow that takes a question from a chat message, asks Private Q&amp;A as that person,<br>and posts the answer with its source, or says it found nothing.", "n8n  |  Webhook  |  HTTP Request  |  Switch  |  Chat reply"); pg.wait_for_timeout(4000)
            cut_a = time.time() - t0 - .3; pg.goto(f"{N8N}/workflow/{wid}"); pg.wait_for_selector('[data-node-name="Reply with result"]', timeout=60000); pg.wait_for_timeout(600); cut_b = time.time() - t0 - .3
            pg.wait_for_timeout(2500)
            cap(pg, "The workflow. A chat message comes in (a test inbox here, Slack or Teams in production)", 4400)
            cap(pg, "It asks Private Q&A as the person who wrote the message, so their document access applies", 4400)
            cap(pg, "Run 1: Ayesha asks about annual leave", 500); click(pg, "text=Execute workflow"); pg.wait_for_timeout(1800)
            t = threading.Thread(target=lambda: fire("/webhook-test/ask-documents", "ayesha", "How many days of annual leave do I get?")); t.start(); pg.wait_for_timeout(9000); t.join()
            cap(pg, "Answered. The reply to chat carries the answer and its source", 4200)
            bb = pg.locator('[data-node-name="Write reply with source"]').first.bounding_box(); pg.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, steps=25); pg.wait_for_timeout(300)
            pg.mouse.dblclick(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(2600); cap(pg, "The message that was posted: the answer, then Source: document, section, page", 4600)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(800)
            cap(pg, "Run 2: Ayesha asks about HR salary bands, which she may not read", 500); click(pg, "text=Execute workflow"); pg.wait_for_timeout(1800)
            t = threading.Thread(target=lambda: fire("/webhook-test/ask-documents", "ayesha", "What is the salary range for Band C?")); t.start(); pg.wait_for_timeout(9000); t.join()
            cap(pg, "No answer branch. The reply does not reveal that the document exists", 4800)
            cap(pg, "Every run is recorded in n8n, and every question is logged in Private Q&A", 400)
            pg.goto(f"{N8N}/workflow/{wid}/executions"); pg.wait_for_timeout(3500); cap(pg, "A failed or odd run can be found and replayed", 4000)
            card(pg, "Two ways to ask", "In the app, or from the chat people already use.<br>Same documents, same access rules, same log.", "n8n workflow file included"); pg.wait_for_timeout(3600)
            video = pg.video; ctx.close(); b.close(); vpath = video.path()
    finally: srv.terminate(); slack.terminate()
    encode(vpath, A / "n8n_Flow_Demo.mp4", cut=(cut_a, cut_b))

def cover():
    img = base64.b64encode((A / "02_answer_with_source.png").read_bytes()).decode()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=2)
        pg.set_content(f"""<body style="margin:0;width:1600px;height:900px;background:linear-gradient(135deg,{SAGE},{BG} 55%,#f1e6d6);font-family:Inter,'DejaVu Sans',sans-serif;color:{INK};position:relative;overflow:hidden">
        <div style="position:absolute;left:84px;top:150px;width:620px">
          <div style="display:inline-block;background:#fff;border:1px solid #d5dcc6;color:{PRI};font-weight:700;font-size:20px;padding:9px 18px;border-radius:999px">Private document Q&amp;A</div>
          <div style="font-size:74px;font-weight:800;line-height:1.04;letter-spacing:-2.5px;margin-top:28px">Private Q&amp;A</div>
          <div style="font-size:28px;color:#66736b;line-height:1.45;margin-top:26px">Ask questions about your own documents. Answers with the source, only from what each person may read.</div>
          <div style="display:flex;gap:12px;margin-top:40px;flex-wrap:wrap">{"".join(f'<span style="background:{PRI};color:#fff;font-weight:650;font-size:20px;padding:10px 18px;border-radius:12px">{t}</span>' for t in ("Search", "Cite", "Refuse", "Log"))}</div>
          <div style="font-size:19px;color:#8a9890;margin-top:30px">Python  |  FastAPI  |  SQLite  |  runs on one machine  |  n8n</div></div>
        <div style="position:absolute;left:740px;top:110px;width:760px;border-radius:18px;overflow:hidden;box-shadow:0 40px 90px rgba(47,93,70,.25);border:1px solid #d5dcc6;background:#fff">
          <div style="background:#ecebdc;padding:12px 16px;display:flex;gap:8px"><i style="width:12px;height:12px;border-radius:50%;background:#e29b94"></i><i style="width:12px;height:12px;border-radius:50%;background:#e9c46a"></i><i style="width:12px;height:12px;border-radius:50%;background:#7fbf9f"></i></div>
          <img src="data:image/png;base64,{img}" style="width:760px;display:block;margin-top:-4px"></div></body>""")
        pg.wait_for_timeout(400); pg.screenshot(path=str(A / "00_cover.png")); b.close()
    print("cover done")

def architecture():
    box = lambda x, y, w, h, t, sub="", fill="#fff", stroke="#cfd6bf", col=INK: f"""<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/><text x="{x + w / 2}" y="{y + h / 2 - (8 if sub else -6)}" text-anchor="middle" font-size="21" font-weight="700" fill="{col}">{t}</text>{f'<text x="{x + w / 2}" y="{y + h / 2 + 18}" text-anchor="middle" font-size="15" fill="{"#dbe8de" if fill == PRI else "#66736b"}">{sub}</text>' if sub else ""}"""
    arrow = lambda x1, y1, x2, y2: f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{PRI}" stroke-width="3" marker-end="url(#a)" fill="none"/>'
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="640" viewBox="0 0 1500 640" font-family="Inter,'DejaVu Sans',sans-serif">
    <defs><marker id="a" markerUnits="userSpaceOnUse" markerWidth="14" markerHeight="14" refX="12" refY="7" orient="auto"><path d="M0 1 L13 7 L0 13 z" fill="{PRI}"/></marker></defs>
    <rect width="1500" height="640" fill="{BG}"/>
    {box(40, 130, 210, 90, "Web app", "sign in, ask", SAGE, PRI)}
    {box(40, 250, 210, 90, "Chat via n8n", "asks as the sender", SAGE, PRI)}
    {box(40, 370, 210, 90, "Admin upload", "file and groups", SAGE, PRI)}
    {box(330, 250, 240, 100, "Who is asking", "token or inbound key")}
    {box(650, 250, 250, 100, "Readable set", "only their groups", PRI, "#244a37", "#fff")}
    {box(980, 250, 220, 100, "Search", "words, spelling, glossary", "#fff")}
    {box(1260, 250, 200, 100, "Enough support?", "else refuse", "#fff")}
    {box(1260, 450, 200, 90, "Answer + source", "quote and page")}
    {box(980, 450, 220, 90, "Audit log", "question, outcome, source", "#fff")}
    {box(650, 450, 250, 90, "Admin gaps", "what could not be answered", SAGE, PRI)}
    {box(330, 450, 240, 90, "Reader", "PDF, Word, text")}
    {box(980, 60, 220, 90, "Local model (optional)", "quote must be in passage")}
    {box(650, 60, 250, 90, "Glossary", "company words")}
    {arrow(250, 175, 330, 285)}{arrow(250, 295, 330, 300)}{arrow(250, 415, 400, 450)}{arrow(570, 300, 650, 300)}{arrow(900, 300, 980, 300)}{arrow(1200, 300, 1260, 300)}
    {arrow(1090, 150, 1090, 250)}{arrow(1360, 350, 1360, 450)}{arrow(1260, 495, 1200, 495)}{arrow(980, 495, 900, 495)}{arrow(775, 150, 775, 250)}{arrow(450, 450, 700, 350)}
    <text x="40" y="610" font-size="17" fill="#66736b">Text a person may not read is never in the search they use. When the documents do not say, the answer is a refusal, not a guess.</text></svg>"""
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1500, "height": 640}, device_scale_factor=2)
        pg.set_content(f"<body style='margin:0'>{svg}</body>"); pg.screenshot(path=str(A / "10_architecture.png")); b.close()
    print("architecture done")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"shots": shots, "tour": tour, "n8nvideo": n8nvideo, "cover": cover, "arch": architecture}.get(cmd, lambda: print("use: shots|tour|n8nvideo|cover|arch"))()
