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
        "END:VCARD",
    ]) + "\r\n"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="My eCard">
<meta name="theme-color" content="#0b3d6e">
<link rel="apple-touch-icon" href="../icon.png"><link rel="icon" href="../icon.png">
<link rel="manifest" href="manifest.webmanifest">
<title>{name} - eCard</title>
<style>body{{margin:0;font-family:system-ui,sans-serif;background:#0b3d6e;color:#222;display:flex;min-height:100vh;align-items:center;justify-content:center}}
.c{{background:#fff;border-radius:16px;padding:24px;max-width:380px;width:88%;text-align:center}}
img{{width:100%;max-width:320px;image-rendering:pixelated}}h1{{margin:.2em 0;font-size:1.4em}}p{{margin:.3em 0}}.t{{color:#0b3d6e;font-weight:600}}
.h{{font-size:.8em;color:#666;margin-top:12px}}</style></head>
<body><div class="c"><img src="qr.png?v={ver}" alt="QR code with contact details of {name}">
<h1>{name}</h1><p class="t">{post}</p><p>{org}</p>
<p>{phone}<br>{email}</p><p style="font-size:.85em">{address}</p>
<p class="h">Scan with phone camera to add contact</p></div></body></html>
"""

MANIFEST = {"name": "My eCard", "short_name": "eCard", "start_url": "./", "scope": "./",
            "display": "standalone", "background_color": "#0b3d6e", "theme_color": "#0b3d6e",
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
            name=e["first_name"] + " " + e["last_name"], ver=hashlib.sha1(card.encode()).hexdigest()[:8], **e),
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
