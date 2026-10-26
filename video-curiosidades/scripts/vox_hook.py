import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1]
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H, FPS = 1920, 1080, 30
rng = np.random.default_rng(11)

INK = (28, 24, 22)
RED = (200, 38, 38)
PAPER = np.array([234, 222, 198], dtype=np.float32)

f_type = lambda s: ImageFont.truetype(f"{FD}/SpecialElite-Regular.ttf", s)
f_big = lambda s: ImageFont.truetype(f"{FD}/Anton-Regular.ttf", s)
f_serif = lambda s: ImageFont.truetype(f"{FD}/AbrilFatface-Regular.ttf", s)
f_mark = lambda s: ImageFont.truetype(f"{FD}/PermanentMarker-Regular.ttf", s)


def ease_out(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = min(max(t, 0), 1)
    c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


# ---------- paper background (rendered once, a bit larger for the camera push) ----------
PW, PH = int(W * 1.12), int(H * 1.12)


def blotch(scale, amp, w, h):
    small = rng.normal(0, 1, (h // scale + 2, w // scale + 2)).astype(np.float32)
    im = Image.fromarray(((small * 40) + 128).clip(0, 255).astype(np.uint8))
    im = im.resize((w + 2 * scale, h + 2 * scale), Image.BICUBIC).crop((scale, scale, w + scale, h + scale))
    return (np.asarray(im, dtype=np.float32) - 128) / 40 * amp


tex = blotch(120, 9, PW, PH) + blotch(25, 4, PW, PH) + rng.normal(0, 4, (PH, PW)).astype(np.float32)
yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
tex -= (((xx - PW / 2) / (PW / 2)) ** 2 + ((yy - PH / 2) / (PH / 2)) ** 2) * 26
paper = Image.fromarray((PAPER[None, None, :] + tex[..., None] * np.array([1.0, 0.95, 0.85])).clip(0, 255).astype(np.uint8))
pd = ImageDraw.Draw(paper, "RGBA")
for _ in range(1400):
    x, y = rng.uniform(0, PW), rng.uniform(0, PH)
    a = rng.uniform(0, math.pi)
    L = rng.uniform(5, 18)
    pd.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=(120, 100, 80, int(rng.uniform(15, 40))), width=1)
paper = paper.convert("RGBA")

# pre-baked grain frames, cycled
GRAIN = []
for _ in range(6):
    g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    g = Image.fromarray((g * 18 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    GRAIN.append(np.asarray(g, dtype=np.int16) - 128)


def camera(img, t, z0=1.0, z1=1.06, shake=0.0, frame=0):
    """Slow push-in, optional shake; img is PW x PH."""
    z = z0 + (z1 - z0) * t
    cw, ch = W * 1.12 / z, H * 1.12 / z
    cx, cy = PW / 2, PH / 2
    if shake:
        cx += math.sin(frame * 2.3) * shake
        cy += math.cos(frame * 3.1) * shake
    box = (cx - cw / 2 * (W / (W * 1.12)) * 1.12, cy - ch / 2 * (H / (H * 1.12)) * 1.12)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return img.crop(tuple(int(v) for v in box)).resize((W, H), Image.BILINEAR)


def finish(img, frame):
    a = np.asarray(img.convert("RGB"), dtype=np.int16)
    a = (a + GRAIN[frame % len(GRAIN)][..., None]).clip(0, 255).astype(np.uint8)
    return a


def text_center(d, xy, s, font, fill):
    bb = d.textbbox((0, 0), s, font=font)
    d.text((xy[0] - (bb[2] - bb[0]) / 2 - bb[0], xy[1] - (bb[3] - bb[1]) / 2 - bb[1]), s, font=font, fill=fill)
    return bb


def typed(s, t, cps=28):
    return s[: int(t * cps)]


OX, OY = (PW - W) // 2, (PH - H) // 2  # content offset inside the larger paper

frames = []

# ---------- scene 1: "Você provavelmente já usou  3 COISAS  hoje" (0 – 3.6 s) ----------
S1 = int(3.6 * FPS)
for i in range(S1):
    t = i / FPS
    im = paper.copy()
    d = ImageDraw.Draw(im)
    line1 = "Você provavelmente já usou"
    text_center(d, (PW / 2, OY + 330), typed(line1, t), f_type(78), INK)
    # marker swipe behind "3 COISAS"
    k = ease_out((t - 1.0) / 0.35)
    if k > 0:
        font = f_big(250)
        bb = d.textbbox((0, 0), "3 COISAS", font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x0, y0 = PW / 2 - tw / 2 - 40, OY + 560 - th / 2 - 30
        mark = Image.new("RGBA", im.size, (0, 0, 0, 0))
        md = ImageDraw.Draw(mark)
        md.polygon([(x0, y0 + 14), (x0 + (tw + 80) * k, y0), (x0 + (tw + 80) * k, y0 + th + 54), (x0 + 6, y0 + th + 66)],
                   fill=RED + (235,))
        im.alpha_composite(mark)
        d = ImageDraw.Draw(im)
        if k > 0.6:
            text_center(d, (PW / 2, OY + 560), "3 COISAS", font, (250, 244, 230))
    if t > 1.9:
        text_center(d, (PW / 2, OY + 800), typed("hoje.", t - 1.9, 12), f_type(78), INK)
    frames.append(finish(camera(im, i / S1, 1.0, 1.05), i))

# ---------- scene 2: "que NUNCA deveriam ter existido" with stamp (3.6 – 7.2 s) ----------
S2 = int(3.6 * FPS)
stamp_font = f_big(300)
st = Image.new("RGBA", (1300, 460), (0, 0, 0, 0))
sd = ImageDraw.Draw(st)
sd.rounded_rectangle((20, 20, 1280, 440), 30, outline=RED + (255,), width=22)
text_center(sd, (650, 230), "NUNCA", stamp_font, RED + (255,))
holes = (rng.random((460, 1300)) > 0.12).astype(np.uint8) * 255
holes = Image.fromarray(holes).filter(ImageFilter.GaussianBlur(1.1))
sa = np.asarray(st.getchannel("A"), dtype=np.float32) * np.asarray(holes, dtype=np.float32) / 255 * 0.92
st.putalpha(Image.fromarray(sa.astype(np.uint8)))
st = st.rotate(-7, resample=Image.BICUBIC, expand=True)

for i in range(S2):
    t = i / FPS
    im = paper.copy()
    d = ImageDraw.Draw(im)
    text_center(d, (PW / 2, OY + 220), typed("que", t, 20), f_type(80), INK)
    k = (t - 0.35) / 0.18
    shake = 0
    if k > 0:
        s = 2.4 - 1.4 * ease_out(k)
        sw, sh = int(st.width * s), int(st.height * s)
        stamp = st.resize((sw, sh), Image.BILINEAR)
        if k < 1:
            stamp.putalpha(stamp.getchannel("A").point(lambda v: int(v * min(1, k * 1.5))))
        im.alpha_composite(stamp, (int(PW / 2 - sw / 2), int(OY + 540 - sh / 2)))
        if 1 <= k < 2.2:
            shake = 14 * (2.2 - k)
    d = ImageDraw.Draw(im)
    if t > 1.2:
        text_center(d, (PW / 2, OY + 880), typed("deveriam ter existido.", t - 1.2), f_type(80), INK)
    frames.append(finish(camera(im, i / S2, 1.0, 1.04, shake, i), S1 + i))

# ---------- scene 3: evidence board with 3 cards + red string (7.2 – 12 s) ----------
S3 = int(4.8 * FPS)
cards = []
for year, ang in (("1826", -6), ("1879", 4), ("1928", -3)):
    c = Image.new("RGBA", (420, 500), (0, 0, 0, 0))
    cd = ImageDraw.Draw(c)
    cd.rectangle((0, 0, 419, 499), fill=(250, 247, 238, 255))
    cd.rectangle((26, 26, 393, 380), fill=(40, 36, 34, 255))
    text_center(cd, (210, 203), "?", f_serif(260), (234, 222, 198, 255))
    text_center(cd, (210, 440), year, f_mark(70), INK + (255,))
    sh = Image.new("RGBA", (460, 540), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((20, 26, 440, 526), fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    sh.alpha_composite(c, (20, 20))
    cards.append(sh.rotate(ang, resample=Image.BICUBIC, expand=True))

xs = [PW / 2 - 560, PW / 2, PW / 2 + 560]
ys = [OY + 470, OY + 420, OY + 480]
for i in range(S3):
    t = i / FPS
    im = paper.copy()
    pins = []
    for n, card in enumerate(cards):
        k = ease_back((t - n * 0.45) / 0.45)
        if t - n * 0.45 <= 0:
            continue
        y = ys[n] - (1 - k) * 700
        im.alpha_composite(card, (int(xs[n] - card.width / 2), int(y - card.height / 2)))
        pins.append((xs[n], y - 230))
    d = ImageDraw.Draw(im)
    # red string connecting the pins, drawn progressively
    ks = ease_out((t - 1.7) / 0.8)
    if ks > 0 and len(pins) == 3:
        seg = ks * 2
        for a in range(2):
            p, q = pins[a], pins[a + 1]
            f = min(max(seg - a, 0), 1)
            if f > 0:
                d.line((p, (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)), fill=RED, width=7)
    for p in pins:
        d.ellipse((p[0] - 18, p[1] - 18, p[0] + 18, p[1] + 18), fill=RED, outline=(120, 20, 20), width=3)
        d.ellipse((p[0] - 7, p[1] - 9, p[0], p[1] - 2), fill=(255, 150, 150))
    if t > 2.6:
        s = "tudo por "
        font = f_type(84)
        full = typed("tudo por ACIDENTE.", t - 2.6, 22)
        part1 = full[: len(s)]
        part2 = full[len(s):]
        bb1 = d.textbbox((0, 0), s, font=font)
        bb2 = d.textbbox((0, 0), "ACIDENTE.", font=f_big(120))
        total = (bb1[2] - bb1[0]) + (bb2[2] - bb2[0])
        x = PW / 2 - total / 2
        d.text((x, OY + 890), part1, font=font, fill=INK)
        if part2:
            d.text((x + bb1[2] - bb1[0], OY + 862), part2, font=f_big(120), fill=RED)
    frames.append(finish(camera(im, i / S3, 1.0, 1.05), S1 + S2 + i))

# ---------- encode ----------
proc = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
     "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
    stdin=subprocess.PIPE)
for fr in frames:
    proc.stdin.write(fr.tobytes())
proc.stdin.close()
proc.wait()
print("frames", len(frames))
