"""Render an animated vertical YouTube Short (1080x1920, 30fps) from a story JSON.

Features: neural English voice (Piper), animated gradient + light rays + particles,
scene-specific emoji animations (pop, count, shake, run, rain, zoom, subscribe),
camera shake, kinetic word-by-word captions, flash transitions, synthesized music
bed with beat, whoosh and pop sound effects.

Usage: python3 make_short.py story.json out.mp4
"""
import json, math, os, random, subprocess, sys, wave, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 44100
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
VOICE_MODEL = os.environ.get("SHORT_VOICE", os.path.join(HERE, "voices", "en-us-ryan-high.onnx"))
PALETTES = [((255, 94, 58), (255, 42, 104), (120, 20, 160)),
            ((58, 123, 213), (0, 210, 255), (20, 40, 120)),
            ((131, 58, 180), (253, 29, 29), (252, 176, 69)),
            ((17, 153, 142), (56, 239, 125), (10, 60, 90)),
            ((252, 70, 107), (63, 94, 251), (30, 20, 80))]
EMO_Y = 700          # vertical centre of the illustration area
CAP_Y = 1330         # vertical centre of captions

top_font = ImageFont.truetype(BOLD, 46)
_emoji_font = ImageFont.truetype(EMOJI, 109)
_cache = {}
_fonts = {}


def font(size):
    size = max(8, int(size))
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(BOLD, size)
    return _fonts[size]


def emoji(ch, size, flip=False, angle=0.0):
    key = (ch, int(size), flip, round(angle))
    if key in _cache:
        return _cache[key]
    base = _cache.get(ch)
    if base is None:
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=_emoji_font, embedded_color=True, anchor="mm")
        base = _cache[ch] = im.crop(im.getbbox() or (0, 0, 160, 160))
    s = max(2, int(size))
    im = base.resize((s, int(s * base.height / base.width)), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if angle:
        im = im.rotate(round(angle), expand=True, resample=Image.BICUBIC)
    if len(_cache) < 4000:
        _cache[key] = im
    return im


def paste_c(img, im, cx, cy):
    img.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2))) if \
        -im.width < cx < W + im.width and -im.height < cy < H + im.height else None


def ease_back(t):
    t = min(max(t, 0.0), 1.0); c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------- audio
def tts_all(texts, work):
    from piper import PiperVoice
    voice = PiperVoice.load(VOICE_MODEL)
    out = []
    for i, text in enumerate(texts):
        p = f"{work}/{i}.wav"
        with wave.open(p, "wb") as wf:
            voice.synthesize_wav(text, wf)
        with wave.open(p) as wf:
            sr = wf.getframerate()
            a = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
        n = int(len(a) * SR / sr)
        out.append(np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a))
    return out


def synth_music(total, rnd):
    n = int(total * SR); t = np.arange(n) / SR
    beat = 0.6
    prog = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (261.6, 329.6, 392.0), (196.0, 246.9, 293.7)]
    pad = np.zeros(n, np.float32)
    bar = beat * 4
    for k in range(int(total / bar) + 1):
        s, e = int(k * bar * SR), min(n, int((k + 1) * bar * SR))
        if s >= n: break
        tt = t[s:e] - k * bar
        env = np.minimum(1, tt / 0.3) * np.minimum(1, (bar - tt) / 0.3)
        for f in prog[k % 4]:
            pad[s:e] += (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.003 * tt)) * env * 0.12
    beats = np.zeros(n, np.float32)
    kick_t = np.arange(int(0.18 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-kick_t * 30)) * kick_t) * np.exp(-kick_t * 18)
    hat = np.random.default_rng(1).standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 80) * 0.15
    k = 0.0
    while k < total:
        i = int(k * SR); beats[i:i + len(kick)] += kick[: n - i] * 0.5
        j = int((k + beat / 2) * SR)
        if j < n: beats[j:j + len(hat)] += hat[: n - j]
        k += beat
    m = pad + beats
    fade = np.minimum(1, np.minimum(t / 1.0, (total - t) / 1.5))
    return m * fade * 0.22


def whoosh():
    d = 0.45; n = int(d * SR); x = np.random.default_rng(2).standard_normal(n)
    out = np.zeros(n); y = 0.0
    for i in range(n):          # sweeping one-pole lowpass
        a = 0.02 + 0.25 * math.sin(math.pi * i / n)
        y += a * (x[i] - y); out[i] = y
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return out * env * 0.9


def pop():
    n = int(0.09 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * (300 + 900 * np.exp(-tt * 40)) * tt) * np.exp(-tt * 35) * 0.35


def boom():
    n = int(0.35 * SR); tt = np.arange(n) / SR
    noise = np.random.default_rng(3).standard_normal(n) * np.exp(-tt * 14) * 0.25
    return (np.sin(2 * np.pi * (40 + 80 * np.exp(-tt * 20)) * tt) * np.exp(-tt * 9) * 0.7 + noise)


# ---------------------------------------------------------------- scene animations
def anim_pop(img, sc, lt, t, rnd_state):
    ems = sc["emoji"]
    for k, ch in enumerate(ems):
        p = ease_back((lt - 0.15 * k) / 0.45)
        if p <= 0.01: continue
        size = (430 if len(ems) == 1 else 330 if len(ems) == 2 else 250) * p
        cx = W / 2 + (k - (len(ems) - 1) / 2) * (360 if len(ems) == 2 else 290)
        cy = EMO_Y + 28 * math.sin(t * 2.6 + k * 1.3)
        paste_c(img, emoji(ch, size, angle=8 * math.sin(t * 2.2 + k)), cx, cy)


def anim_count(img, sc, lt, t, rs):
    # field of wheat along the bottom, a swarm of birds marching over it, and a counter
    for i in range(9):
        x = 60 + i * 120
        paste_c(img, emoji(sc.get("under", "🌾"), 130, angle=6 * math.sin(t * 3 + i)), x, EMO_Y + 260)
    n_b = 16
    for i in range(n_b):
        appear = ease_back((lt - i * 0.06) / 0.35)
        if appear <= 0.01: continue
        x = ((i * 157 + lt * (110 + 9 * (i % 5))) % (W + 200)) - 100
        y = EMO_Y + 175 + (i % 3) * 40 - 60 * abs(math.sin(t * 6 + i))
        paste_c(img, emoji(sc["emoji"][0], 120 * appear), x, y)
    val = int(sc["to"] * ease_out(lt / 1.6))
    txt = f"{val:,}"
    d = ImageDraw.Draw(img, "RGBA")
    s = 1 + 0.06 * math.sin(t * 8) if lt > 1.6 else 1
    d.text((W / 2, EMO_Y - 140), txt, font=font(210 * s), fill=(255, 230, 0), stroke_width=12,
           stroke_fill=(0, 0, 0), anchor="mm")
    d.text((W / 2, EMO_Y + 10), sc.get("label", ""), font=font(80), fill="white", stroke_width=8,
           stroke_fill=(0, 0, 0), anchor="mm")


def anim_shake(img, sc, lt, t, rs):
    ems = sc["emoji"]
    for k, ch in enumerate(ems):
        p = ease_back((lt - 0.2 * k) / 0.4)
        if p <= 0.01: continue
        cx = W / 2 + (k - (len(ems) - 1) / 2) * 380
        recoil = -25 * max(0, math.sin(t * 22)) if k == 1 and lt > 0.6 else 0
        paste_c(img, emoji(ch, 340 * p, flip=(k == 1)), cx + recoil, EMO_Y + 15 * math.sin(t * 3))
    # impact bursts
    for j in range(int(lt / 0.45) + 1):
        bt = lt - j * 0.45 - 0.6
        if 0 <= bt < 0.4:
            r = random.Random(j * 7 + 3)
            bx, by = r.uniform(150, W - 150), r.uniform(EMO_Y - 330, EMO_Y + 300)
            paste_c(img, emoji("💥", 120 + 260 * ease_out(bt / 0.25), angle=r.uniform(-30, 30)), bx, by)


def shake_offset(sc, lt):
    if sc.get("anim") != "shake" or lt < 0.6:
        return 0, 0
    ph = (lt - 0.6) % 0.45
    amp = 26 * math.exp(-ph * 12)
    return int(amp * math.sin(lt * 90)), int(amp * math.cos(lt * 73))


def anim_run(img, sc, lt, t, rs):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(14):  # speed lines
        r = random.Random(i)
        y = r.uniform(EMO_Y - 420, EMO_Y + 420)
        x = W - ((lt * 2600 + r.uniform(0, W * 2)) % (W * 2))
        d.line([(x, y), (x + r.uniform(120, 320), y)], fill=(255, 255, 255, 150), width=6)
    lanes = [(EMO_Y - 260, 1.0, 0.0), (EMO_Y, 1.25, 0.5), (EMO_Y + 260, 0.85, 0.25)]
    for k, (y, sp, off) in enumerate(lanes + [(a, b, c + 0.55) for a, b, c in lanes]):
        x = ((lt * 520 * sp + off * (W + 500)) % (W + 500)) - 250
        bob = -40 * abs(math.sin(t * 14 + k))
        paste_c(img, emoji(sc.get("trail", "💨"), 150), x - 190, y + 40)
        paste_c(img, emoji(sc["emoji"][0], 260, angle=-8), x, y + bob)


def anim_rain(img, sc, lt, t, rs):
    for i in range(16):
        r = random.Random(i * 13)
        x = r.uniform(40, W - 40) + 40 * math.sin(t * 1.5 + i)
        y = ((lt * r.uniform(250, 450) + r.uniform(0, H)) % (H + 200)) - 100
        paste_c(img, emoji(sc.get("drop", "🪶"), r.uniform(70, 130), angle=40 * math.sin(t * 2 + i)), x, y)
    ems = sc["emoji"]
    for k, ch in enumerate(ems):
        p = ease_back((lt - 0.2 * k) / 0.45)
        if p <= 0.01: continue
        cx = W / 2 + (k - (len(ems) - 1) / 2) * 360
        shrink = 1 - 0.25 * ease_out((lt - 1.2) / 1.5) if k == 1 else 1
        paste_c(img, emoji(ch, 330 * p * shrink, angle=6 * math.sin(t * 1.7 + k)), cx,
                EMO_Y + 20 * math.sin(t * 2 + k))


def anim_zoom(img, sc, lt, t, rs):
    p = ease_back(lt / 0.6)
    orbit = sc.get("orbit")
    if orbit:
        for k in range(5):
            a = t * 1.6 + k * 2 * math.pi / 5
            paste_c(img, emoji(orbit, 140, flip=math.cos(a) < 0), W / 2 + 380 * math.cos(a) * p,
                    EMO_Y + 220 * math.sin(a) * p)
    paste_c(img, emoji(sc["emoji"][0], 470 * p * (1 + 0.05 * math.sin(t * 5))), W / 2, EMO_Y)
    if len(sc["emoji"]) > 1:
        q = ease_back((lt - 0.5) / 0.4)
        if q > 0.01:
            paste_c(img, emoji(sc["emoji"][1], 180 * q, angle=-15), W / 2 + 10, EMO_Y - 290)


def anim_subscribe(img, sc, lt, t, rs):
    d = ImageDraw.Draw(img, "RGBA")
    p = ease_back(lt / 0.45)
    clicked = lt > 1.5
    bw, bh = 640 * p, 170 * p
    if bw > 10:
        col = (90, 90, 90) if clicked else (230, 33, 23)
        cy = EMO_Y + (10 * math.sin(t * 25) * math.exp(-(lt - 1.5) * 8) if clicked else 0)
        d.rounded_rectangle([W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2], int(40 * p), fill=col,
                            outline=(255, 255, 255), width=6)
        d.text((W / 2, cy), "SUBSCRIBED ✓" if clicked else "SUBSCRIBE", font=font(78 * p), fill="white",
               anchor="mm")
    # cursor moves in and clicks
    if lt > 0.5:
        m = ease_out((lt - 0.5) / 0.9)
        cx, cy = W - 120 + (W / 2 + 230 - (W - 120)) * m, EMO_Y + 560 + (150 - 560) * m
        press = 0.85 if 1.4 < lt < 1.6 else 1
        paste_c(img, emoji("👆", 190 * press), cx, cy)
    if clicked:
        q = ease_back((lt - 1.5) / 0.4)
        paste_c(img, emoji("🔔", 230 * q, angle=25 * math.sin(lt * 20) * math.exp(-(lt - 1.5) * 1.5)),
                W / 2 - 200, EMO_Y - 300)
        paste_c(img, emoji("👍", 230 * ease_back((lt - 1.7) / 0.4)), W / 2 + 200, EMO_Y - 300)


ANIMS = dict(pop=anim_pop, count=anim_count, shake=anim_shake, run=anim_run, rain=anim_rain,
             zoom=anim_zoom, subscribe=anim_subscribe)


# ---------------------------------------------------------------- background
def make_bg(t, pal):
    yy, xx = np.mgrid[0:H // 6, 0:W // 6].astype(np.float32)
    phase = (xx * 0.5 + yy) / (H // 6) + 0.15 * math.sin(t * 0.6)
    s = (np.sin(phase * math.pi + t * 0.5) + 1) / 2
    a, b, c = (np.array(p, np.float32) for p in pal)
    s3 = s[..., None]
    mix = np.where(s3 < 0.5, a + (b - a) * (s3 * 2), b + (c - b) * ((s3 - 0.5) * 2))
    return Image.fromarray(mix.astype(np.uint8)).resize((W, H), Image.BILINEAR).convert("RGBA")


def rays_layer(t, strength):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cx, cy, R = W / 2, EMO_Y, 1600
    for k in range(12):
        a0 = t * 0.35 + k * 2 * math.pi / 12
        a1 = a0 + math.pi / 18
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                   (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=(255, 255, 255, int(38 * strength)))
    return lay


def glow_layer():
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.ellipse([W / 2 - 380, EMO_Y - 380, W / 2 + 380, EMO_Y + 380], fill=(255, 255, 255, 70))
    return lay.filter(ImageFilter.GaussianBlur(90))


def vignette_layer():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    a = (np.clip(r - 0.55, 0, 1) * 330).clip(0, 170).astype(np.uint8)
    arr = np.zeros((H, W, 4), np.uint8); arr[..., 3] = a
    return Image.fromarray(arr, "RGBA")


# ---------------------------------------------------------------- main
def main(story_path, out_path):
    story = json.load(open(story_path))
    rnd = random.Random(story.get("title", story_path))
    pal = rnd.choice(PALETTES)
    work = os.path.splitext(out_path)[0] + "_work"; os.makedirs(work, exist_ok=True)

    voices = tts_all([sc["text"] for sc in story["scenes"]], work)
    scenes, t0 = [], 0.35
    for sc, v in zip(story["scenes"], voices):
        d = len(v) / SR
        extra = 1.6 if sc.get("anim") == "subscribe" else 0.3
        words = sc["text"].split()
        weights = [len(w) + (4 if w[-1] in ".,!?:" else 0) + 2 for w in words]
        tot, acc, wt = sum(weights), 0.0, []
        for w, g in zip(words, weights):
            wt.append((w, t0 + acc / tot * d, t0 + (acc + g) / tot * d)); acc += g
        scenes.append(dict(sc, start=t0 - (0.35 if not scenes else 0), vstart=t0, end=t0 + d + extra,
                           voice=v, words=wt))
        t0 += d + extra
    scenes[0]["start"] = 0.0
    total = t0 + 0.3

    # ---- audio mix
    n = int(total * SR)
    mix = synth_music(total, rnd)
    def add(sig, at, gain=1.0):
        i = int(at * SR)
        if i >= n: return
        mix[i:i + len(sig)] += sig[: n - i] * gain
    wh, pp, bm = whoosh(), pop(), boom()
    for k, s in enumerate(scenes):
        add(s["voice"], s["vstart"], 0.95)
        if k: add(wh, s["start"] - 0.15, 0.5)
        anim = s.get("anim", "pop")
        if anim in ("pop", "rain", "shake"):
            for j in range(len(s["emoji"])): add(pp, s["start"] + 0.15 * j + 0.1, 0.8)
        if anim == "shake":
            j = 0
            while s["start"] + 0.6 + j * 0.45 < s["end"]:
                add(bm, s["start"] + 0.6 + j * 0.45, 0.5); j += 1
        if anim == "zoom": add(bm, s["start"] + 0.05, 0.6)
        if anim == "subscribe": add(pp, s["start"] + 1.5, 1.0)
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    audio = f"{work}/mix.wav"
    with wave.open(audio, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((mix * 32767).astype(np.int16).tobytes())

    # ---- video
    vign, glow = vignette_layer(), glow_layer()
    parts = [dict(x=rnd.uniform(0, W), y=rnd.uniform(0, H), r=rnd.uniform(6, 34), v=rnd.uniform(20, 80),
                  ph=rnd.uniform(0, 6.28), a=rnd.randint(30, 85)) for _ in range(30)]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", "-movflags", "+faststart", out_path],
                          stdin=subprocess.PIPE)
    banner = story.get("banner", "CRAZY FACTS")
    for fi in range(int(total * FPS)):
        t = fi / FPS
        sc = next((s for s in scenes if s["start"] <= t < s["end"]), scenes[-1])
        lt = t - sc["start"]
        anim = sc.get("anim", "pop")
        img = make_bg(t, pal)
        img.alpha_composite(rays_layer(t, 1.6 if anim == "zoom" else 1.0))
        img.alpha_composite(glow)
        d = ImageDraw.Draw(img, "RGBA")
        for p in parts:
            y = (p["y"] - p["v"] * t) % (H + 100) - 50
            x = p["x"] + 30 * math.sin(t * 0.8 + p["ph"])
            d.ellipse([x - p["r"], y - p["r"], x + p["r"], y + p["r"]], fill=(255, 255, 255, p["a"]))
        ANIMS[anim](img, sc, lt, t, None)

        # kinetic captions: groups of up to 3 words, active word yellow + bigger
        d = ImageDraw.Draw(img, "RGBA")
        groups = [sc["words"][i:i + 3] for i in range(0, len(sc["words"]), 3)]
        g = groups[0]
        for gg in groups:
            if t >= gg[0][1]: g = gg
        p = ease_back((t - g[0][1]) / 0.2) if t >= g[0][1] else 1
        if not (anim == "subscribe" and t > sc["words"][-1][2] + 0.3):
            f = font(96 * (0.8 + 0.2 * p))
            lines, cur = [], []
            for w in g:
                if cur and d.textlength(" ".join(x[0] for x in cur + [w]), font=f) > W - 120:
                    lines.append(cur); cur = []
                cur.append(w)
            lines.append(cur)
            y = CAP_Y - (len(lines) - 1) * 62
            for ln in lines:
                widths = [d.textlength(w[0] + " ", font=f) for w in ln]
                x = (W - sum(widths) + d.textlength(" ", font=f)) / 2
                for (w, ws, we), wd in zip(ln, widths):
                    act = ws <= t < we + 0.05
                    d.text((x + 6, y + 8), w, font=f, fill=(0, 0, 0, 120), anchor="lm")
                    d.text((x, y), w, font=f, fill=(255, 230, 0) if act else (255, 255, 255),
                           stroke_width=10, stroke_fill=(0, 0, 0), anchor="lm")
                    x += wd
                y += 124

        img.alpha_composite(vign)
        d = ImageDraw.Draw(img, "RGBA")
        bw = d.textlength(banner, font=top_font) / 2 + 50
        d.rounded_rectangle([W / 2 - bw, 130, W / 2 + bw, 214], 42, fill=(0, 0, 0, 150))
        d.text((W / 2, 172), banner, font=top_font, fill=(255, 230, 0), anchor="mm")
        d.rounded_rectangle([40, 70, W - 40, 86], 8, fill=(0, 0, 0, 90))
        d.rounded_rectangle([40, 70, 40 + int((W - 80) * t / total), 86], 8, fill=(255, 230, 0))

        frame = img.convert("RGB")
        dx, dy = shake_offset(sc, lt)
        if dx or dy:
            frame = frame.resize((W + 60, H + 106)).crop((30 + dx, 53 + dy, 30 + dx + W, 53 + dy + H))
        if lt < 0.12 and sc is not scenes[0]:
            frame = Image.blend(frame, Image.new("RGB", (W, H), "white"), 0.65 * (1 - lt / 0.12))
        ff.stdin.write(frame.tobytes())
    ff.stdin.close(); ff.wait()
    print(out_path, f"{total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
