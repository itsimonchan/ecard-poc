# eCard PoC (static, GitHub Pages)

The QR code on each staff page **contains the vCard text itself**.
Scanning it with the iPhone / Android camera shows the contact directly, ready to save.
No .vcf download, no server-side script.

## Files
```
index.html            site root (placeholder)
icon.png              home-screen icon
staff.json            simulated daily HRIS export (full list of active staff)
build.py              regenerates every staff folder from staff.json
simon/ , mary/        index.html + qr.png + manifest.webmanifest
```

## Daily update
1. Replace `staff.json` with the latest full HRIS export.
2. `pip install "qrcode[pil]"` (once), then `python build.py`
3. Upload / push all files. Folders of staff no longer in staff.json are deleted by build.py.

Note: because contact data is inside the QR image, the QR **changes** whenever
details change. That is fine because staff show it on screen, not on print.
Contacts already saved by others are not updated.

## Staff setup
Open `https://itsimonchan.github.io/ecard-poc/<id>/` on the phone, then
- iPhone (Safari): Share > Add to Home Screen
- Android (Chrome): menu > Add to Home screen / Install app
