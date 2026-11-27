"""인스타 프로필 사진 (1080x1080, 원형 크롭 안전) — python3 profile.py"""
import pathlib
from playwright.sync_api import sync_playwright
from render import alien, blob, text, line, FONT_CSS, PAPER, YELLOW, ROOT

VARIANTS = {
    "a_yellow": ("#ffe28a", "calm", "none"),
    "b_cream": (PAPER, "calm", "clipboard"),
    "c_pink": ("#ffd3dc", "love", "none"),
}

def svg(bg, mood, hold):
    body = blob(540, 540, 500, 500, bg, 0, 24, 3)
    body += alien(540, 1075, 2.3, mood, hold)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">
<defs><filter id="wobble" x="-5%" y="-5%" width="110%" height="110%">
<feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="4"/>
<feDisplacementMap in="SourceGraphic" scale="7" xChannelSelector="R" yChannelSelector="G"/></filter></defs>
<rect width="1080" height="1080" fill="{bg}"/><g filter="url(#wobble)">{body}</g></svg>"""

out = ROOT / "out" / "profile"; out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
    pg = b.new_page(viewport={"width": 1080, "height": 1080})
    for name, (bg, mood, hold) in VARIANTS.items():
        f = out / f"{name}.html"
        f.write_text(f"<html><head><style>{FONT_CSS} body{{margin:0}}</style></head><body>{svg(bg, mood, hold)}</body></html>")
        pg.goto(f"file://{f}"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(out / f"{name}.png")); f.unlink()
    b.close()
print("done")
