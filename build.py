"""Build static eCard pages from staff.json.

Each staff folder gets:
  index.html            - page shown on the staff's phone (QR only, no download button)
  qr.png                - QR code that CONTAINS the vCard text (scan -> add contact directly)
  manifest.webmanifest  - lets Android "install" the page like an app

Run daily after the HRIS export:  python build.py
Requires: pip install "qrcode[pil]"
"""
import hashlib, html, json, re, shutil
from pathlib import Path
import qrcode
from qrcode.constants import ERROR_CORRECT_M

ROOT = Path(__file__).parent

def esc(v):  # vCard 3.0 text escaping
    return v.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

def vcard(s):
    return "\r\n".join([
        "BEGIN:VCARD", "VERSION:3.0",
        f"N:{esc(s['last_name'])};{esc(s['first_name'])};;;",
        f"FN:{esc(s['first_name'] + ' ' + s['last_name'])}",
        f"ORG:{esc(s['org'])}",
        f"TITLE:{esc(s['post'])}",
        f"TEL;TYPE=WORK,VOICE:{s['phone']}",
        f"EMAIL;TYPE=WORK:{s['email']}",
        f"ADR;TYPE=WORK:;;{esc(s['address'])};;;;",
        *( [f"URL:https://{s['website']}"] if s.get("website") else [] ),
        "END:VCARD",
    ]) + "\r\n"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="My eCard">
<meta name="theme-color" content="#FF6400">
<link rel="apple-touch-icon" href="../icon.png"><link rel="icon" href="../icon.png">
<link rel="manifest" href="manifest.webmanifest">
<title>{name} - eCard</title>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;background:#FF6400;color:#fff}}
body{{font-family:Roboto,"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;min-height:100vh;
display:flex;justify-content:center;padding:max(28px,env(safe-area-inset-top)) 28px max(28px,env(safe-area-inset-bottom))}}
.card{{width:100%;max-width:420px;display:flex;flex-direction:column}}
h1{{margin:0 0 10px;font-size:1.9rem;font-weight:700;letter-spacing:.02em}}
.post{{margin:0;font-size:1.05rem;line-height:1.35}}
.org{{margin:2px 0 0;font-size:.95rem;opacity:.95}}
ul{{list-style:none;margin:26px 0 0;padding:0}}
li{{display:flex;align-items:center;gap:12px;margin:0 0 10px;font-size:1.05rem}}
li svg{{flex:none;width:18px;height:18px}}
a{{color:#fff;text-decoration:none}}
.addr{{margin:20px 0 0;font-size:.9rem;line-height:1.4}}
.web{{margin:14px 0 0;font-size:.9rem}}
.qr{{margin:26px auto 0;background:#fff;border-radius:14px;padding:12px;width:100%;max-width:300px}}
.qr img{{display:block;width:100%;height:auto;image-rendering:pixelated}}
.hint{{margin:10px 0 0;text-align:center;font-size:.8rem;opacity:.9}}
</style></head>
<body><main class="card">
<h1>{name}</h1>
<p class="post">{post}</p>
<p class="org">{org}</p>
<ul>
<li><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg><a href="tel:{tel}">{phone}</a></li>
<li><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg><a href="mailto:{email}">{email}</a></li>
</ul>
<p class="addr">{address}</p>
<p class="web"><a href="https://{website}">{website}</a></p>
<div class="qr"><img src="qr.png?v={ver}" alt="QR code with contact details of {name}"></div>
<p class="hint">Scan with phone camera to add contact</p>
</main></body></html>
"""

MANIFEST = {"name": "My eCard", "short_name": "eCard", "start_url": "./", "scope": "./",
            "display": "standalone", "background_color": "#FF6400", "theme_color": "#FF6400",
            "icons": [{"src": "../icon.png", "sizes": "512x512", "type": "image/png"}]}

def main():
    staff = json.loads((ROOT / "staff.json").read_text(encoding="utf-8"))
    ids = set()
    for s in staff:
        sid = s["id"]
        assert re.fullmatch(r"[a-z0-9._-]+", sid), f"bad id {sid}"
        ids.add(sid)
        d = ROOT / sid
        d.mkdir(exist_ok=True)
        card = vcard(s)
        qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=10, border=4)
        qr.add_data(card.encode("utf-8"))  # raw vCard text inside QR
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(d / "qr.png")
        e = {k: html.escape(str(v)) for k, v in s.items()}
        (d / "index.html").write_text(PAGE.format(
            name=e["first_name"] + " " + e["last_name"], tel=e["phone"].replace(" ", ""), ver=hashlib.sha1(card.encode()).hexdigest()[:8], **e),
            encoding="utf-8")
        (d / "manifest.webmanifest").write_text(json.dumps(MANIFEST), encoding="utf-8")
        old = d / "contact.vcf"
        if old.exists():
            old.unlink()
        print(f"{sid}: QR version {qr.version}, {len(card.encode())} bytes")
    # remove folders of staff no longer in the full HRIS list (terminated staff)
    for d in ROOT.iterdir():
        if d.is_dir() and (d / "qr.png").exists() and d.name not in ids:
            shutil.rmtree(d)
            print(f"removed {d.name}")

if __name__ == "__main__":
    main()
