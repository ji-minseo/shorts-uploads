"""인간 사용설명서 — 릴스/쇼츠 (1080x1920, 약 25초) 생성기
usage: python3 reels.py episodes/epNN.json   (먼저 render.py로 out/epNN/slideXX.jpg 가 있어야 함)
episode JSON 의 "reels": [scene, ...]
  scene 종류
   {"slide": 3, "top": "위쪽 큰 글씨", "dur": 3.0, "zoom": [1.0, 1.15], "focus": [0.5, 0.6], "shake": true, "sfx": "thump"}
   {"card": "카드 큰 글씨", "sub": "작은 글씨(선택)", "doodle": "brain_folder" | [요소...], "dur": 3.5}
   {"end": true, "dur": 3.0}   # 마지막 팔로우 카드
"""
import json, math, sys, wave, pathlib, subprocess, random
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
import render as R

RW, RH, FPS = 1080, 1920, 30
WIN_Y, WIN_H = 400, 1350          # 슬라이드 창 위치
HANDLE = "@kuru.observes"


def frame_svg(body, seed=1):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{RW}" height="{RH}" viewBox="0 0 {RW} {RH}">
<defs><filter id="wobble" x="-5%" y="-5%" width="110%" height="110%">
<feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="{seed}"/>
<feDisplacementMap in="SourceGraphic" scale="7" xChannelSelector="R" yChannelSelector="G"/></filter></defs>
<rect width="{RW}" height="{RH}" fill="{R.PAPER}"/><g filter="url(#wobble)">{body}</g></svg>"""


def base_for_slide(sc, i):
    b = R.text(540, 150, sc.get("top", ""), R.fit(sc.get("top", " "), 72, 960), lh=1.22)
    b += R.text(540, 1840, HANDLE, 40, 700, fill="#9a8f80")
    return frame_svg(b, i)


def card_svg(sc, i, ep):
    b = R.wrect(60, 120, 960, 1640, "#fffdf7", 7)
    if sc.get("label"):
        b += R.shape(R.wpath(R.rect_pts(90, 80, 300, 76)), "#ff9f6e", 5)
        b += R.text(240, 133, sc["label"], 42)
    b += R.text(540, 380, sc["card"], R.fit(sc["card"], 84, 860), lh=1.3)
    if sc.get("sub"):
        b += R.text(540, 760, sc["sub"], R.fit(sc["sub"], 46, 860), 400, fill="#6b6157", lh=1.35)
    d = sc.get("doodle")
    if isinstance(d, str):
        b += f'<g transform="translate(540,1230) scale(1.15) translate(-540,-890)">{R.doodle(d, 540, 890)}</g>'
    elif d:
        b += f'<g transform="translate(540,1230) scale(1.15) translate(-540,-890)">{R.render_elements(d)}</g>'
    b += R.text(540, 1840, HANDLE, 40, 700, fill="#9a8f80")
    return frame_svg(b, i)


def end_svg(ep, i):
    b = R.text(540, 330, "자세한 인간 사용설명서는\n게시물에서 →", 76, lh=1.3)
    b += R.alien(540, 1330, 1.35, "love", "clipboard")
    b += R.shape(R.wpath(R.rect_pts(170, 1430, 740, 150)), R.YELLOW, 6)
    b += R.text(540, 1525, HANDLE, 64)
    b += R.text(540, 1700, "팔로우하고 같이 인간 관찰하기", 46, 400, fill="#6b6157")
    return frame_svg(b, i)


def html(svg):
    return f"<html><head><style>{R.FONT_CSS} body{{margin:0}}</style></head><body>{svg}</body></html>"


# ---------- 소리 ----------
SR = 44100


def pluck(freq, dur, amp=0.18):
    n = int(SR * dur)
    period = max(2, int(SR / freq))
    buf = np.random.uniform(-1, 1, period)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.996 * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out * amp


def make_audio(total, events, path):
    n = int(SR * total) + SR
    mix = np.zeros(n)
    # BGM: 엉뚱하고 통통 튀는 뚱땅뚱땅 (튜바 쿵-짝 + 마림바 멜로디 + 뾰잉), 116bpm
    bpm = 116; e8 = 60 / bpm / 2
    mtof = lambda m: 440.0 * 2 ** ((m - 69) / 12)

    def env_note(dur, tau):
        tt = np.arange(int(SR * dur)) / SR
        return tt, np.exp(-tt / tau) * np.minimum(1, tt / 0.004)

    def marimba(m, dur=0.35, amp=0.30):
        f = mtof(m); tt, e = env_note(dur, 0.11)
        return amp * e * (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 4 * f * tt) * np.exp(-tt / 0.02))

    def tuba(m, dur=0.22, amp=0.38):
        f = mtof(m); tt, e = env_note(dur, 0.12)
        w = sum(np.sin(2 * np.pi * f * k * tt) / k ** 1.3 for k in range(1, 6))
        return amp * e * w * (1 + 0.15 * np.sin(2 * np.pi * 6 * tt))

    def pah(ms, dur=0.10, amp=0.10):
        tt, e = env_note(dur, 0.04)
        return amp * e * sum((2 / np.pi) * np.arcsin(np.sin(2 * np.pi * mtof(m) * tt)) for m in ms)

    def boing(dur=0.35, amp=0.22):
        tt = np.arange(int(SR * dur)) / SR
        f = 220 * (1 + 2.5 * tt / dur) * (1 + 0.08 * np.sin(2 * np.pi * 18 * tt))
        return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.2)

    def put(w, at):
        s = int(at * SR); e = min(n, s + len(w))
        if s < n: mix[s:e] += w[: e - s]

    # 화음(근음, 5음, 짝 화음) / 멜로디(8분음표 8개, None=쉼, 'B'=뾰잉)
    prog = [(48, 55, [64, 67, 72]), (43, 50, [62, 65, 71]), (48, 55, [64, 67, 72]), (43, 50, [62, 65, 71]),
            (41, 48, [65, 69, 72]), (48, 55, [64, 67, 72]), (43, 50, [62, 65, 71]), (48, 55, [64, 67, 72])]
    mel = [[72, None, 76, None, 79, None, 76, 74], [71, None, 74, None, 77, None, 74, None],
           [72, 76, 79, 84, None, 79, None, None], [79, 78, 77, 76, 74, None, 'B', None],
           [77, None, 81, None, 84, None, 81, 79], [76, None, 79, 76, 72, None, None, None],
           [74, 75, 76, None, 79, None, 77, 74], [72, None, 'B', None, 84, None, None, None]]
    t, bar = 0.0, 0
    while t < total:
        root, fifth, chord = prog[bar % 8]
        for beat in range(4):
            bt = t + beat * 2 * e8
            if beat % 2 == 0:
                put(tuba(root if beat == 0 else fifth), bt)
            else:
                put(pah(chord), bt)
        for k, m in enumerate(mel[bar % 8]):
            at = t + k * e8 + (0.03 if k % 2 else 0)   # 살짝 스윙
            if m == 'B':
                put(boing(), at)
            elif m is not None:
                put(marimba(m), at)
        t += 8 * e8
        bar += 1
    # 효과음
    for at, kind in events:
        s = int(at * SR)
        if kind == "pop":
            d = int(0.09 * SR); tt = np.arange(d) / SR
            w = np.sin(2 * np.pi * (500 + 1800 * tt / 0.09) * tt) * np.exp(-tt * 40) * 0.35
        elif kind == "thump":
            d = int(0.35 * SR); tt = np.arange(d) / SR
            w = (np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 12) + np.random.uniform(-1, 1, d) * np.exp(-tt * 30) * 0.4) * 0.7
        elif kind == "ding":
            d = int(0.8 * SR); tt = np.arange(d) / SR
            w = (np.sin(2 * np.pi * 1318.5 * tt) + 0.5 * np.sin(2 * np.pi * 1975.5 * tt)) * np.exp(-tt * 5) * 0.22
        else:
            continue
        e = min(n, s + len(w)); mix[s:e] += w[: e - s]
    # 페이드아웃
    fo = int(1.2 * SR); end = int(total * SR)
    mix[end - fo:end] *= np.linspace(1, 0, fo)
    mix[end:] = 0
    mix = mix[:end]
    mix = np.clip(mix / max(1e-6, np.abs(mix).max()) * 0.85, -1, 1)
    with wave.open(str(path), "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((mix * 32767).astype(np.int16).tobytes())


# ---------- 영상 ----------
def ease(x):
    return 0.5 - 0.5 * math.cos(math.pi * min(1, max(0, x)))


def main(path):
    ep = json.loads(pathlib.Path(path).read_text())
    out = R.ROOT / "out" / f"ep{ep['ep']:02d}"
    tmp = out / "_reels"; tmp.mkdir(parents=True, exist_ok=True)
    scenes = ep["reels"]
    # 1) 정적 레이어 렌더
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        pg = b.new_page(viewport={"width": RW, "height": RH})
        for i, sc in enumerate(scenes):
            if "slide" in sc:
                svg = base_for_slide(sc, i + 1)
            elif sc.get("end"):
                svg = end_svg(ep, i + 1)
            else:
                svg = card_svg(sc, i + 1, ep)
            f = tmp / f"s{i}.html"; f.write_text(html(svg))
            pg.goto(f"file://{f}"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(250)
            pg.screenshot(path=str(tmp / f"s{i}.png")); f.unlink()
        b.close()
    # 2) 프레임 합성 → ffmpeg
    total = sum(sc["dur"] for sc in scenes)
    events, t = [], 0.0
    for sc in scenes:
        events.append((t, sc.get("sfx", "ding" if sc.get("end") else "pop")))
        t += sc["dur"]
    wav = tmp / "audio.wav"
    make_audio(total, events, wav)
    mp4 = out / f"reels_ep{ep['ep']:02d}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
                           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(mp4)],
                          stdin=subprocess.PIPE)
    rnd = random.Random(3)
    for i, sc in enumerate(scenes):
        base = Image.open(tmp / f"s{i}.png").convert("RGB")
        slide = Image.open(out / f"slide{sc['slide']:02d}.jpg").convert("RGB") if "slide" in sc else None
        nf = int(sc["dur"] * FPS)
        z0, z1 = sc.get("zoom", [1.0, 1.08])
        fx, fy = sc.get("focus", [0.5, 0.5])
        for k in range(nf):
            u = k / max(1, nf - 1)
            pop = 1.0 - 0.06 * (1 - ease(k / 6)) if k < 6 else 1.0   # 등장 시 살짝 튀어나옴
            if slide is not None:
                fr = base.copy()
                # 잘라내지 않고 슬라이드 전체를 통째로 확대/축소 (창 안에서 약 92~99%)
                z = z0 + (z1 - z0) * ease(u)
                scale = 0.925 * (1 + (z - 1) * 0.55) * pop
                ww, hh = int(R.W * scale), int(R.H * scale)
                img = slide.resize((ww, hh), Image.BILINEAR)
                ox, oy = (RW - ww) // 2, WIN_Y + (WIN_H - hh) // 2
                if sc.get("shake") and k < 14:
                    ox += int(rnd.uniform(-12, 12)); oy += int(rnd.uniform(-12, 12))
                fr.paste(img, (ox, oy))
            else:
                s = pop * (1 + 0.03 * ease(u))
                ww, hh = int(RW * s), int(RH * s)
                big = base.resize((ww, hh), Image.BILINEAR)
                fr = big.crop(((ww - RW) // 2, (hh - RH) // 2, (ww - RW) // 2 + RW, (hh - RH) // 2 + RH)) if s >= 1 else base
                if s < 1:
                    fr = Image.new("RGB", (RW, RH), R.PAPER); fr.paste(big, ((RW - ww) // 2, (RH - hh) // 2))
            ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    # 미리보기 시트
    for f in tmp.glob("s*.png"):
        f.unlink()
    wav.unlink()
    tmp.rmdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", f"fps=1/2,scale=270:480,tile=7x2", "-frames:v", "1",
                    str(out / "reels_sheet.jpg")])
    print("done", mp4, f"{total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])
