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
        b += R.render_elements(d)
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
    # BGM: 느긋한 4코드 플럭 (C - G - Am - F), 92bpm
    beat = 60 / 92
    chords = [[261.6, 329.6, 392.0], [246.9, 293.7, 392.0], [220.0, 261.6, 329.6], [220.0, 261.6, 349.2]]
    melody = [523.3, 587.3, 659.3, 587.3, 523.3, 440.0, 392.0, 440.0]
    cache = {}
    t, k = 0.0, 0
    while t < total:
        ch = chords[(k // 4) % 4]
        f = ch[k % 3] if k % 2 == 0 else ch[(k + 1) % 3]
        key = (round(f, 1), 0.1)
        if key not in cache:
            cache[key] = pluck(f, 0.9, 0.10)
        s = int(t * SR)
        seg = cache[key][: n - s]
        mix[s:s + len(seg)] += seg
        if k % 2 == 0:
            mf = melody[(k // 2) % len(melody)]
            key2 = (round(mf, 1), 0.2)
            if key2 not in cache:
                cache[key2] = pluck(mf, 0.7, 0.06)
            seg = cache[key2][: n - s]
            mix[s:s + len(seg)] += seg
        t += beat / 2
        k += 1
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
                z = z0 + (z1 - z0) * ease(u)
                cw, chh = R.W / z, R.H / z
                cx = min(max(fx * R.W, cw / 2), R.W - cw / 2); cy = min(max(fy * R.H, chh / 2), R.H - chh / 2)
                if sc.get("shake") and k < 14:
                    cx += rnd.uniform(-14, 14); cy += rnd.uniform(-14, 14)
                crop = slide.crop((int(cx - cw / 2), int(cy - chh / 2), int(cx + cw / 2), int(cy + chh / 2)))
                ww, hh = int(RW * pop), int(WIN_H * pop)
                crop = crop.resize((ww, hh), Image.BILINEAR)
                fr.paste(crop, ((RW - ww) // 2, WIN_Y + (WIN_H - hh) // 2))
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
