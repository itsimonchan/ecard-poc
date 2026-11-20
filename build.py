"""Build static eCard pages from staff.json.

Each staff folder gets:
  index.html            - e-name card page (card + QR code)
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
ORANGE = "#FF6400"   # Pantone 158C / RGB 255 100 0


def esc(v):  # vCard 3.0 text escaping
    return v.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def e164(display):  # "(852) 3129 1173" -> "+85231291173" for dialling / vCard
    digits = re.sub(r"\D", "", display)
    return "+" + digits


def vcard(s):
    lines = [
        "BEGIN:VCARD", "VERSION:3.0",
        f"N:{esc(s['last_name'])};{esc(s['first_name'])};;;",
        f"FN:{esc(s['first_name'] + ' ' + s['last_name'])}",
        f"ORG:{esc(s['org'])}",
        f"TITLE:{esc(s['post'])}",
        f"TEL;TYPE=WORK,VOICE:{e164(s['phone'])}",
    ]
    if s.get("fax"):
        lines.append(f"TEL;TYPE=WORK,FAX:{e164(s['fax'])}")
    lines += [
        f"EMAIL;TYPE=WORK:{s['email']}",
        f"ADR;TYPE=WORK:;;{esc(s['address'])};;;;Hong Kong",
    ]
    if s.get("website"):
        lines.append(f"URL:https://{s['website']}")
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


ICON_PHONE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>'
ICON_FAX = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9V3h12v6"/><rect x="2" y="9" width="20" height="9" rx="2"/><rect x="6" y="14" width="12" height="7"/></svg>'
ICON_MAIL = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg>'

PAGE = """<!doctype html><html lang="zh-Hant-HK"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="My eCard">
<meta name="theme-color" content="#3a3a3a">
<link rel="apple-touch-icon" href="../icon.png"><link rel="icon" href="../icon.png">
<link rel="manifest" href="manifest.webmanifest">
<title>{name_zh} {name} - eCard</title>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;background:#3a3a3a}}
body{{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;
padding:max(20px,env(safe-area-inset-top)) 14px max(20px,env(safe-area-inset-bottom));
font-family:Roboto,"Noto Sans TC","PingFang HK","PingFang TC","Microsoft JhengHei","Segoe UI",system-ui,sans-serif}}
.wrap{{width:100%;max-width:640px;container-type:inline-size}}
.card{{background:{orange};color:#fff;aspect-ratio:1.65/1;padding:9cqw 7.6cqw 6cqw;
display:flex;flex-direction:column;box-shadow:0 6px 24px rgba(0,0,0,.35)}}
.zh{{letter-spacing:.08em}}
h1{{margin:0;font-size:max(24px,6.4cqw);font-weight:700;line-height:1.1}}
.pz{{margin:3.2cqw 0 0;font-size:max(15px,3.9cqw);font-weight:500;line-height:1.3}}
.pe{{margin:.4cqw 0 0;font-size:max(14px,3.6cqw);font-weight:500;line-height:1.3}}
ul{{list-style:none;margin:auto 0 0;padding:6cqw 0 0}}
li{{display:flex;align-items:center;gap:2.6cqw;font-size:max(14px,3.7cqw);line-height:1.6}}
li svg{{flex:none;width:max(13px,3.2cqw);height:max(13px,3.2cqw);fill:none;stroke:#fff;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}}
a{{color:#fff;text-decoration:none}}
.az{{margin:5.4cqw 0 0;font-size:max(13px,3.1cqw);line-height:1.4}}
.ae{{margin:.4cqw 0 0;font-size:max(12px,2.95cqw);line-height:1.4}}
.web{{margin:3.6cqw 0 0;font-size:max(12px,2.95cqw)}}
.qrbox{{background:#fff;padding:10px;border-radius:10px;width:min(78vw,300px)}}
.qrbox img{{display:block;width:100%;height:auto;image-rendering:pixelated}}
.hint{{margin:-10px 0 0;color:#ddd;font-size:13px;font-family:inherit}}
</style></head>
<body>
<div class="wrap"><section class="card">
<h1 class="zh">{name_zh}</h1>
<p class="pz zh">{post_zh}</p>
<p class="pe">{post}</p>
<ul>
<li>{icon_phone}<a href="tel:{tel}">{phone}</a></li>
{fax_li}<li>{icon_mail}<a href="mailto:{email}">{email}</a></li>
</ul>
<p class="az zh">{address_zh}</p>
<p class="ae">{address}</p>
<p class="web"><a href="https://{website}">{website}</a></p>
</section></div>
<div class="qrbox"><img src="qr.png?v={ver}" alt="QR code with contact details of {name}"></div>
<p class="hint">掃描 QR code 加入聯絡人 · Scan to add contact</p>
</body></html>
"""

MANIFEST = {"name": "My eCard", "short_name": "eCard", "start_url": "./", "scope": "./",
            "display": "standalone", "background_color": "#3a3a3a", "theme_color": "#3a3a3a",
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
        e.setdefault("name_zh", "")
        e.setdefault("post_zh", "")
        e.setdefault("address_zh", "")
        fax_li = f'<li>{ICON_FAX}<span>{e["fax"]}</span></li>\n' if s.get("fax") else ""
        (d / "index.html").write_text(PAGE.format(
            name=e["first_name"] + " " + e["last_name"], orange=ORANGE,
            icon_phone=ICON_PHONE, icon_mail=ICON_MAIL, fax_li=fax_li,
            tel=e164(s["phone"]), ver=hashlib.sha1(card.encode()).hexdigest()[:8], **e),
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
