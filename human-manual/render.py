"""인간 사용설명서 — 손그림 인스타툰 렌더러
usage: python3 render.py episodes/ep01.json
"""
import json, math, random, sys, pathlib, html
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent
W, H = 1080, 1350
INK = "#2b2622"
PAPER = "#fbf5e9"
ALIEN = "#9fe0b8"
ALIEN_D = "#6cc595"
SKIN = "#ffd9bf"
BLANKET = "#b9d3f5"
PINK = "#f6b6c4"
YELLOW = "#ffe28a"

FONT_CSS = f"""
@font-face {{ font-family: 'Gaegu'; font-weight: 700;
  src: url('file://{ROOT}/node_modules/@fontsource/gaegu/files/gaegu-korean-700-normal.woff2'); }}
@font-face {{ font-family: 'Gaegu'; font-weight: 400;
  src: url('file://{ROOT}/node_modules/@fontsource/gaegu/files/gaegu-korean-400-normal.woff2'); }}
"""

rng = random.Random(7)


def esc(t):
    return html.escape(t)


# ---------- wobbly primitives ----------
def wob(v, a=2.5):
    return v + rng.uniform(-a, a)


def wpath(points, closed=True, a=2.0):
    """smooth jittered path through points (Catmull-Rom → bezier)"""
    pts = [(wob(x, a), wob(y, a)) for x, y in points]
    n = len(pts)
    if closed:
        pts_ext = [pts[-1]] + pts + pts[:2]
    else:
        pts_ext = [pts[0]] + pts + [pts[-1]]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    rngs = n if closed else n - 1
    for i in range(1, rngs + 1):
        p0, p1, p2, p3 = pts_ext[i - 1], pts_ext[i], pts_ext[i + 1], pts_ext[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    if closed:
        d += "Z"
    return d


def ellipse_pts(cx, cy, rx, ry, n=14):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rect_pts(x, y, w, h, n=4):
    pts = []
    for i in range(n):
        pts.append((x + w * i / n, y))
    for i in range(n):
        pts.append((x + w, y + h * i / n))
    for i in range(n):
        pts.append((x + w - w * i / n, y + h))
    for i in range(n):
        pts.append((x, y + h - h * i / n))
    return pts


def shape(d, fill="none", sw=5, stroke=INK, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'


def blob(cx, cy, rx, ry, fill, sw=5, n=14, a=2.0):
    return shape(wpath(ellipse_pts(cx, cy, rx, ry, n), True, a), fill, sw)


def wrect(x, y, w, h, fill="none", sw=5, a=2.5):
    return shape(wpath(rect_pts(x, y, w, h), True, a), fill, sw)


def line(pts, sw=5, stroke=INK, a=1.5):
    return shape(wpath(pts, False, a), "none", sw, stroke)


def fit(t, size, maxw):
    """가장 긴 줄이 maxw 픽셀을 넘지 않게 글자 크기 축소"""
    longest = max(sum(0.5 if c.isascii() else 0.92 for c in ln) for ln in t.split("\n"))
    return min(size, int(maxw / max(longest, 1)))


def text(x, y, t, size=44, weight=700, anchor="middle", fill=INK, lh=1.3, rot=0):
    lines = t.split("\n")
    out = [f'<text x="{x}" y="{y}" font-family="Gaegu" font-weight="{weight}" font-size="{size}" '
           f'fill="{fill}" text-anchor="{anchor}" transform="rotate({rot} {x} {y})">']
    for i, ln in enumerate(lines):
        out.append(f'<tspan x="{x}" dy="{0 if i == 0 else size * lh}">{esc(ln) if ln else " "}</tspan>')
    out.append("</text>")
    return "".join(out)


# ---------- characters ----------
def egg_pts(cx, cy, rx, ry, n=20):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        sy = math.sin(t)
        f = 1 - 0.14 * (-sy) if sy < 0 else 1.0
        pts.append((cx + rx * math.cos(t) * f, cy + ry * sy))
    return pts


def alien(x, y, s=1.0, mood="calm", hold="none", **_):
    """보호자 '쿠루' — 길쭉한 민트 외눈 외계인, 무심한 표정. (x,y)= 발 아래 중심"""
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    cy = -175
    # 길고 가는 더듬이 (살짝 처짐)
    g.append(line([(-28, -335), (-46, -392), (-72, -418)], 5))
    g.append(line([(28, -335), (48, -395), (74, -412)], 5))
    g.append(blob(-78, -420, 14, 14, YELLOW, 4, 8))
    g.append(blob(80, -414, 14, 14, YELLOW, 4, 8))
    # feet
    g.append(blob(-42, -8, 30, 13, ALIEN_D, 5, 10))
    g.append(blob(42, -8, 30, 13, ALIEN_D, 5, 10))
    # tall egg body
    g.append(shape(wpath(egg_pts(0, cy, 118, 168), True, 2.5), ALIEN, 6))
    g.append(blob(0, -95, 58, 48, "#c8f0d6", 0, 12))
    # eye — 작은 동공으로 멍하게
    ey = -240
    g.append(blob(0, ey, 58, 56, "white", 6, 14))
    if mood == "shock":
        g.append(blob(0, ey, 7, 7, INK, 0, 6, .5))
    elif mood == "proud":
        g.append(line([(-34, ey + 4), (0, ey - 16), (34, ey + 4)], 7))
    else:
        px = {"confused": 22, "reading": 0, "love": 0}.get(mood, 8)
        py = {"reading": 20}.get(mood, 2)
        g.append(blob(px, ey + py, 15, 15, INK, 0, 8, 1))
    # mouth — 일자
    my = -150
    if mood == "shock":
        g.append(blob(0, my, 8, 10, INK, 0, 8, 1))
    elif mood == "proud":
        g.append(shape(wpath([(-16, my), (6, my + 1), (18, my - 7)], False, 0.5), "none", 5))
    else:
        g.append(line([(-14, my), (14, my)], 5))
    if mood == "love":
        g.append(shape("M110,-350 C110,-370 135,-370 135,-352 C135,-370 160,-370 160,-350 C160,-332 135,-320 135,-312 C135,-320 110,-332 110,-350Z", "#ff7a9a", 4))
    # 가는 팔 + held item
    if hold == "clipboard":
        g.append(line([(-112, -170), (-150, -120), (-125, -88)], 6))
        g.append(wrect(-178, -170, 92, 115, "#e9c995", 5))
        g.append(wrect(-155, -184, 44, 22, "#bbb", 4))
        for i in range(3):
            g.append(line([(-165, -140 + i * 24), (-105, -140 + i * 24)], 3, "#8a7350"))
        g.append(line([(112, -170), (148, -125), (138, -92)], 6))
    elif hold == "book":
        g.append(wrect(-110, -165, 220, 90, "#ff9f6e", 6))
        g.append(line([(0, -165), (0, -75)], 4))
        g.append(text(-55, -118, "인간\n설명서", 22, 700, lh=1.0))
        g.append(line([(-114, -160), (-128, -110), (-106, -88)], 6))
        g.append(line([(114, -160), (128, -110), (106, -88)], 6))
    elif hold == "note":
        g.append(line([(112, -175), (165, -225)], 6))
        g.append(shape(wpath(rect_pts(150, -330, 110, 130)), "white", 5, extra='transform="rotate(12 205 -265)"'))
        g.append(text(205, -285, "내일\n할 일", 26, 700, rot=12, lh=1.1))
        g.append(line([(-112, -170), (-148, -118), (-125, -88)], 6))
    else:
        g.append(line([(-112, -170), (-152, -112), (-130, -80)], 6))
        g.append(line([(112, -170), (152, -115), (134, -80)], 6))
    if mood == "confused":
        g.append(text(170, -330, "?", 80, 700, rot=10))
    if mood == "shock":
        g.append(line([(-150, -330), (-185, -365)], 5))
        g.append(line([(-165, -290), (-210, -300)], 5))
    g.append("</g>")
    return "".join(g)


def bed(x, y, s=1.0, eyes="closed", kick=False, **_):
    """인간 1호 — 이불 속 인간. (x,y)=침대 바닥 중심"""
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    # bed frame
    g.append(wrect(-330, -110, 660, 110, "#d8a878", 6))
    g.append(line([(-320, 0), (-320, 40)], 7))
    g.append(line([(320, 0), (320, 40)], 7))
    # pillow
    g.append(blob(-215, -150, 105, 48, "white", 6, 12))
    # head
    hx, hy = -200, -205
    g.append(blob(hx, hy, 70, 66, SKIN, 6, 14))
    # hair scribble
    hair = [(hx - 70, hy - 10), (hx - 60, hy - 60), (hx - 20, hy - 78), (hx + 25, hy - 72), (hx + 62, hy - 45),
            (hx + 70, hy - 5), (hx + 45, hy - 35), (hx + 10, hy - 48), (hx - 30, hy - 40), (hx - 55, hy - 20)]
    g.append(shape(wpath(hair, True, 3), INK, 4))
    g.append(line([(hx - 5, hy - 75), (hx + 5, hy - 105), (hx + 25, hy - 98)], 5))
    ey = hy + 5
    if eyes == "closed":
        g.append(shape(wpath([(hx - 38, ey), (hx - 24, ey + 10), (hx - 10, ey)], False, 1), "none", 5))
        g.append(shape(wpath([(hx + 10, ey), (hx + 24, ey + 10), (hx + 38, ey)], False, 1), "none", 5))
    elif eyes == "sleepy":
        g.append(line([(hx - 38, ey + 4), (hx - 10, ey + 4)], 5))
        g.append(line([(hx + 10, ey + 4), (hx + 38, ey + 4)], 5))
        g.append(shape(wpath([(hx - 12, hy + 32), (hx, hy + 40), (hx + 12, hy + 32)], False, 1), "none", 4))
    elif eyes == "wide":
        g.append(blob(hx - 24, ey, 15, 15, "white", 4, 8))
        g.append(blob(hx + 24, ey, 15, 15, "white", 4, 8))
        g.append(blob(hx - 24, ey + 2, 5, 5, INK, 0, 6, 0.5))
        g.append(blob(hx + 24, ey + 2, 5, 5, INK, 0, 6, 0.5))
        g.append(line([(hx - 10, hy + 38), (hx + 10, hy + 38)], 4))
    elif eyes == "shock":
        g.append(line([(hx - 38, ey - 10), (hx - 14, ey + 2), (hx - 38, ey + 12)], 5))
        g.append(line([(hx + 38, ey - 10), (hx + 14, ey + 2), (hx + 38, ey + 12)], 5))
        g.append(blob(hx, hy + 40, 14, 12, "#5a2e2e", 4, 8))
        g.append(blob(hx + 60, hy - 30, 9, 16, "#8fd0ff", 3, 8))
    if eyes != "shock":
        g.append(blob(hx - 44, hy + 25, 13, 7, "#ffaaa0", 0, 8))
        g.append(blob(hx + 44, hy + 25, 13, 7, "#ffaaa0", 0, 8))
    # blanket
    if kick:
        # 이불이 위로 날아감
        g.append(shape(wpath([(-60, -430), (60, -490), (220, -470), (330, -420), (300, -360), (170, -385), (20, -370), (-80, -380)], True, 4), BLANKET, 6, extra='transform="rotate(-8 130 -420)"'))
        for px, py in [(20, -430), (120, -440), (220, -420)]:
            g.append(blob(px, py, 7, 7, "white", 0, 6, 1))
        for i in range(4):
            g.append(line([(-60 + i * 110, -320), (-40 + i * 110, -355)], 5))
        g.append(text(250, -520, "펄럭!", 46, rot=12))
        PJ = "#c9b6e6"

        def limb(pts, w=30):
            d = wpath(pts, False, 1.5)
            return (shape(d, "none", w + 11, INK) + shape(d, "none", w, PJ))

        # 뒤쪽 다리 (무릎 굽혀서 허공 발차기)
        g.append(limb([(40, -150), (150, -225), (245, -195)]))
        g.append(blob(262, -192, 26, 17, SKIN, 5, 10))
        # 몸통
        g.append(shape(wpath([(-150, -125), (-160, -170), (-110, -205), (0, -210), (60, -185), (70, -140), (20, -118), (-90, -115)], True, 2), PJ, 6))
        for sx in (-100, -45, 10):
            g.append(line([(sx, -200), (sx + 4, -122)], 4, "#8f78b8"))
        # 앞쪽 다리 (높이 차올림)
        g.append(limb([(30, -170), (105, -270), (200, -345)]))
        g.append(blob(215, -358, 30, 19, SKIN, 5, 10))
        # 팔: 주먹 번쩍
        g.append(limb([(-115, -190), (-95, -255), (-60, -290)], 24))
        g.append(blob(-52, -300, 18, 16, SKIN, 5, 8))
        # 동작선 (곡선)
        for (cx, cy, rr) in [(215, -358, 55), (262, -192, 45)]:
            g.append(shape(f"M{cx-rr},{cy-rr*0.3} Q{cx},{cy-rr*1.3} {cx+rr},{cy-rr*0.3}", "none", 4))
        g.append(line([(-95, -320), (-110, -345)], 4)); g.append(line([(-65, -330), (-62, -358)], 4))
    else:
        g.append(shape(wpath([(-140, -120), (-120, -205), (0, -225), (150, -215), (300, -190), (310, -120)], True, 4), BLANKET, 6))
    # blanket dots
    for px, py in [(-40, -170), (60, -180), (160, -165), (240, -150), (20, -140), (120, -135)]:
        if not kick:
            g.append(blob(px, py, 7, 7, "white", 0, 6, 1))
    g.append("</g>")
    return "".join(g)


def bubble(x, y, w, text_, tail=None, kind="speech", size=44, **_):
    lines = text_.split("\n")
    h = len(lines) * size * 1.3 + 60
    fill = "white" if kind == "speech" else "#fff3c4"
    g = []
    if tail:
        tx, ty = tail
        g.append(shape(wpath([(x - 30, y + h / 2 - 10), (tx, ty), (x + 30, y + h / 2 - 10)], False, 2), fill, 5))
    if kind == "narr":
        g.append(wrect(x - w / 2, y - h / 2, w, h, fill, 5))
    else:
        g.append(blob(x, y, w / 2 + 20, h / 2 + 18, fill, 5, 18, 3))
    if tail:  # cover tail join
        tx, ty = tail
        g.append(shape(wpath([(x - 22, y + h / 2 - 22), (x + 22, y + h / 2 - 22), (x, y + h / 2 + 4)], True, 0.5), fill, 0))
    g.append(text(x, y - h / 2 + 30 + size * 0.8, text_, size))
    return "".join(g)


def shout(x, y, text_, **_):
    g = []
    pts = []
    for i in range(22):
        r = 230 if i % 2 == 0 else 165
        a = 2 * math.pi * i / 22
        pts.append((x + r * math.cos(a) * 1.25, y + r * math.sin(a) * 0.62))
    g.append(shape(wpath(pts, True, 4).replace("C", "L") if False else "M" + " L".join(f"{wob(px,4):.1f},{wob(py,4):.1f}" for px, py in pts) + "Z", YELLOW, 6))
    g.append(text(x, y + 26, text_, 82, rot=-4))
    return "".join(g)


def zzz(x, y, **_):
    return text(x, y, "z", 50, rot=-10) + text(x + 45, y - 50, "z", 64, rot=-10) + text(x + 100, y - 115, "Z", 84, rot=-10)


def brain(cx, cy, r=120, face="calm"):
    pts = []
    n = 11
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append((cx + r * 1.2 * math.cos(a), cy + r * 0.9 * math.sin(a)))
    # bumpy outline using arcs
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, n + 1):
        p = pts[i % n]
        d += f" A{r*0.34:.1f},{r*0.34:.1f} 0 0 1 {wob(p[0],3):.1f},{wob(p[1],3):.1f}"
    g = [shape(d + "Z", PINK, 6)]
    g.append(line([(cx, cy - r * 0.8), (cx - 12, cy - r * 0.3), (cx + 10, cy + r * 0.1), (cx - 5, cy + r * 0.5)], 4))
    g.append(line([(cx - r * 0.8, cy - 20), (cx - r * 0.45, cy - 40), (cx - r * 0.3, cy - 5)], 4))
    g.append(line([(cx + r * 0.85, cy + 10), (cx + r * 0.5, cy - 20), (cx + r * 0.35, cy + 15)], 4))
    ey = cy + r * 0.25
    if face == "sleepy":
        g.append(line([(cx - 50, ey), (cx - 22, ey)], 5)); g.append(line([(cx + 22, ey), (cx + 50, ey)], 5))
    elif face == "busy":
        g.append(blob(cx - 36, ey, 10, 10, INK, 0, 6, 1)); g.append(blob(cx + 36, ey, 10, 10, INK, 0, 6, 1))
        g.append(shape(wpath([(cx - 15, ey + 30), (cx, ey + 42), (cx + 15, ey + 30)], False, 1), "none", 4))
    elif face == "evil":
        g.append(line([(cx - 55, ey - 14), (cx - 22, ey)], 5)); g.append(line([(cx + 55, ey - 14), (cx + 22, ey)], 5))
        g.append(shape(wpath([(cx - 25, ey + 25), (cx, ey + 42), (cx + 25, ey + 25)], False, 1), "none", 5))
    else:
        g.append(blob(cx - 36, ey, 16, 16, "white", 4, 8)); g.append(blob(cx + 36, ey, 16, 16, "white", 4, 8))
        g.append(blob(cx - 36, ey, 6, 6, INK, 0, 6, .5)); g.append(blob(cx + 36, ey, 6, 6, INK, 0, 6, .5))
    return "".join(g)


def doodle(kind, x, y):
    g = []
    if kind == "brain_daynight":
        g.append(text(x - 230, y - 120, "낮", 46)); g.append(text(x + 230, y - 120, "밤", 46))
        g.append(brain(x - 230, y, 95, "busy"))
        g.append(brain(x + 230, y, 95, "calm"))
        for i, w in enumerate(["일", "폰", "카톡"]):
            g.append(wrect(x - 360 + i * 90, y + 105, 75, 50, "white", 4)); g.append(text(x - 322 + i * 90, y + 142, w, 30))
        g.append(line([(x - 70, y), (x + 70, y)], 6)); g.append(line([(x + 45, y - 22), (x + 72, y), (x + 45, y + 22)], 6))
        g.append(blob(x + 350, y - 120, 70, 36, "#fff3c4", 4, 10)); g.append(text(x + 350, y - 110, "2014...", 30))
    elif kind == "brain_folder":
        g.append(brain(x - 180, y, 110, "evil"))
        fx, fy, fw, fh = x + 50, y - 90, 290, 200
        # 뒷판 + 큰 탭
        g.append(wrect(fx, fy - 10, fw, fh, "#f0c24f", 6, 1.5))
        g.append(wrect(fx, fy - 52, 120, 50, "#f0c24f", 6, 1.5))
        # 삐져나온 종이 2장
        g.append(shape(wpath(rect_pts(fx + 30, fy - 35, 210, 120), True, 1.5), "white", 5, extra=f'transform="rotate(-6 {fx+135} {fy+25})"'))
        g.append(shape(wpath(rect_pts(fx + 60, fy - 25, 200, 110), True, 1.5), "#fffbe8", 5, extra=f'transform="rotate(5 {fx+160} {fy+30})"'))
        g.append(text(fx + 160, fy + 15, "2014.03", 26, 400, fill="#8a7350", rot=5))
        # 앞판
        g.append(wrect(fx, fy + 40, fw, fh - 50, YELLOW, 6, 1.5))
        g.append(text(fx + fw / 2, fy + 100, "★ 중요 ★", 40))
        g.append(text(fx + fw / 2, fy + 145, "창피했던 일", 32))
        g.append(line([(x - 40, y - 20), (x + 45, y - 20)], 6)); g.append(line([(x + 22, y - 40), (x + 46, y - 20), (x + 22, y)], 6))
    elif kind == "brain_brake":
        bx, by = x - 270, y - 10
        g.append(brain(bx, by, 85, "sleepy"))
        # 뇌에서 뻗어나가는 선로
        g.append(line([(bx + 60, by + 72), (x + 400, by + 72)], 5))
        for tx in range(int(bx + 90), int(x + 400), 40):
            g.append(line([(tx, by + 64), (tx, by + 82)], 3))
        # 객차 (뒤쪽 → 앞쪽)
        cars = ["그때 왜", "그 말을", "다들 기억할까"]
        cx0 = bx + 110
        for i, t in enumerate(cars):
            cx = cx0 + i * 140
            g.append(wrect(cx, by - 5, 125, 62, "white", 5))
            g.append(text(cx + 62, by + 34, t, 19 if len(t) > 4 else 26))
            g.append(blob(cx + 28, by + 62, 12, 12, INK, 0, 8, 1)); g.append(blob(cx + 97, by + 62, 12, 12, INK, 0, 8, 1))
            g.append(line([(cx + 125, by + 30), (cx + 140, by + 30)], 4))
        # 기관차 (맨 앞)
        lx = cx0 + 3 * 140
        g.append(shape(wpath([(lx, by - 5), (lx + 90, by - 5), (lx + 125, by + 25), (lx + 125, by + 57), (lx, by + 57)], True, 1.5), "#ff9f6e", 5))
        g.append(wrect(lx + 15, by - 45, 30, 42, "#ff9f6e", 5))
        g.append(blob(lx + 30, by - 75, 22, 16, "white", 4, 8)); g.append(blob(lx + 58, by - 100, 28, 20, "white", 4, 8))
        g.append(blob(lx + 30, by + 62, 12, 12, INK, 0, 8, 1)); g.append(blob(lx + 95, by + 62, 12, 12, INK, 0, 8, 1))
        # 속도선
        for k in range(3):
            g.append(line([(lx + 140, by + 5 + k * 20), (lx + 175, by + 5 + k * 20)], 4))
        # 고장난 브레이크 레버 (뇌 아래, 따로 떨어져서)
        lvx, lvy = bx + 10, by + 215
        g.append(wrect(lvx - 55, lvy, 110, 30, "#bbb", 4))
        g.append(line([(lvx, lvy), (lvx - 8, lvy - 40)], 7))           # 부러진 밑동
        g.append(line([(lvx + 30, lvy - 30), (lvx + 75, lvy - 8)], 7))  # 떨어져 나간 손잡이
        g.append(blob(lvx + 80, lvy - 6, 11, 11, "#e2725b", 4, 8))
        g.append(text(lvx + 8, lvy - 50, "뚝", 28, rot=-10))
        g.append(wrect(lvx - 90, lvy + 45, 180, 48, "#ffc9c9", 4))
        g.append(text(lvx, lvy + 79, "브레이크 고장", 26))
    return "".join(g)



# ---------- 서 있는 인간 + 범용 요소 (자동화용) ----------
def face(hx, hy, eyes):
    g = []
    ey = hy + 5
    if eyes == "closed":
        g.append(shape(wpath([(hx - 38, ey), (hx - 24, ey + 10), (hx - 10, ey)], False, 1), "none", 5))
        g.append(shape(wpath([(hx + 10, ey), (hx + 24, ey + 10), (hx + 38, ey)], False, 1), "none", 5))
    elif eyes == "sleepy":
        g.append(line([(hx - 38, ey + 4), (hx - 10, ey + 4)], 5)); g.append(line([(hx + 10, ey + 4), (hx + 38, ey + 4)], 5))
    elif eyes == "happy":
        g.append(shape(wpath([(hx - 38, ey + 6), (hx - 24, ey - 6), (hx - 10, ey + 6)], False, 1), "none", 5))
        g.append(shape(wpath([(hx + 10, ey + 6), (hx + 24, ey - 6), (hx + 38, ey + 6)], False, 1), "none", 5))
        g.append(shape(f"M{hx-14},{hy+28} Q{hx},{hy+48} {hx+14},{hy+28}Z", "#7a3b3b", 4))
    elif eyes == "sad":
        g.append(blob(hx - 24, ey + 4, 6, 6, INK, 0, 6, .5)); g.append(blob(hx + 24, ey + 4, 6, 6, INK, 0, 6, .5))
        g.append(line([(hx - 38, ey - 14), (hx - 14, ey - 20)], 4)); g.append(line([(hx + 38, ey - 14), (hx + 14, ey - 20)], 4))
        g.append(shape(wpath([(hx - 12, hy + 40), (hx, hy + 32), (hx + 12, hy + 40)], False, 1), "none", 4))
        g.append(blob(hx + 30, ey + 25, 6, 11, "#8fd0ff", 3, 8))
    elif eyes == "shock":
        g.append(line([(hx - 38, ey - 10), (hx - 14, ey + 2), (hx - 38, ey + 12)], 5))
        g.append(line([(hx + 38, ey - 10), (hx + 14, ey + 2), (hx + 38, ey + 12)], 5))
        g.append(blob(hx, hy + 40, 14, 12, "#5a2e2e", 4, 8))
        g.append(blob(hx + 60, hy - 30, 9, 16, "#8fd0ff", 3, 8))
    elif eyes == "blank":  # 영혼 없음
        g.append(blob(hx - 24, ey, 13, 13, "white", 4, 8)); g.append(blob(hx + 24, ey, 13, 13, "white", 4, 8))
        g.append(line([(hx - 10, hy + 36), (hx + 10, hy + 36)], 4))
    else:  # wide / default
        g.append(blob(hx - 24, ey, 15, 15, "white", 4, 8)); g.append(blob(hx + 24, ey, 15, 15, "white", 4, 8))
        g.append(blob(hx - 24, ey + 2, 5, 5, INK, 0, 6, 0.5)); g.append(blob(hx + 24, ey + 2, 5, 5, INK, 0, 6, 0.5))
        g.append(line([(hx - 10, hy + 38), (hx + 10, hy + 38)], 4))
    if eyes not in ("shock", "blank"):
        g.append(blob(hx - 44, hy + 25, 13, 7, "#ffaaa0", 0, 8)); g.append(blob(hx + 44, hy + 25, 13, 7, "#ffaaa0", 0, 8))
    return "".join(g)


def head(hx, hy, eyes):
    g = [blob(hx, hy, 70, 66, SKIN, 6, 14)]
    hair = [(hx - 70, hy - 10), (hx - 60, hy - 60), (hx - 20, hy - 78), (hx + 25, hy - 72), (hx + 62, hy - 45),
            (hx + 70, hy - 5), (hx + 45, hy - 35), (hx + 10, hy - 48), (hx - 30, hy - 40), (hx - 55, hy - 20)]
    g.append(shape(wpath(hair, True, 3), INK, 4))
    g.append(line([(hx - 5, hy - 75), (hx + 5, hy - 105), (hx + 25, hy - 98)], 5))
    g.append(face(hx, hy, eyes))
    return "".join(g)


def _limb(pts, w=26, col="#c9b6e6"):
    d = wpath(pts, False, 1.5)
    return shape(d, "none", w + 11, INK) + shape(d, "none", w, col)


def icon(name, x, y, s=1.0, **_):
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    if name == "phone":
        g.append(wrect(-35, -60, 70, 120, "#555", 5)); g.append(wrect(-25, -45, 50, 80, "#bfe3ff", 3))
    elif name == "bag":
        g.append(wrect(-50, -40, 100, 90, "#ffb3c7", 5)); g.append(shape("M-25,-40 C-25,-85 25,-85 25,-40", "none", 6))
    elif name == "box":  # 택배상자
        g.append(wrect(-60, -45, 120, 90, "#d8a878", 5)); g.append(line([(-60, -15), (60, -15)], 4)); g.append(line([(0, -45), (0, -15)], 4))
    elif name == "coin":
        g.append(blob(0, 0, 45, 45, "#ffd45c", 5, 12)); g.append(text(0, 15, "₩", 44))
    elif name == "money":
        g.append(wrect(-70, -35, 140, 70, "#b8e6b0", 5)); g.append(blob(0, 0, 20, 20, "none", 4, 8)); g.append(text(0, 10, "₩", 28))
    elif name == "heart":
        g.append(shape("M0,25 C-60,-10 -40,-55 0,-28 C40,-55 60,-10 0,25Z", "#ff7a9a", 5))
    elif name == "clock":
        g.append(blob(0, 0, 50, 50, "white", 5, 12)); g.append(line([(0, 0), (0, -32)], 5)); g.append(line([(0, 0), (22, 10)], 5))
    elif name == "cloud":
        for cx, cy, r_ in [(-35, 5, 32), (0, -15, 40), (38, 5, 30)]:
            g.append(blob(cx, cy, r_, r_ * 0.85, "#d9dde3", 5, 10))
    elif name == "rain":
        for cx, cy, r_ in [(-35, 5, 32), (0, -15, 40), (38, 5, 30)]:
            g.append(blob(cx, cy, r_, r_ * 0.85, "#9aa3b0", 5, 10))
        for dx in (-30, 0, 30):
            g.append(line([(dx, 45), (dx - 8, 70)], 4, "#5b9bd5"))
    elif name == "lightning":
        g.append(shape("M10,-60 L-30,5 L0,5 L-15,60 L35,-10 L5,-10 Z", YELLOW, 5))
    elif name == "star":
        pts = [(math.cos(-math.pi / 2 + i * math.pi / 5) * (45 if i % 2 == 0 else 20), math.sin(-math.pi / 2 + i * math.pi / 5) * (45 if i % 2 == 0 else 20)) for i in range(10)]
        g.append(shape("M" + " L".join(f"{wob(px,2):.1f},{wob(py,2):.1f}" for px, py in pts) + "Z", YELLOW, 5))
    elif name == "cup":
        g.append(wrect(-35, -35, 70, 75, "white", 5)); g.append(shape("M35,-20 C65,-20 65,20 35,20", "none", 5))
        g.append(line([(-12, -50), (-8, -70)], 3)); g.append(line([(10, -50), (14, -72)], 3))
    elif name == "battery":
        lvl = 0.2
        g.append(wrect(-60, -30, 120, 60, "white", 5)); g.append(wrect(60, -12, 12, 24, INK, 3))
        g.append(wrect(-52, -22, 104 * lvl, 44, "#ff7a7a", 0))
    elif name == "dopamine":
        g.append(blob(0, 0, 40, 40, "#ffd6f0", 5, 10)); g.append(text(0, 12, "D", 36))
        for a in range(0, 360, 60):
            ra = math.radians(a); g.append(line([(55 * math.cos(ra), 55 * math.sin(ra)), (75 * math.cos(ra), 75 * math.sin(ra))], 4))
    elif name == "pillow":
        g.append(blob(0, 0, 80, 38, "white", 5, 12))
    elif name == "calendar":
        g.append(wrect(-55, -50, 110, 100, "white", 5)); g.append(wrect(-55, -50, 110, 28, "#ff9f6e", 5))
        for i in range(3):
            for j in range(3):
                g.append(blob(-30 + j * 30, -5 + i * 22, 5, 5, INK, 0, 6, .5))
    g.append("</g>")
    return "".join(g)


def human(x, y, s=1.0, pose="stand", eyes="wide", hold="none", **_):
    """서 있는 인간 1호 (줄무늬 파자마). (x,y)=발 아래 중심. pose: stand|cheer|slump|walk|sit"""
    PJ = "#c9b6e6"
    g = [f'<g transform="translate({x},{y}) scale({s})">']
    sit = pose == "sit"
    hip_y = -150 if sit else -210
    # legs
    if sit:
        g.append(line([(-80, hip_y + 30), (-85, -5)], 7)); g.append(line([(80, hip_y + 30), (85, -5)], 7))
        g.append(wrect(-100, hip_y + 5, 200, 32, "#d8a878", 5))
        g.append(_limb([(-30, hip_y + 15), (-34, -80), (-38, -15)], 28, PJ)); g.append(_limb([(30, hip_y + 15), (34, -80), (38, -15)], 28, PJ))
        g.append(blob(-45, -8, 26, 14, SKIN, 5, 8)); g.append(blob(45, -8, 26, 14, SKIN, 5, 8))
    elif pose == "walk":
        g.append(_limb([(-20, hip_y), (-45, -100), (-75, -15)], 28, PJ)); g.append(_limb([(20, hip_y), (40, -100), (70, -20)], 28, PJ))
        g.append(blob(-85, -10, 26, 14, SKIN, 5, 8)); g.append(blob(82, -12, 26, 14, SKIN, 5, 8))
    else:
        g.append(_limb([(-25, hip_y), (-30, -100), (-35, -15)], 28, PJ)); g.append(_limb([(25, hip_y), (30, -100), (35, -15)], 28, PJ))
        g.append(blob(-42, -8, 26, 14, SKIN, 5, 8)); g.append(blob(42, -8, 26, 14, SKIN, 5, 8))
    # torso
    ty = hip_y - 120
    lean = 18 if pose == "slump" else 0
    g.append(shape(wpath([(-62 + lean, ty), (62 + lean, ty), (70, hip_y + 10), (-70, hip_y + 10)], True, 2), PJ, 6))
    for sx in (-30, 0, 30):
        g.append(line([(sx + lean * 0.6, ty + 8), (sx, hip_y + 4)], 4, "#8f78b8"))
    # arms
    sh_y = ty + 20
    if pose == "cheer":
        g.append(_limb([(-55, sh_y), (-100, sh_y - 60), (-110, sh_y - 130)], 22, PJ)); g.append(_limb([(55, sh_y), (100, sh_y - 60), (110, sh_y - 130)], 22, PJ))
        g.append(blob(-112, sh_y - 145, 17, 15, SKIN, 5, 8)); g.append(blob(112, sh_y - 145, 17, 15, SKIN, 5, 8))
    elif pose == "slump":
        g.append(_limb([(-50, sh_y), (-75, sh_y + 70), (-80, sh_y + 140)], 22, PJ)); g.append(_limb([(60, sh_y), (85, sh_y + 70), (90, sh_y + 140)], 22, PJ))
        g.append(blob(-80, sh_y + 155, 16, 15, SKIN, 5, 8)); g.append(blob(90, sh_y + 155, 16, 15, SKIN, 5, 8))
    else:
        g.append(_limb([(-55, sh_y), (-85, sh_y + 60), (-90, sh_y + 120)], 22, PJ))
        if hold != "none":
            g.append(_limb([(55, sh_y), (95, sh_y + 50), (75, sh_y + 30)], 22, PJ))
        else:
            g.append(_limb([(55, sh_y), (85, sh_y + 60), (90, sh_y + 120)], 22, PJ))
        g.append(blob(-90, sh_y + 135, 16, 15, SKIN, 5, 8))
        g.append(blob(90 if hold == "none" else 72, sh_y + 135 if hold == "none" else sh_y + 25, 16, 15, SKIN, 5, 8))
    if hold != "none":
        g.append(icon(hold, 95, sh_y - 20, 0.75))
    # head
    hx, hy = lean * 1.6, ty - 62 + (12 if pose == "slump" else 0)
    g.append(head(hx, hy, eyes))
    if pose == "slump":
        for i in range(3):
            g.append(line([(-80 + i * 25, hy - 95), (-78 + i * 25, hy - 120)], 4))
    g.append("</g>")
    return "".join(g)


def arrow(x1, y1, x2, y2, **_):
    ang = math.atan2(y2 - y1, x2 - x1)
    a1 = (x2 - 28 * math.cos(ang - 0.5), y2 - 28 * math.sin(ang - 0.5))
    a2 = (x2 - 28 * math.cos(ang + 0.5), y2 - 28 * math.sin(ang + 0.5))
    return line([(x1, y1), ((x1 + x2) / 2, (y1 + y2) / 2 + 6), (x2, y2)], 6) + line([a1, (x2, y2), a2], 6)


def labelbox(x, y, w, h, text_, fill="white", size=32, **_):
    return wrect(x - w / 2, y - h / 2, w, h, fill, 5) + text(x, y - (len(text_.split("\n")) - 1) * size * 0.65 + size * 0.35, text_, size)


def mini_alien(x, y, s=0.42, mood="calm"):
    return alien(x, y, s, mood, "none")


ELEMS = {"alien": alien, "bed": bed, "bubble": lambda **k: bubble(k["x"], k["y"], k["w"], k["text"], k.get("tail"), k.get("kind", "speech"), k.get("size", 44)),
         "shout": lambda **k: shout(k["x"], k["y"], k["text"]), "zzz": lambda **k: zzz(k["x"], k["y"]),
         "human": human, "icon": lambda **k: icon(k["name"], k["x"], k["y"], k.get("s", 1.0)),
         "brain": lambda **k: brain(k["x"], k["y"], k.get("r", 100), k.get("face", "calm")),
         "arrow": lambda **k: arrow(k["x1"], k["y1"], k["x2"], k["y2"]),
         "box": lambda **k: labelbox(k["x"], k["y"], k["w"], k["h"], k.get("text", ""), k.get("fill", "white"), k.get("size", 32)),
         "label": lambda **k: text(k["x"], k["y"], k["text"], k.get("size", 36), k.get("weight", 700), rot=k.get("rot", 0))}


def render_elements(els):
    return "".join(ELEMS[e["type"]](**{k: v for k, v in e.items() if k != "type"}) for e in els)


# ---------- slide layouts ----------
def page_number(i, n):
    return text(W - 70, H - 30, f"{i}/{n}", 30, 400, anchor="end", fill="#9a8f80")


def footer_brand():
    return text(70, H - 30, "@인간사용설명서", 30, 700, anchor="start", fill="#9a8f80")


def slide_cover(ep, s):
    g = [wrect(60, 60, W - 120, H - 170, "none", 6)]
    g.append(wrect(150, 110, 780, 140, YELLOW, 6))
    g.append(text(540, 205, "인간 사용설명서", 86))
    g.append(text(540, 310, "외계인의 인간 입양 관찰기", 40, 400, fill="#6b6157"))
    g.append(text(540, 430, f"EP.{ep['ep']:02d}", 48, fill="#e2725b"))
    g.append(text(540, 520, ep["title"], fit(ep["title"], 62, 860), lh=1.3))
    g.append(render_elements(s["elements"]))
    return "".join(g)


def slide_comic(ep, s):
    g = [wrect(60, 170, W - 120, 1040, "white", 7)]
    lw = sum(20 if c.isascii() else 38 for c in s["label"]) + 50
    g.append(shape(wpath(rect_pts(70, 70, lw, 70)), YELLOW, 5, extra=f'transform="rotate(-1.5 {70+lw/2} 105)"'))
    g.append(text(90, 122, s["label"], 38, anchor="start", rot=-1.5))
    g.append(f'<g clip-path="url(#panel)">{render_elements(s["elements"])}</g>')
    if s.get("caption"):
        g.append(text(540, 1275, s["caption"], 40, 400, fill="#6b6157"))
    return "".join(g)


def grid_bg():
    g = []
    for yy in range(200, H - 100, 54):
        g.append(f'<line x1="90" y1="{yy}" x2="{W-90}" y2="{yy}" stroke="#e8dcc6" stroke-width="2"/>')
    return "".join(g)


def slide_manual(ep, s):
    g = [wrect(60, 60, W - 120, H - 170, "#fffdf7", 6)]
    g.append(grid_bg())
    g.append(wrect(60, 60, 330, 80, "#ff9f6e", 5))
    g.append(text(225, 115, f"설명서 p.{s['page']}", 42))
    g.append(text(540, 240, s["heading"], fit(s["heading"], 54, 880)))
    g.append(line([(150, 270), (930, 275)], 8, "#ffcf5a"))
    g.append(text(120, 360, s["body"], fit(s["body"], 40, 840), 400, anchor="start", lh=1.45))
    g.append(doodle(s["doodle"], 540, 890) if isinstance(s["doodle"], str) else render_elements(s["doodle"]))
    g.append(mini_alien(905, 1165, 0.42, "calm"))
    g.append(bubble(660, 1110, 300, s["note"], tail=[820, 1100], size=32))
    return "".join(g)


def slide_solution(ep, s):
    g = [wrect(60, 60, W - 120, H - 170, "#f0fbf4", 6)]
    g.append(wrect(250, 110, 580, 110, "white", 6))
    g.append(text(540, 185, "Rx " + s["heading"], 56, fill="#2f8f5b"))
    g.append(text(540, 330, s["body"], fit(s["body"], 44, 860), 400, lh=1.45))
    g.append(render_elements(s["elements"]))
    return "".join(g)


def slide_ending(ep, s):
    g = [wrect(60, 60, W - 120, H - 170, "none", 6)]
    g.append(shape(wpath(rect_pts(150, 120, 780, 300)), "white", 6, extra='transform="rotate(1 540 270)"'))
    g.append(text(540, 205, s["log"], 50, lh=1.35))
    g.append(render_elements(s["elements"]))
    g.append(wrect(140, 960, 800, 200, YELLOW, 6))
    g.append(text(540, 1015, "다음 관찰 →", 36, 400, fill="#6b6157"))
    g.append(text(540, 1070, ep["next"], 42, lh=1.25))
    return "".join(g)


LAYOUTS = {"cover": slide_cover, "comic": slide_comic, "manual": slide_manual, "solution": slide_solution, "ending": slide_ending}


def build_svg(ep, s, i, n):
    body = LAYOUTS[s["type"]](ep, s)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <filter id="wobble" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="{i*3+1}" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="5"/>
    <feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.45  0 0 0 0 0.35  0 0 0 0.07 0"/></filter>
  <clipPath id="panel"><rect x="62" y="172" width="{W-124}" height="1036"/></clipPath>
</defs>
<rect width="{W}" height="{H}" fill="{PAPER}"/>
<rect width="{W}" height="{H}" filter="url(#grain)"/>
<g filter="url(#wobble)">{body}{footer_brand()}{page_number(i, n)}</g>
</svg>"""


def main(path):
    ep = json.loads(pathlib.Path(path).read_text())
    out = ROOT / "out" / f"ep{ep['ep']:02d}"
    out.mkdir(parents=True, exist_ok=True)
    n = len(ep["slides"])
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, s in enumerate(ep["slides"], 1):
            svg = build_svg(ep, s, i, n)
            htmldoc = f"<html><head><style>{FONT_CSS} body{{margin:0}}</style></head><body>{svg}</body></html>"
            f = out / f"slide{i:02d}.html"
            f.write_text(htmldoc)
            pg.goto(f"file://{f}")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(300)
            png = out / f"slide{i:02d}.png"
            pg.screenshot(path=str(png))
            from PIL import Image
            Image.open(png).convert("RGB").save(out / f"slide{i:02d}.jpg", quality=90, optimize=True)
            png.unlink()
            f.unlink()
        b.close()
    from PIL import Image
    ims = [Image.open(out / f"slide{i:02d}.jpg").resize((360, 450)) for i in range(1, n + 1)]
    cols = 5
    sheet = Image.new("RGB", (360 * cols, 450 * ((n + cols - 1) // cols)), PAPER)
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * 360, (i // cols) * 450))
    sheet.save(out / "overview.jpg", quality=85)
    print("done", out)


if __name__ == "__main__":
    main(sys.argv[1])
