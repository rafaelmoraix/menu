"""Vox-style collage on red paper for the opening line (3 coisas / NUNCA deveriam ter existido).
Crow professor talks in the corner; synthesized paper/whoosh/stamp/typewriter SFX are muxed in."""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crow_prof

CROW_SRC, OUT = sys.argv[1], sys.argv[2]
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H, FPS = 1920, 1080, 30
DUR = 8.0
N = int(DUR * FPS)
rng = np.random.default_rng(5)

INK = (24, 20, 20)
CREAM = (246, 238, 220)
NEWS = (232, 224, 204)
YEL = (238, 196, 60)
RED = (196, 30, 34)

F = {
    "anton": f"{FD}/Anton-Regular.ttf",
    "abril": f"{FD}/AbrilFatface-Regular.ttf",
    "type": f"{FD}/SpecialElite-Regular.ttf",
    "mark": f"{FD}/PermanentMarker-Regular.ttf",
}
font = lambda k, s: ImageFont.truetype(F[k], s)


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = min(max(t, 0.0), 1.0)
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


# ------------------------------------------------------------------ background
PW, PH = int(W * 1.08), int(H * 1.08)


def blotch(scale, amp, w, h):
    small = rng.normal(0, 1, (h // scale + 2, w // scale + 2)).astype(np.float32)
    im = Image.fromarray(((small * 40) + 128).clip(0, 255).astype(np.uint8))
    im = im.resize((w + 2 * scale, h + 2 * scale), Image.BICUBIC).crop((scale, scale, w + scale, h + scale))
    return (np.asarray(im, dtype=np.float32) - 128) / 40 * amp


tex = blotch(110, 8, PW, PH) + blotch(24, 5, PW, PH) + rng.normal(0, 6, (PH, PW)).astype(np.float32)
yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
tex -= (((xx - PW / 2) / (PW / 2)) ** 2 + ((yy - PH / 2) / (PH / 2)) ** 2) * 22
BG = (np.array([186, 30, 32], np.float32)[None, None] + tex[..., None] * np.array([1.0, 0.35, 0.35])).clip(0, 255)
BG = Image.fromarray(BG.astype(np.uint8))
bd = ImageDraw.Draw(BG, "RGBA")
for _ in range(1500):
    x, y = rng.uniform(0, PW), rng.uniform(0, PH)
    a = rng.uniform(0, math.pi)
    L = rng.uniform(5, 20)
    bd.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=(240, 130, 120, int(rng.uniform(20, 55))), width=1)
BG = BG.convert("RGBA")
OX, OY = (PW - W) // 2, (PH - H) // 2

GRAIN = []
for _ in range(6):
    g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    g = Image.fromarray((g * 14 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    GRAIN.append(np.asarray(g, dtype=np.int16) - 128)


# ------------------------------------------------------------------ collage helpers
def torn_poly(w, h, step=9, jit=3.5):
    pts = []
    for x in np.arange(0, w, step):
        pts.append((x, rng.uniform(-jit, jit)))
    for y in np.arange(0, h, step):
        pts.append((w + rng.uniform(-jit, jit), y))
    for x in np.arange(w, 0, -step):
        pts.append((x, h + rng.uniform(-jit, jit)))
    for y in np.arange(h, 0, -step):
        pts.append((rng.uniform(-jit, jit), y))
    return pts


def scrap(w, h, color, edge=(255, 252, 245)):
    """Torn paper piece with a lighter fibrous edge, paper grain and a drop shadow."""
    pad = 30
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    poly = [(x + pad, y + pad) for x, y in torn_poly(w, h)]
    under = [(x + rng.uniform(-3, 3), y + rng.uniform(-3, 3)) for x, y in torn_poly(w, h, 7, 6)]
    under = [(x + pad, y + pad) for x, y in under]
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).polygon([(x + 7, y + 10) for x, y in under], fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    shadow = Image.new("RGBA", img.size, (30, 0, 0, 255))
    shadow.putalpha(sh)
    img.alpha_composite(shadow)
    d = ImageDraw.Draw(img)
    d.polygon(under, fill=edge + (255,))
    d.polygon(poly, fill=color + (255,))
    n = rng.normal(0, 7, (img.height, img.width))
    arr = np.asarray(img, dtype=np.float32)
    m = arr[..., 3] > 0
    arr[..., :3][m] = (arr[..., :3][m] + n[m][:, None]).clip(0, 255)
    return Image.fromarray(arr.astype(np.uint8)), pad


def halftone(dark, spacing=8, color=INK):
    """dark: L image (255 = full ink). Returns RGBA dot layer."""
    out = Image.new("RGBA", dark.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    a = np.asarray(dark, dtype=np.float32) / 255
    for y in range(spacing // 2, dark.height, spacing):
        off = spacing // 2 if (y // spacing) % 2 else 0
        for x in range(spacing // 2 + off, dark.width, spacing):
            v = a[y, x]
            if v > 0.04:
                r = spacing * 0.62 * math.sqrt(v)
                d.ellipse((x - r, y - r, x + r, y + r), fill=color + (255,))
    return out


def bust(d, cx, base_y, s, shade, hat=None):
    """Simple head-and-shoulders silhouette."""
    d.ellipse((cx - 95 * s, base_y - 120 * s, cx + 95 * s, base_y + 80 * s), fill=shade)  # shoulders
    d.rectangle((cx - 22 * s, base_y - 150 * s, cx + 22 * s, base_y - 95 * s), fill=shade)  # neck
    d.ellipse((cx - 40 * s, base_y - 235 * s, cx + 40 * s, base_y - 135 * s), fill=shade)  # head
    if hat == "bowler":
        d.ellipse((cx - 58 * s, base_y - 222 * s, cx + 58 * s, base_y - 204 * s), fill=shade)
        d.ellipse((cx - 38 * s, base_y - 268 * s, cx + 38 * s, base_y - 200 * s), fill=shade)
    elif hat == "chef":
        d.rectangle((cx - 34 * s, base_y - 290 * s, cx + 34 * s, base_y - 215 * s), fill=shade)
        for k in (-30, 0, 30):
            d.ellipse((cx + (k - 30) * s, base_y - 330 * s, cx + (k + 30) * s, base_y - 270 * s), fill=shade)
    elif hat == "hair":
        d.ellipse((cx - 46 * s, base_y - 245 * s, cx + 46 * s, base_y - 170 * s), fill=shade)


def crowd_card(w, h, color):
    img, pad = scrap(w, h, color)
    dark = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(dark)
    rows = [(0.55, 120, 0.42), (0.75, 165, 0.62), (1.0, 230, 0.9)]
    for row, (s, step, shade) in enumerate(rows):
        x = rng.uniform(-30, 30)
        while x < w + 60:
            hat = rng.choice(["bowler", "hair", None, "bowler", None])
            bust(d, x, h - 10 - (2 - row) * 70, s * rng.uniform(0.9, 1.08), int(255 * shade), hat)
            x += step * rng.uniform(0.85, 1.15)
    dots = halftone(dark, 8)
    img.alpha_composite(dots, (pad, pad))
    return img


def person_card(w, h, color, hat):
    img, pad = scrap(w, h, color)
    dark = Image.new("L", (w, h), 0)
    bust(ImageDraw.Draw(dark), w / 2, h + 20, w / 210, 230, hat)
    img.alpha_composite(halftone(dark, 7), (pad, pad))
    return img


def petri_card():
    w, h = 470, 430
    img, pad = scrap(w, h, (250, 248, 242))
    d = ImageDraw.Draw(img)
    cx, cy, r = pad + w / 2, pad + h / 2 - 25, 170
    d.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=(205, 210, 205, 255), outline=(150, 155, 150, 255), width=3)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(236, 214, 150, 255))
    mx, my = cx - 30, cy + 10
    for _ in range(220):  # bacteria colonies, killed in a ring around the mould
        a, rr = rng.uniform(0, math.tau), rng.uniform(0, r - 10)
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        if math.hypot(x - mx, y - my) < 105:
            continue
        q = rng.uniform(3, 6)
        d.ellipse((x - q, y - q, x + q, y + q), fill=(250, 244, 222, 255), outline=(200, 180, 120, 255))
    mould = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mould)
    for _ in range(40):
        a, rr = rng.uniform(0, math.tau), rng.uniform(0, 34)
        q = rng.uniform(16, 30)
        x, y = mx + math.cos(a) * rr, my + math.sin(a) * rr
        md.ellipse((x - q, y - q, x + q, y + q), fill=255)
    mould = mould.filter(ImageFilter.GaussianBlur(3))
    green = Image.new("RGBA", img.size, (96, 128, 84, 255))
    green.putalpha(mould)
    img.alpha_composite(green)
    rim = mould.filter(ImageFilter.MaxFilter(9)).point(lambda v: 150 if v > 60 else 0).filter(ImageFilter.GaussianBlur(2))
    rimc = Image.new("RGBA", img.size, (240, 246, 232, 255))
    rimc.putalpha(Image.fromarray((np.asarray(rim, np.int16) - np.asarray(mould, np.int16)).clip(0, 255).astype(np.uint8)))
    img.alpha_composite(rimc)
    d.arc((cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18), 200, 250, fill=(255, 255, 255, 200), width=6)
    d.text((pad + w / 2 - 55, pad + h - 70), "1928", font=font("mark", 54), fill=INK + (255,))
    return img


def label(text, fk, size, fg, bg, padx=26, pady=14):
    f = font(fk, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    img, pad = scrap(tw + 2 * padx, th + 2 * pady, bg)
    ImageDraw.Draw(img).text((pad + padx - bb[0], pad + pady - bb[1]), text, font=f, fill=fg + (255,))
    return img


def clipping():
    w, h = 640, 470
    img, pad = scrap(w, h, NEWS)
    d = ImageDraw.Draw(img)
    d.text((pad + 30, pad + 18), "A LENDA DA", font=font("abril", 58), fill=INK + (255,))
    d.text((pad + 30, pad + 88), "BATATA CHIPS", font=font("abril", 58), fill=INK + (255,))
    d.line((pad + 30, pad + 168, pad + w - 30, pad + 168), fill=INK + (255,), width=3)
    pic = Image.new("L", (250, 230), 0)
    bust(ImageDraw.Draw(pic), 125, 250, 1.0, 230, "chef")
    d.rectangle((pad + 30, pad + 190, pad + 280, pad + 420), fill=(214, 204, 180, 255))
    img.alpha_composite(halftone(pic, 6), (pad + 30, pad + 190))
    for row in range(10):
        y = pad + 196 + row * 23
        d.rectangle((pad + 305, y, pad + w - 30 - rng.uniform(0, 60), y + 9), fill=(120, 112, 100, 255))
    d.text((pad + 30, pad + 428), "Saratoga Springs, 1853", font=font("type", 26), fill=INK + (255,))
    return img


def stamp(text, size, w, h):
    st = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rounded_rectangle((14, 14, w - 14, h - 14), 22, fill=(250, 240, 225, 255), outline=RED + (255,), width=16)
    f = font("anton", size)
    bb = sd.textbbox((0, 0), text, font=f)
    sd.text((w / 2 - (bb[2] - bb[0]) / 2 - bb[0], h / 2 - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=RED + (255,))
    holes = Image.fromarray(((rng.random((h, w)) > 0.14) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))
    a = np.asarray(st.getchannel("A"), np.float32) * np.asarray(holes, np.float32) / 255 * 0.95
    st.putalpha(Image.fromarray(a.astype(np.uint8)))
    return st.rotate(-9, resample=Image.BICUBIC, expand=True)


# ------------------------------------------------------------------ timeline of collage elements
SFX = []  # (time, kind)


class El:
    def __init__(self, img, x, y, t_in, rot=0.0, kind="slap", t_out=None, dur=0.16, sfx="slap"):
        self.img, self.x, self.y, self.t_in, self.rot, self.kind, self.t_out, self.dur = img, x, y, t_in, rot, kind, t_out, dur
        self.cache = None
        if sfx:
            SFX.append((t_in, sfx))

    def draw(self, canvas, t):
        if t < self.t_in:
            return
        p = (t - self.t_in) / self.dur
        x, y, rot, s, alpha = self.x, self.y, self.rot, 1.0, 1.0
        if self.kind == "slap":
            s = 1.0 + 0.32 * (1 - ease_out(p))
            alpha = min(1.0, p * 2.5)
        elif self.kind == "pop":
            s = max(0.01, ease_back(p))
        moving = p < 1
        if self.t_out is not None and t > self.t_out:
            q = (t - self.t_out) / 0.3
            x -= (q ** 2) * 2200
            rot += q * 30
            moving = True
        if not moving and self.cache is not None:
            img = self.cache
        else:
            img = self.img.rotate(rot, resample=Image.BICUBIC, expand=True)
            if abs(s - 1) > 0.005:
                img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)
            if alpha < 1:
                img = img.copy()
                img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
            if not moving:
                self.cache = img
        canvas.alpha_composite(img, (int(OX + x - img.width / 2), int(OY + y - img.height / 2)))


els = []

STYLES = [(CREAM, INK, "abril"), (INK, CREAM, "anton"), ((255, 255, 255), RED, "anton"), (YEL, INK, "type"),
          (NEWS, INK, "anton"), (CREAM, RED, "abril"), (INK, YEL, "abril")]
# opening line: "Você provavelmente já usou pelo menos 3 coisas hoje / que provavelmente NUNCA deveriam ter existido"
T_OUT_A = 3.3


def strip(text, fk, size, fg, bg, padx=26, pady=14):
    """Blank torn strip sized for `text`; returns (img, text_xy, font, fg) so text can be typed onto copies."""
    f = font(fk, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    img, pad = scrap(bb[2] - bb[0] + 2 * padx, bb[3] - bb[1] + 2 * pady, bg)
    return img, (pad + padx - bb[0], pad + pady - bb[1]), f, fg


class Typed:
    def __init__(self, text, fk, size, fg, bg, x, y, t0, rot, t_out=None, cps=24):
        self.blank, self.xy, self.f, self.fg = strip(text, fk, size, fg, bg)
        self.text, self.t0, self.cps = text, t0, cps
        self.el = El(self.blank, x, y, t0, rot, "slap", t_out, 0.14, "slap")
        self.last = -1
        for k, ch in enumerate(text):
            if ch != " ":
                SFX.append((t0 + 0.12 + k / cps, "key"))

    def draw(self, canvas, t):
        n = max(0, min(len(self.text), int((t - self.t0 - 0.12) * self.cps)))
        if n != self.last:
            im = self.blank.copy()
            ImageDraw.Draw(im).text(self.xy, self.text[:n], font=self.f, fill=self.fg + (255,))
            self.el.img, self.el.cache, self.last = im, None, n
        self.el.draw(canvas, t)


def match_card():
    img, pad = scrap(230, 270, CREAM)
    d = ImageDraw.Draw(img)
    cx = pad + 115
    d.polygon([(cx - 10, pad + 250), (cx + 10, pad + 250), (cx + 8, pad + 120), (cx - 8, pad + 120)], fill=(214, 170, 110, 255))
    d.ellipse((cx - 17, pad + 96, cx + 17, pad + 140), fill=(150, 40, 30, 255))
    d.polygon([(cx, pad + 14), (cx + 34, pad + 70), (cx + 22, pad + 104), (cx, pad + 112), (cx - 22, pad + 104), (cx - 34, pad + 70)], fill=(240, 140, 40, 255))
    d.polygon([(cx, pad + 50), (cx + 16, pad + 82), (cx, pad + 104), (cx - 16, pad + 82)], fill=(250, 220, 90, 255))
    return img


def postit_card():
    img, pad = scrap(250, 240, (250, 226, 90), edge=(255, 240, 150))
    d = ImageDraw.Draw(img)
    d.text((pad + 26, pad + 40), "não", font=font("mark", 54), fill=INK + (255,))
    d.text((pad + 26, pad + 110), "esquecer!", font=font("mark", 42), fill=INK + (255,))
    return img


def popsicle_card():
    img, pad = scrap(220, 280, (200, 228, 236))
    d = ImageDraw.Draw(img)
    cx = pad + 110
    d.rounded_rectangle((cx - 13, pad + 170, cx + 13, pad + 262), 10, fill=(222, 186, 130, 255))
    d.rounded_rectangle((cx - 60, pad + 20, cx + 60, pad + 200), 50, fill=(226, 58, 90, 255))
    d.rounded_rectangle((cx - 40, pad + 36, cx - 24, pad + 150), 8, fill=(250, 150, 170, 255))
    return img


els = []
TY1 = Typed("Você provavelmente já usou", "type", 66, INK, CREAM, 660, 190, 0.15, -2, T_OUT_A)
els.append(TY1)
THREE = El(label("3", "anton", 330, INK, YEL, 40, 6), 300, 540, 1.6, -7, t_out=T_OUT_A)
els.append(THREE)
els.append(El(label("COISAS", "anton", 170, CREAM, INK, 34, 14), 760, 520, 1.85, 3, t_out=T_OUT_A))
for img, x, y, rot, t0 in ((match_card(), 610, 850, -8, 2.25), (postit_card(), 880, 860, 6, 2.45), (popsicle_card(), 1130, 830, -4, 2.65)):
    els.append(El(img, x, y, t0, rot, "pop", T_OUT_A, 0.22, "tap"))
CIRCLE_T0 = 2.75
SFX.append((CIRCLE_T0, "scribble"))

T_B = 3.45
TY2 = Typed("que provavelmente", "type", 66, INK, CREAM, 640, 200, T_B, 2, None)
els.append(TY2)
NUNCA = El(stamp("NUNCA", 250, 860, 340), 650, 500, 4.4, 0, dur=0.14, sfx="stamp")
els.append(NUNCA)
TY3 = Typed("deveriam ter", "type", 66, INK, CREAM, 640, 760, 5.15, -3, None, cps=26)
els.append(TY3)
letters = []
for ch in "EXISTIDO":
    bg, fg, fk = STYLES[rng.integers(len(STYLES))]
    letters.append(label(ch, fk, int(rng.uniform(110, 135)), fg, bg, 14, 10))
x = 640 - sum(l.width - 40 for l in letters) / 2
for k, l in enumerate(letters):
    els.append(El(l, x + (l.width - 40) / 2, 930 + rng.uniform(-12, 12), 5.55 + k * 0.075, rng.uniform(-9, 9), "pop", None, 0.2, "tap"))
    x += l.width - 40

# ------------------------------------------------------------------ crow professor
CROW = crow_prof.build(CROW_SRC, 1.0)
CROW_SCALE = 1.08
crow_cache = {}


def crow_img(level):
    if level not in crow_cache:
        im = crow_prof.frame(CROW, level / 6)
        crow_cache[level] = im.resize((int(im.width * CROW_SCALE), int(im.height * CROW_SCALE)), Image.LANCZOS)
    return crow_cache[level]


# talking envelope: syllables with pauses where the scenes change
talk = np.zeros(N)
pauses = [(0, 0.2), (3.25, 3.5), (6.6, DUR)]
tt = 0.25
while tt < DUR:
    d_ = rng.uniform(0.11, 0.2)
    amp = rng.uniform(0.35, 1.0)
    i0, i1 = int(tt * FPS), int((tt + d_) * FPS)
    for i in range(i0, min(i1 + 1, N)):
        ph = (i / FPS - tt) / d_
        talk[i] = max(talk[i], amp * math.sin(math.pi * min(max(ph, 0), 1)))
    tt += d_ + rng.uniform(0.02, 0.08)
for a, b in pauses:
    talk[int(a * FPS):int(b * FPS)] = 0
SFX.append((0.0, "whoosh"))
SFX.append((T_OUT_A, "whoosh"))


def draw_crow(canvas, i, t):
    k = ease_back(t / 0.4)
    img = crow_img(int(round(talk[i] * 6)))
    bob = math.sin(t * 7.0) * 1.2 * (talk[i] > 0.05)
    img = img.rotate(bob, resample=Image.BICUBIC, center=(img.width * 0.6, img.height))
    x = OX + W - img.width + 30 + (1 - k) * 900
    y = OY + H - img.height + 60 + math.sin(t * 2.1) * 6
    canvas.alpha_composite(img, (int(x), int(y)))


# ------------------------------------------------------------------ render
def fmt(n):
    return f"{n:,}".replace(",", ".")


frames = []
for i in range(N):
    t = i / FPS
    canvas = BG.copy()
    for e in els:
        e.draw(canvas, t)
    # hand-drawn circle around the "3" + "hoje!"
    if CIRCLE_T0 <= t < T_OUT_A + 0.35:
        dx = -((t - T_OUT_A) / 0.3) ** 2 * 2200 if t > T_OUT_A else 0
        d = ImageDraw.Draw(canvas)
        prog = min(1, (t - CIRCLE_T0) / 0.4)
        cx0, cy0 = OX + 300 + dx, OY + 540
        pts = []
        for j in range(int(60 * prog) + 1):
            a = -2.2 + j / 60 * math.tau * 1.08
            r = 230 + math.sin(j * 0.7) * 6 + j * 0.4
            pts.append((cx0 + math.cos(a) * r * 0.82, cy0 + math.sin(a) * r))
        if len(pts) > 1:
            d.line(pts, fill=CREAM + (255,), width=14, joint="curve")
        if t > CIRCLE_T0 + 0.35:
            d.text((OX + 60 + dx, OY + 760), "hoje!", font=font("mark", 92), fill=CREAM + (255,))
    draw_crow(canvas, i, t)
    # camera: slow push, kick on the stamp
    z = 1.0 + 0.045 * t / DUR
    shake = 14 * max(0, 1 - (t - 4.4) / 0.4) if t >= 4.4 else 0
    cw, ch = PW / 1.08 / z * 1.0, PH / 1.08 / z
    cx = PW / 2 + math.sin(i * 2.7) * shake
    cy = PH / 2 + math.cos(i * 3.3) * shake
    fr = canvas.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BILINEAR)
    a = (np.asarray(fr.convert("RGB"), np.int16) + GRAIN[i % 6][..., None]).clip(0, 255).astype(np.uint8)
    frames.append(a)

# ------------------------------------------------------------------ audio
SR = 44100
mix = np.zeros(int(DUR * SR) + SR)


def band(n, lo, hi):
    x = rng.normal(size=n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, n)
    return y / (np.abs(y).max() + 1e-9)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def thump(n, f0, f1, tau):
    tt_ = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt_ / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt_ / tau)


def snd(kind):
    if kind == "slap":
        n = int(0.16 * SR)
        return 0.55 * band(n, 700, 6500) * env_exp(n, 0.02) + 0.5 * thump(n, 140, 60, 0.035)
    if kind == "tap":
        n = int(0.06 * SR)
        return 0.38 * band(n, 1500, 8000) * env_exp(n, 0.008) + 0.12 * thump(n, 300, 180, 0.012)
    if kind == "whoosh":
        n = int(0.42 * SR)
        e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
        lo, hi = band(n, 250, 1400), band(n, 1400, 6000)
        x = np.linspace(0, 1, n)
        return 0.45 * e * (lo * (1 - x) + hi * x)
    if kind == "rustle":
        n = int(0.5 * SR)
        c = np.abs(band(n, 5, 40)) ** 3
        return 0.4 * band(n, 2000, 9000) * c / (c.max() + 1e-9) * np.sin(np.pi * np.linspace(0, 1, n))
    if kind == "tape":
        n = int(0.22 * SR)
        c = (rng.random(n) > 0.6).astype(float)
        e = np.linspace(0.3, 1, n) ** 2
        e[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
        return 0.45 * band(n, 1200, 7000) * c * e
    if kind == "stamp":
        n = int(0.45 * SR)
        return 0.95 * thump(n, 110, 45, 0.09) + 0.5 * band(n, 200, 3000) * env_exp(n, 0.012)
    if kind == "key":
        n = int(0.05 * SR)
        return 0.3 * band(n, 2000, 9000) * env_exp(n, 0.006) + 0.15 * thump(n, 260, 160, 0.01)
    if kind == "scribble":
        n = int(0.55 * SR)
        tt_ = np.arange(n) / SR
        m = (0.5 + 0.5 * np.sin(2 * np.pi * 9 * tt_)) ** 2
        return 0.35 * band(n, 1500, 5500) * m * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.5
    if kind == "tick":
        n = int(0.015 * SR)
        return 0.16 * np.sin(2 * np.pi * 2300 * np.arange(n) / SR) * env_exp(n, 0.003)
    if kind == "ding":
        n = int(0.8 * SR)
        tt_ = np.arange(n) / SR
        return 0.3 * (np.sin(2 * np.pi * 1320 * tt_) + 0.5 * np.sin(2 * np.pi * 1980 * tt_)) * env_exp(n, 0.18)
    raise ValueError(kind)


for t0, kind in SFX:
    s = snd(kind)
    i0 = int(t0 * SR)
    mix[i0:i0 + len(s)] += s[: len(mix) - i0]
mix = mix[: int(DUR * SR)]
mix = mix / (np.abs(mix).max() + 1e-9) * 0.7
pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
wav_path = OUT.rsplit(".", 1)[0] + "_sfx.wav"
with wave.open(wav_path, "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())

proc = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-i", wav_path, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
     "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for fr in frames:
    proc.stdin.write(fr.tobytes())
proc.stdin.close()
proc.wait()
print("ok", len(frames), "frames,", len(SFX), "sfx")
