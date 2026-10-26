"""Vox-style collage on purple paper: #8 saccharin — Fahlberg (photo-head paper doll), the lab, dinner with unwashed hands, sweet bread.
Crow professor talks in the corner; synthesized paper/whoosh/stamp/typewriter SFX are muxed in."""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crow_prof

CROW_SRC, OUT = sys.argv[1], sys.argv[2]
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H, FPS = 1920, 1080, 30
DUR = 33.0
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
BG = (np.array([26, 25, 36], np.float32)[None, None] + tex[..., None] * np.array([0.5, 0.5, 0.7])).clip(0, 255)
BG = Image.fromarray(BG.astype(np.uint8))
bd = ImageDraw.Draw(BG, "RGBA")
for _ in range(1500):
    x, y = rng.uniform(0, PW), rng.uniform(0, PH)
    a = rng.uniform(0, math.pi)
    L = rng.uniform(5, 20)
    bd.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=(120, 120, 150, int(rng.uniform(15, 40))), width=1)
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
    shadow = Image.new("RGBA", img.size, (40, 0, 50, 255))
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
    elif hat == "tophat":
        d.rounded_rectangle((cx - 62 * s, base_y - 228 * s, cx + 62 * s, base_y - 212 * s), 6, fill=shade)
        d.rectangle((cx - 40 * s, base_y - 330 * s, cx + 40 * s, base_y - 215 * s), fill=shade)
        d.rectangle((cx - 30 * s, base_y - 150 * s, cx + 30 * s, base_y - 115 * s), fill=shade)  # high collar
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
# "Quando voltaram, a massa tinha ficado velha. Em vez de jogar tudo fora, eles resolveram passar a massa no
#  rolo. E aí veio a surpresa: em vez de virar uma folha lisa, ela se partiu em vários flocos."
import paper_dolls as PD

DOLL_NOISE = rng.normal(0, 6, (PD.CH, PD.CW, 1))


def doll(kind, **pose):
    im = PD.draw(kind, **pose)
    a = np.asarray(im, np.float32)
    m = a[..., 3:] > 0
    a[..., :3] = np.where(m, (a[..., :3] + DOLL_NOISE).clip(0, 255), a[..., :3])
    return PD.with_border(Image.fromarray(a.astype(np.uint8)))


TABLE_X0, TABLE_X1, TABLE_Y = 360, 900, 812
TCX = (TABLE_X0 + TABLE_X1) / 2
FEET_Y = 1040


def table_img():
    w = TABLE_X1 - TABLE_X0
    im = Image.new("RGBA", (w + 40, 340), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for lx in (40, w - 10):
        d.rectangle((lx, 30, lx + 26, 330), fill=(104, 68, 40, 255))
    d.rectangle((20, 0, w + 20, 34), fill=(150, 98, 56, 255))
    for k in range(5):
        y = 6 + k * 6
        d.line((30, y, w + 10, y + rng.uniform(-2, 2)), fill=(128, 82, 46, 255), width=1)
    d.rectangle((20, 30, w + 20, 40), fill=(104, 68, 40, 255))
    return sticker(im, 6)



def sticker(img, r=9, col=(250, 246, 236)):
    pad = r + 24
    big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", big.size, 0)
    a.paste(img.getchannel("A"), (pad, pad))
    border = a.point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.MaxFilter(2 * r + 1)).filter(ImageFilter.GaussianBlur(1))
    sh = border.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.45))
    shadow = Image.new("RGBA", big.size, (40, 0, 50, 255))
    shadow.putalpha(sh)
    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, (6, 9))
    paper = Image.new("RGBA", big.size, col + (255,))
    paper.putalpha(border)
    out.alpha_composite(paper)
    out.alpha_composite(img, (pad, pad))
    return out


def pot_img():
    im = Image.new("RGBA", (260, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 40, 240, 168), 30, fill=(74, 76, 86, 255))
    d.ellipse((6, 22, 254, 66), fill=(104, 106, 118, 255))
    d.ellipse((22, 30, 238, 60), fill=(176, 170, 118, 255))
    for k in range(9):
        x, y = rng.uniform(40, 220), rng.uniform(34, 52)
        d.ellipse((x - 14, y - 8, x + 14, y + 8), fill=(160, 158, 104, 255))
        d.ellipse((x - 4, y - 3, x + 2, y + 1), fill=(120, 140, 80, 255))
    d.rectangle((0, 70, 24, 84), fill=(54, 56, 64, 255))
    d.rectangle((236, 70, 260, 84), fill=(54, 56, 64, 255))
    return sticker(im, 6)


def trash_img():
    im = Image.new("RGBA", (190, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(26, 40), (164, 40), (150, 226), (40, 226)], fill=(150, 156, 160, 255))
    for x in (60, 95, 130):
        d.line((x, 56, x - 4 + (x - 95) * 0.1, 212), fill=(110, 116, 122, 255), width=8)
    d.rounded_rectangle((10, 18, 180, 44), 8, fill=(120, 126, 132, 255))
    d.rounded_rectangle((76, 0, 114, 22), 8, fill=(120, 126, 132, 255))
    return sticker(im, 6)


def pin_img():
    im = Image.new("RGBA", (380, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((70, 4, 310, 56), 24, fill=(206, 160, 104, 255))
    d.line((90, 18, 290, 18), fill=(232, 196, 140, 255), width=6)
    for x0 in (0, 300):
        d.rounded_rectangle((x0 + 4, 20, x0 + 76, 40), 10, fill=(170, 122, 72, 255))
    return sticker(im, 5)


def flake_img(seed):
    r_ = np.random.default_rng(seed)
    im = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    n = r_.integers(6, 9)
    pts = []
    for k in range(n):
        a = k / n * math.tau
        rr = r_.uniform(18, 32)
        pts.append((35 + math.cos(a) * rr, 35 + math.sin(a) * rr * r_.uniform(0.6, 1.0)))
    d.polygon(pts, fill=(176, 104, 36, 255))
    d.polygon([(35 + (x - 35) * 0.8, 35 + (y - 35) * 0.8) for x, y in pts], fill=(232, 172, 70, 255))
    d.line([(35 + (x - 35) * 0.5, 33 + (y - 35) * 0.4) for x, y in pts[:3]], fill=(250, 214, 130, 255), width=3)
    return sticker(im, 4)


TABLE = table_img()
POT, TRASH, PIN = pot_img(), trash_img(), pin_img()
FLAKES = [flake_img(k) for k in range(6)]
KERNEL = FLAKES[0]

def strip_(text, fk, size, fg, bg, padx=26, pady=14):
    f = font(fk, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    img, pad = scrap(bb[2] - bb[0] + 2 * padx, bb[3] - bb[1] + 2 * pady, bg)
    return img, (pad + padx - bb[0], pad + pady - bb[1]), f, fg


class Typed:
    def __init__(self, text, fk, size, fg, bg, x, y, t0, rot, cps=24):
        self.blank, self.xy, self.f, self.fg = strip_(text, fk, size, fg, bg)
        self.text, self.t0, self.cps, self.last = text, t0, cps, -1
        self.el = El(self.blank, x, y, t0, rot, "slap", None, 0.14, "slap")
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



# ======================= "milho → Corn Flakes → açúcar → briga → 1906 → resumo" =======================
GREEN = (0, 214, 0)


def lerp(a, b, u):
    u = min(max(u, 0), 1)
    return a + (b - a) * u


def sack_img(text, col):
    im = Image.new("RGBA", (230, 270), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(30, 70), (200, 70), (220, 250), (115, 266), (10, 250)], fill=col + (255,))
    d.polygon([(70, 70), (160, 70), (186, 22), (44, 22)], fill=col + (255,))
    d.rectangle((60, 60, 170, 76), fill=(120, 84, 50, 255))
    for k in range(6):
        d.line((30 + k * 32, 90, 22 + k * 34, 240), fill=(int(col[0] * 0.85), int(col[1] * 0.85), int(col[2] * 0.85), 255), width=3)
    f = font("anton", 54)
    bb = d.textbbox((0, 0), text, font=f)
    d.rectangle((115 - (bb[2] - bb[0]) / 2 - 14, 130, 115 + (bb[2] - bb[0]) / 2 + 14, 210), fill=(250, 244, 230, 255))
    d.text((115 - (bb[2] - bb[0]) / 2 - bb[0], 170 - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=INK + (255,))
    return sticker(im, 6)


def cob_img():
    w, h = 110, 260
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(55, 250), (8, 140), (20, 60), (50, 200)], fill=(92, 150, 70, 255))
    d.polygon([(55, 250), (102, 150), (92, 70), (62, 200)], fill=(72, 128, 56, 255))
    d.ellipse((24, 10, 86, 230), fill=(236, 180, 40, 255))
    for row in range(14):
        for col in range(4):
            x = 30 + col * 13 + (row % 2) * 4
            y = 22 + row * 14
            if (x - 55) ** 2 / 31 ** 2 + (y - 120) ** 2 / 110 ** 2 < 0.92:
                d.rounded_rectangle((x, y, x + 10, y + 11), 4, fill=(250, 210, 70, 255), outline=(200, 140, 20, 255))
    return sticker(im, 6)


def tv_img():
    """Vintage TV cut from paper with a chroma-green screen for real footage."""
    w, h = 700, 540
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line((300, 80, 220, 4), fill=(40, 34, 30, 255), width=8)
    d.line((400, 80, 480, 4), fill=(40, 34, 30, 255), width=8)
    d.rounded_rectangle((0, 70, w, h - 30), 46, fill=(150, 98, 56, 255))
    d.rounded_rectangle((14, 84, w - 14, h - 44), 40, outline=(118, 74, 40, 255), width=6)
    d.rounded_rectangle((40, 110, 540, 470), 50, fill=(40, 34, 30, 255))
    d.rounded_rectangle((60, 128, 520, 452), 40, fill=GREEN + (255,))
    for k, y in enumerate((170, 270)):
        d.ellipse((585, y, 655, y + 70), fill=(216, 196, 150, 255), outline=(60, 44, 30, 255), width=5)
        d.line((620, y + 35, 620 + 22 * (1 if k else -1), y + 14), fill=(60, 44, 30, 255), width=6)
    for k in range(5):
        d.line((580, 380 + k * 14, 660, 380 + k * 14), fill=(90, 58, 32, 255), width=5)
    d.rectangle((80, h - 34, 140, h), fill=(80, 52, 30, 255))
    d.rectangle((w - 140, h - 34, w - 80, h), fill=(80, 52, 30, 255))
    return sticker(im, 8)


def sunburst(size=1500, n=18):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    for k in range(n):
        a0, a1 = k / n * math.tau, (k + 0.5) / n * math.tau
        d.polygon([(c, c), (c + math.cos(a0) * c * 1.5, c + math.sin(a0) * c * 1.5),
                   (c + math.cos(a1) * c * 1.5, c + math.sin(a1) * c * 1.5)], fill=(250, 220, 120, 70))
    return im


def jar_img():
    im = Image.new("RGBA", (170, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 40, 160, 216), 28, fill=(200, 230, 245, 255), outline=(120, 160, 190, 255), width=4)
    for k in range(14):
        x, y = 30 + (k % 4) * 30 + rng.uniform(-4, 4), 120 + (k // 4) * 26
        d.rectangle((x, y, x + 24, y + 22), fill=(255, 255, 255, 255), outline=(200, 200, 210, 255))
    d.rounded_rectangle((26, 6, 144, 44), 10, fill=(196, 40, 44, 255))
    d.rectangle((24, 62, 146, 108), fill=(250, 244, 230, 255))
    f = font("anton", 34)
    bb = d.textbbox((0, 0), "AÇÚCAR", font=f)
    d.text((85 - (bb[2] - bb[0]) / 2 - bb[0], 85 - (bb[3] - bb[1]) / 2 - bb[1]), "AÇÚCAR", font=f, fill=INK + (255,))
    return sticker(im, 6)


def bolt_img():
    im = Image.new("RGBA", (200, 360), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(120, 0), (20, 190), (90, 190), (50, 360), (180, 140), (110, 140), (170, 0)],
                               fill=(255, 214, 40, 255))
    return sticker(im, 8, (255, 255, 255))


def cloud_img():
    im = Image.new("RGBA", (620, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(26):
        x, y, r = rng.uniform(110, 510), rng.uniform(110, 310), rng.uniform(60, 110)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(246, 240, 226, 255))
    for txt, x, y, col in (("#@$%!", 170, 150, RED), ("!!", 420, 120, INK), ("?#!", 380, 250, RED)):
        d.text((x, y), txt, font=font("anton", 70), fill=col + (255,))
    for _ in range(6):
        x, y = rng.uniform(140, 480), rng.uniform(120, 300)
        pts = [(x + math.cos(k * math.pi / 5) * (28 if k % 2 == 0 else 12), y + math.sin(k * math.pi / 5) * (28 if k % 2 == 0 else 12))
               for k in range(10)]
        d.polygon(pts, fill=(255, 214, 40, 255))
    return sticker(im, 8)


def factory_img():
    im = Image.new("RGBA", (620, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((470, 20, 530, 260), fill=(140, 60, 44, 255))
    d.rectangle((462, 20, 538, 40), fill=(110, 46, 34, 255))
    base = 410
    d.rectangle((20, 200, 600, base), fill=(176, 80, 56, 255))
    for k in range(4):
        x = 20 + k * 145
        d.polygon([(x, 200), (x + 145, 200), (x + 145, 130)], fill=(150, 66, 46, 255))
    for row in range(2):
        for col in range(7):
            x, y = 50 + col * 78, 240 + row * 70
            d.rectangle((x, y, x + 44, y + 44), fill=(250, 220, 120, 255), outline=(110, 46, 34, 255), width=4)
            d.line((x + 22, y, x + 22, y + 44), fill=(110, 46, 34, 255), width=3)
    d.rectangle((260, 330, 360, base), fill=(90, 40, 30, 255))
    return sticker(im, 8)


def box_img():
    w, h = 300, 420
    im = Image.new("RGBA", (w + 40, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(w, 10), (w + 36, 0), (w + 36, h - 14), (w, h)], fill=(196, 150, 40, 255))
    d.rectangle((0, 10, w, h), fill=(244, 204, 64, 255))
    d.rectangle((0, 10, w, 90), fill=(196, 34, 40, 255))
    for txt, f, y, col in (("TOASTED", font("type", 36), 50, CREAM), ("CORN", font("anton", 92), 150, RED),
                           ("FLAKES", font("anton", 92), 250, RED)):
        bb = d.textbbox((0, 0), txt, font=f)
        d.text((w / 2 - (bb[2] - bb[0]) / 2 - bb[0], y - (bb[3] - bb[1]) / 2 - bb[1]), txt, font=f, fill=col + (255,))
    d.chord((60, 300, 240, 420), 0, 180, fill=(250, 250, 250, 255))
    for k in range(9):
        x = 80 + k * 18
        d.ellipse((x, 344 - (k % 3) * 8, x + 26, 366 - (k % 3) * 8), fill=(226, 160, 60, 255))
    return sticker(im, 8)


def heart_img():
    im = Image.new("RGBA", (80, 72), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 42, 42), fill=RED + (255,))
    d.ellipse((38, 4, 76, 42), fill=RED + (255,))
    d.polygon([(6, 30), (74, 30), (40, 70)], fill=RED + (255,))
    return sticker(im, 4)



# ======================= #8 ADOÇANTE: "Em 1879 ... estava doce. Muito doce." =======================
import json
FAHL_SRC = sys.argv[3]
GEO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo", "package", "states-10m.json")


def photo_cut(box, bottom=None, hide=None):
    """Cut a region of the purple-background photo; alpha from low saturation (B&W photo vs purple)."""
    im = Image.open(FAHL_SRC).convert("RGB").crop(box)
    a = np.asarray(im, np.float32)
    sat = a.max(-1) - a.min(-1)
    alpha = ((60 - sat) / 30).clip(0, 1) * 255
    if bottom is not None:
        alpha[bottom - box[1]:] = 0
    if hide is not None:  # drop another object that overlaps the crop (the spoon next to his face)
        alpha[: hide[1] - box[1], : hide[0] - box[0]] = 0
    g = a.mean(-1, keepdims=True)
    g = ((g - 128) * 1.12 + 128).clip(0, 255)
    rgb = np.concatenate([g * 1.0, g * 0.98, g * 0.94], -1) + rng.normal(0, 5, g.shape)
    out = Image.fromarray(np.concatenate([rgb.clip(0, 255), alpha[..., None]], -1).astype(np.uint8), "RGBA")
    return out.filter(ImageFilter.SMOOTH)


BUST_RAW = photo_cut((150, 8, 547, 365), hide=(262, 236))
BUST = sticker(BUST_RAW.resize((int(BUST_RAW.width * 2.0), int(BUST_RAW.height * 2.0)), Image.LANCZOS), 9)
BUST_S = sticker(BUST_RAW.resize((int(BUST_RAW.width * 0.95), int(BUST_RAW.height * 0.95)), Image.LANCZOS), 7)
HEAD = photo_cut((318, 8, 516, 290))
HEAD = HEAD.resize((int(HEAD.width * 0.78), int(HEAD.height * 0.78)), Image.LANCZOS)
SPOON = sticker(photo_cut((0, 118, 256, 228)).resize((512, 220), Image.LANCZOS), 7)


def fahl_doll(**pose):
    im = PD.draw("fahl", head=False, **pose)
    im.alpha_composite(HEAD, (int(PD.HIP[0] - HEAD.width / 2), int(PD.SHOULDER_Y + 4 - HEAD.height)))
    a = np.asarray(im, np.float32)
    m = a[..., 3:] > 0
    a[..., :3] = np.where(m, (a[..., :3] + DOLL_NOISE).clip(0, 255), a[..., :3])
    return PD.with_border(Image.fromarray(a.astype(np.uint8)))


# ---- US map (same projection as the Kellogg scene) with a pin on Baltimore
def us_map(width):
    topo = json.load(open(GEO))
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        arcs.append(pts)
    p1, p2, p0, l0 = map(math.radians, (29.5, 45.5, 37.5, -96))
    n = (math.sin(p1) + math.sin(p2)) / 2
    C = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    r0 = math.sqrt(C - 2 * n * math.sin(p0)) / n

    def proj(lon, lat):
        r = math.sqrt(C - 2 * n * math.sin(math.radians(lat))) / n
        th = n * (math.radians(lon) - l0)
        return r * math.sin(th), -(r0 - r * math.cos(th))

    def ring(idx):
        pts = []
        for i in idx:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(seg if not pts else seg[1:])
        return [proj(*p) for p in pts]

    states = []
    for g in topo["objects"]["states"]["geometries"]:
        if g.get("id") in ("02", "15", "60", "66", "69", "72", "78"):
            continue
        polys = [g["arcs"]] if g["type"] == "Polygon" else g["arcs"]
        states.append((g.get("id"), [ring(p[0]) for p in polys]))
    xs = [x for _, ps in states for r in ps for x, _ in r]
    ys = [y for _, ps in states for r in ps for _, y in r]
    s = width / (max(xs) - min(xs))
    tf = lambda p: ((p[0] - min(xs)) * s, (p[1] - min(ys)) * s)
    img = Image.new("RGBA", (width + 4, int((max(ys) - min(ys)) * s) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for sid, ps in states:
        for r in ps:
            d.polygon([tf(p) for p in r], fill=((246, 206, 70, 255) if sid == "24" else (240, 232, 214, 255)))
    for sid, ps in states:
        for r in ps:
            d.line([tf(p) for p in r] + [tf(r[0])], fill=(150, 140, 125, 255), width=1)
    return img, tf(proj(-76.62, 39.29))


map_img, BALT = us_map(900)
MAP = sticker(map_img, 10)
MAP_PAD = (MAP.width - map_img.width) / 2
MAP_X, MAP_Y = 600, 620


# ---- lab props
def flask_img(liquid, kind):
    im = Image.new("RGBA", (200, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    glass, line = (226, 240, 246, 255), (120, 150, 170, 255)
    if kind == "erlen":
        d.polygon([(80, 10), (120, 10), (120, 90), (190, 250), (10, 250), (80, 90)], fill=glass, outline=line)
        d.polygon([(52, 160), (148, 160), (186, 246), (14, 246)], fill=liquid + (255,))
    else:
        d.rectangle((84, 10, 116, 100), fill=glass, outline=line)
        d.ellipse((20, 80, 180, 250), fill=glass, outline=line)
        d.chord((24, 84, 176, 246), 10, 170, fill=liquid + (255,))
    d.line((92, 30, 92, 80), fill=(255, 255, 255, 255), width=5)
    return sticker(im, 6)


def clock_img():
    im = Image.new("RGBA", (230, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((5, 5, 225, 225), fill=(196, 40, 44, 255))
    d.ellipse((22, 22, 208, 208), fill=(250, 246, 236, 255))
    for k in range(12):
        a = k / 12 * math.tau
        d.line((115 + math.cos(a) * 78, 115 + math.sin(a) * 78, 115 + math.cos(a) * 92, 115 + math.sin(a) * 92), fill=INK + (255,), width=6)
    return sticker(im, 6)


def barrel_img():
    im = Image.new("RGBA", (240, 290), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 30, 220, 286), 30, fill=(40, 36, 36, 255))
    for y in (70, 250):
        d.rectangle((14, y, 226, y + 14), fill=(90, 84, 80, 255))
    d.ellipse((20, 10, 220, 60), fill=(16, 14, 14, 255))
    for x in (60, 120, 170):
        d.rounded_rectangle((x, 40, x + 18, 40 + rng.uniform(40, 90)), 9, fill=(16, 14, 14, 255))
    d.rectangle((40, 120, 200, 210), fill=(250, 244, 230, 255))
    f = font("anton", 34)
    for txt, y in (("ALCATRÃO", 132), ("DE CARVÃO", 168)):
        bb = d.textbbox((0, 0), txt, font=f)
        d.text((120 - (bb[2] - bb[0]) / 2 - bb[0], y), txt, font=f, fill=INK + (255,))
    return sticker(im, 6)


def bread_img(bitten=False):
    im = Image.new("RGBA", (180, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 10, 176, 104), fill=(196, 128, 56, 255))
    d.ellipse((16, 18, 164, 80), fill=(222, 160, 80, 255))
    for k in range(3):
        d.arc((36 + k * 40, 26, 76 + k * 40, 70), 200, 330, fill=(170, 100, 40, 255), width=5)
    if bitten:
        for k in range(3):
            d.ellipse((140 + k * 4, 6 + k * 30, 200, 46 + k * 30), fill=(0, 0, 0, 0))
    return sticker(im, 5)


def plate_img():
    im = Image.new("RGBA", (300, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, 300, 70), fill=(250, 250, 250, 255), outline=(160, 170, 190, 255), width=4)
    d.ellipse((50, 12, 250, 58), outline=(190, 200, 220, 255), width=3)
    return sticker(im, 5)


def cube_img():
    im = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(6, 16), (30, 6), (46, 16), (22, 26)], fill=(255, 255, 255, 255))
    d.polygon([(6, 16), (22, 26), (22, 46), (6, 36)], fill=(226, 228, 236, 255))
    d.polygon([(22, 26), (46, 16), (46, 36), (22, 46)], fill=(200, 204, 216, 255))
    return sticker(im, 4)


TABLE_F = table_img()
TV_S = tv_img()
TV_S = TV_S.resize((int(TV_S.width * 0.6), int(TV_S.height * 0.6)), Image.LANCZOS)
ERLEN, ROUND, CLOCK, BARREL = flask_img((90, 200, 110), "erlen"), flask_img((220, 70, 140), "round"), clock_img(), barrel_img()
BREAD, BREAD_B, PLATE, CUBE = bread_img(), bread_img(True), plate_img(), cube_img()
KERNEL = CUBE
EAT_TIMES = (21.0,)

# ---- "Mas tem um detalhe sombrio ... nasceu de uma mão suja… e de uma traição." — noir infographic style
EAT_TIMES = ()
GOLD = (236, 190, 70)
SLATE = (46, 48, 62)


def card(w, h, fill=SLATE, outline=CREAM, r=26):
    """Clean infographic card (no torn paper): rounded, thin cream outline, soft shadow."""
    pad = 30
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad + 8, pad + 12, pad + w + 8, pad + h + 12), r, fill=170)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 255))
    shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(12)))
    im.alpha_composite(shadow)
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill + (255,), outline=outline + (255,), width=4)
    return im, pad


def pill(text, size=46, fg=INK, bg=CREAM, fk="anton"):
    f = font(fk, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    w, h = bb[2] - bb[0] + 44, bb[3] - bb[1] + 26
    im, pad = card(w, h, bg, bg, r=h // 2)
    ImageDraw.Draw(im).text((pad + 22 - bb[0], pad + 13 - bb[1]), text, font=f, fill=fg + (255,))
    return im


def center_text(d, xy, text, f, col):
    bb = d.textbbox((0, 0), text, font=f)
    d.text((xy[0] - (bb[2] - bb[0]) / 2 - bb[0], xy[1] - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=col + (255,))


def avatar_card(kind, name, role):
    w, h = 300, 380
    im, pad = card(w, h)
    d = ImageDraw.Draw(im)
    cx, cy, r = pad + w / 2, pad + 130, 105
    d.ellipse((cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6), fill=CREAM + (255,))
    disc = Image.new("RGBA", (2 * r, 2 * r), (70, 72, 90, 255))
    if kind == "fahl":
        ph = HEAD.copy()
        s = 2 * r / ph.width * 1.15
        ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
        disc.alpha_composite(ph, (int(r - ph.width / 2), int(2 * r - ph.height + 40)))
    else:  # Remsen: silhouette with moustache, no verified photo here
        dd = ImageDraw.Draw(disc)
        dd.ellipse((r - 120, 2 * r - 60, r + 120, 2 * r + 160), fill=(24, 24, 30, 255))
        dd.ellipse((r - 52, 30, r + 52, 150), fill=(24, 24, 30, 255))
        dd.chord((r - 30, 108, r + 30, 132), 180, 360, fill=(110, 112, 130, 255))
        center_text(dd, (r, 80), "?", font("anton", 70), (110, 112, 130))
    m = Image.new("L", (2 * r, 2 * r), 0)
    ImageDraw.Draw(m).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    im.paste(disc, (int(cx - r), int(cy - r)), m)
    center_text(d, (cx, pad + 284), name, font("anton", 44), CREAM)
    center_text(d, (cx, pad + 336), role, font("type", 30), GOLD)
    return im


def doc_card(title, year, names):
    w, h = 360, 440
    im, pad = card(w, h, (244, 238, 222), (244, 238, 222), r=10)
    d = ImageDraw.Draw(im)
    center_text(d, (pad + w / 2, pad + 50), title, font("abril", 46), INK)
    center_text(d, (pad + w / 2, pad + 100), year, font("type", 34), RED)
    d.line((pad + 30, pad + 130, pad + w - 30, pad + 130), fill=INK + (255,), width=3)
    for k, n in enumerate(names):
        center_text(d, (pad + w / 2, pad + 168 + k * 44), n, font("type", 34), INK)
    for row in range(5):
        y = pad + 270 + row * 26
        d.rectangle((pad + 40, y, pad + w - 40 - rng.uniform(0, 60), y + 8), fill=(160, 150, 130, 255))
    return im


def cup_img():
    im = Image.new("RGBA", (330, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 230, 320, 290), fill=(240, 240, 244, 255), outline=(180, 184, 196, 255), width=4)
    d.chord((50, -40, 260, 270), 0, 180, fill=(250, 250, 252, 255), outline=(180, 184, 196, 255), width=4)
    d.rectangle((50, 110, 260, 116), fill=(250, 250, 252, 255))
    d.ellipse((50, 92, 260, 136), fill=(110, 64, 34, 255), outline=(180, 184, 196, 255), width=4)
    d.arc((236, 130, 320, 220), 270, 90, fill=(240, 240, 244, 255), width=16)
    d.rounded_rectangle((250, 40, 316, 120), 6, fill=(240, 120, 170, 255))  # sweetener sachet
    center_text(d, (283, 80), "ADO", font("anton", 22), (255, 255, 255))
    return sticker(im, 6)


def dagger_img():
    im = Image.new("RGBA", (180, 380), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(90, 0), (122, 60), (118, 230), (62, 230), (58, 60)], fill=(214, 220, 230, 255), outline=(150, 156, 170, 255))
    d.line((90, 20, 90, 220), fill=(170, 176, 190, 255), width=4)
    d.rounded_rectangle((20, 228, 160, 252), 10, fill=(196, 160, 60, 255))
    d.rounded_rectangle((72, 250, 108, 360), 12, fill=(110, 60, 30, 255))
    d.ellipse((66, 350, 114, 378), fill=(196, 160, 60, 255))
    d.polygon([(96, 120), (106, 150), (96, 166), (86, 150)], fill=RED + (255,))
    return sticker(im, 6)


def hand_icon():
    im = Image.new("RGBA", (260, 320), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sk, ln = (240, 204, 172, 255), (200, 156, 124, 255)
    for x, top in ((50, 30), (100, 6), (150, 14), (200, 44)):
        d.rounded_rectangle((x - 22, top, x + 22, 180), 22, fill=sk, outline=ln, width=3)
    d.rounded_rectangle((20, 130, 230, 310), 70, fill=sk, outline=ln, width=3)
    d.rounded_rectangle((212, 110, 258, 220), 23, fill=sk, outline=ln, width=3)
    for _ in range(14):  # green chemical smudges
        x, y = rng.uniform(40, 220), rng.uniform(60, 290)
        r_ = rng.uniform(6, 14)
        d.ellipse((x - r_, y - r_, x + r_, y + r_), fill=(110, 200, 110, 200))
    return sticker(im, 6)


def coin_img():
    im = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 58, 58), fill=GOLD + (255,), outline=(170, 120, 30, 255), width=4)
    center_text(d, (30, 31), "$", font("anton", 36), (150, 100, 20))
    return im


def cloud_rain():
    im = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x, y, r in ((80, 90, 55), (150, 70, 70), (220, 92, 52), (120, 105, 45), (190, 108, 44)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=(120, 124, 140, 255))
    return im





def _flask_stick():
    im = Image.new("RGBA", (150, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(60, 6), (90, 6), (90, 70), (144, 196), (6, 196), (60, 70)], fill=(150, 215, 245, 255))
    d.polygon([(38, 126), (112, 126), (140, 192), (10, 192)], fill=(90, 200, 110, 255))
    return sticker(im, 5)


FLASK_STICK = _flask_stick()

# ======================= ENCERRAMENTO — theatre stage: curtains, spotlight, crow centre-stage
EAT_TIMES = ()
VELVET = (150, 22, 34)
GOLD2 = (236, 190, 70)
YT_RED = (220, 30, 36)

# --- stage background: dark backdrop, warm wooden floor, spotlight pool
_bg = Image.new("RGBA", (PW, PH), (24, 16, 22, 255))
_d = ImageDraw.Draw(_bg)
for y in range(PH):
    k = y / PH
    _d.line((0, y, PW, y), fill=(int(30 + 20 * k), int(18 + 8 * k), int(26 + 6 * k), 255))
fy = OY + 900
for y in range(fy, PH):
    k = (y - fy) / (PH - fy)
    _d.line((0, y, PW, y), fill=(int(90 + 40 * k), int(56 + 22 * k), int(34 + 12 * k), 255))
for x in range(-PW, 2 * PW, 120):
    _d.line((PW / 2 + (x - PW / 2) * 0.3, fy, x, PH), fill=(70, 42, 26, 255), width=3)
_n = rng.normal(0, 5, (PH, PW, 1))
BG = Image.fromarray((np.asarray(_bg, np.float32)[..., :3] + _n).clip(0, 255).astype(np.uint8)).convert("RGBA")
yy_, xx_ = np.mgrid[0:PH, 0:PW].astype(np.float32)
spot = np.exp(-(((xx_ - OX - 960) / 560) ** 2 + ((yy_ - OY - 640) / 520) ** 2)) * 70
cone = np.clip(1 - np.abs(xx_ - OX - 960) / (60 + (yy_ - OY) * 0.42 + 1), 0, 1) * 40
SPOT = Image.new("RGBA", (PW, PH), (255, 236, 190, 255))
SPOT.putalpha(Image.fromarray((spot + cone).clip(0, 255).astype(np.uint8)))


def curtain_panel(w):
    im = Image.new("RGBA", (w, PH), (0, 0, 0, 0))
    a = np.zeros((PH, w, 4), np.float32)
    xs = np.arange(w)[None, :]
    shade = 0.62 + 0.38 * np.sin(xs / 46 * math.pi) ** 2
    for c in range(3):
        a[..., c] = VELVET[c] * shade
    a[..., 3] = 255
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    d.line((0, 0, 0, PH), fill=(60, 8, 14, 255), width=6)
    d.line((w - 3, 0, w - 3, PH), fill=(60, 8, 14, 255), width=6)
    return im


CURT = curtain_panel(PW // 2 + 80)


def valance():
    im = Image.new("RGBA", (PW, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, PW, 90), fill=(120, 14, 26, 255))
    for x in range(0, PW + 160, 160):
        d.chord((x - 80, 20, x + 80, 160), 0, 180, fill=(120, 14, 26, 255))
        d.arc((x - 80, 20, x + 80, 160), 0, 180, fill=GOLD2 + (255,), width=6)
    d.line((0, 92, PW, 92), fill=GOLD2 + (255,), width=6)
    return im


VALANCE = valance()


def curtain_open(t):
    if t < 0.15:
        return 0
    if t < 1.1:
        return ease_out((t - 0.15) / 0.95)
    if t < T_CLOSE:
        return 1
    return 1 - ease_out((t - T_CLOSE) / 1.0)


# --- icons of the next inventions (paper stickers)
def icon_canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def ic_pan():
    im = icon_canvas(260, 150); d = ImageDraw.Draw(im)
    d.rounded_rectangle((150, 62, 258, 84), 10, fill=(60, 40, 30, 255))
    d.ellipse((4, 10, 164, 140), fill=(40, 40, 46, 255)); d.ellipse((18, 22, 150, 128), fill=(70, 72, 82, 255))
    d.ellipse((50, 46, 120, 106), fill=(255, 255, 255, 255)); d.ellipse((72, 64, 100, 90), fill=(250, 190, 40, 255))
    return sticker(im, 7)


def ic_glue():
    im = icon_canvas(250, 110); d = ImageDraw.Draw(im)
    d.polygon([(10, 20), (170, 30), (170, 80), (10, 92)], fill=(236, 236, 240, 255))
    d.rectangle((40, 38, 140, 74), fill=(220, 40, 40, 255)); d.text((52, 40), "COLA", font=font("anton", 30), fill=(255, 255, 255, 255))
    d.polygon([(170, 40), (210, 50), (210, 62), (170, 72)], fill=(200, 200, 210, 255)); d.rectangle((210, 48, 244, 64), fill=(30, 30, 36, 255))
    return sticker(im, 7)


def ic_pops():
    im = icon_canvas(130, 240); d = ImageDraw.Draw(im)
    d.rounded_rectangle((52, 150, 78, 236), 10, fill=(222, 186, 130, 255))
    d.rounded_rectangle((10, 6, 120, 176), 48, fill=(226, 58, 90, 255)); d.rounded_rectangle((28, 22, 44, 130), 8, fill=(250, 150, 170, 255))
    return sticker(im, 7)


def ic_postit():
    im = icon_canvas(200, 190); d = ImageDraw.Draw(im)
    d.polygon([(4, 4), (196, 4), (196, 150), (150, 186), (4, 186)], fill=(250, 226, 90, 255))
    d.polygon([(150, 186), (196, 150), (150, 150)], fill=(220, 190, 60, 255))
    d.text((20, 40), "não", font=font("mark", 46), fill=(30, 30, 30, 255)); d.text((20, 100), "esquecer!", font=font("mark", 32), fill=(30, 30, 30, 255))
    return sticker(im, 7)


def ic_micro():
    im = icon_canvas(270, 170); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, 266, 166), 16, fill=(220, 222, 230, 255))
    d.rounded_rectangle((20, 22, 190, 148), 10, fill=(40, 44, 54, 255)); d.rounded_rectangle((34, 36, 176, 134), 8, fill=(250, 200, 90, 255))
    for k in range(3):
        d.ellipse((210, 30 + k * 42, 246, 62 + k * 42), fill=(120, 124, 136, 255))
    return sticker(im, 7)


def ic_chips():
    im = icon_canvas(200, 160); d = ImageDraw.Draw(im)
    for k, (x, y, r) in enumerate(((60, 70, 54), (130, 60, 50), (95, 105, 52))):
        d.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=(236, 186, 70, 255), outline=(190, 130, 40, 255), width=4)
        d.arc((x - r * 0.6, y - r * 0.4, x + r * 0.6, y + r * 0.4), 200, 340, fill=(250, 220, 130, 255), width=4)
    return sticker(im, 7)


def ic_petri():
    im = icon_canvas(280, 280); d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 276, 276), fill=(205, 210, 205, 255)); d.ellipse((18, 18, 262, 262), fill=(236, 214, 150, 255))
    d.ellipse((90, 100, 170, 180), fill=(96, 128, 84, 255))
    for _ in range(40):
        x, y = rng.uniform(40, 240), rng.uniform(40, 240)
        if math.hypot(x - 130, y - 140) > 75 and math.hypot(x - 140, y - 140) < 118:
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(250, 244, 222, 255))
    return sticker(im, 8)


def q_badge(im):
    out = im.copy()
    d = ImageDraw.Draw(out)
    r = 30
    cx, cy = out.width - 40, 40
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=YT_RED + (255,), outline=(255, 255, 255, 255), width=4)
    center_text(d, (cx, cy), "?", font("anton", 44), (255, 255, 255))
    return out


ICONS = [q_badge(f()) for f in (ic_pan, ic_glue, ic_pops, ic_postit, ic_micro, ic_chips)]
PETRI = ic_petri()
ICON_POS = [(330, 330), (310, 580), (440, 830), (1540, 400), (1610, 600), (1480, 800)]


def sub_button(done):
    w, h = 470, 120
    im, pad = card(w, h, ((90, 92, 104) if done else YT_RED), ((90, 92, 104) if done else YT_RED), r=60)
    d = ImageDraw.Draw(im)
    center_text(d, (pad + w / 2 + (24 if done else 0), pad + h / 2), "INSCRITO" if done else "INSCREVER-SE", font("anton", 58), (255, 255, 255))
    if done:
        x, y, s = pad + 80, pad + h / 2, 18
        d.line((x - s, y, x - s * 0.3, y + s * 0.7, x + s, y - s * 0.8), fill=(255, 255, 255, 255), width=8, joint="curve")
    return im


def bell_img():
    im = Image.new("RGBA", (200, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.pieslice((30, 20, 170, 180), 180, 360, fill=GOLD2 + (255,))
    d.rectangle((30, 98, 170, 160), fill=GOLD2 + (255,))
    d.polygon([(14, 170), (186, 170), (170, 150), (30, 150)], fill=GOLD2 + (255,))
    d.ellipse((84, 166, 116, 198), fill=(200, 150, 40, 255))
    d.ellipse((90, 6, 110, 26), fill=GOLD2 + (255,))
    return sticker(im, 7)


def cursor_img():
    im = Image.new("RGBA", (70, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(4, 4), (4, 78), (24, 60), (38, 94), (52, 88), (38, 54), (64, 54)]
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(10, 10, 10, 255))
    d.line(pts + [pts[0]], fill=(10, 10, 10, 255), width=4)
    return im


SUB_OFF, SUB_ON, BELL, CURSOR = sub_button(False), sub_button(True), bell_img(), cursor_img()
COMMENT_TXT = "qual dessas mais te surpreendeu?"

# ---- timeline (s), following the narration (text in the reply)
T_MONTAO, T_CANAL, T_ACABOU, T_NAO, T_PROX, T_INSC, T_CLICK, T_SINO, T_COMENT, T_ATE, T_FRASCO, T_CLOSE = (
    0.4, 4.1, 6.9, 8.6, 10.3, 15.8, 17.4, 18.7, 20.8, 25.3, 28.2, 30.6)

els = []
TY1 = Typed("um montão de outras coisas...", "type", 60, INK, CREAM, 960, 250, T_MONTAO + 0.4, -2, cps=22)
TY1.el.t_out = T_ACABOU - 0.1
els.append(TY1)
for k, (img, (x, y)) in enumerate(zip(ICONS, ICON_POS)):
    els.append(El(img, x, y, T_MONTAO + 0.9 + k * 0.35, rng.uniform(-10, 10), "pop", T_ACABOU - 0.1, 0.22, "tap"))
els.append(El(label("...esperando aqui no canal", "anton", 52, INK, YEL, 24, 8), 960, 370, T_CANAL + 0.2, 2, t_out=T_ACABOU - 0.1))
els.append(El(label("O VÍDEO ACABOU...", "anton", 84, CREAM, INK, 30, 10), 960, 235, T_ACABOU + 0.1, -3, t_out=T_PROX - 0.1))
letters = []
for ch in "AS CURIOSIDADES NÃO!":
    if ch == " ":
        letters.append(None)
        continue
    bg, fg, fk = STYLES[rng.integers(len(STYLES))]
    letters.append(label(ch, fk, int(rng.uniform(56, 66)), fg, bg, 10, 6))
widths = [30 if l is None else l.width - 46 for l in letters]
x = 960 - sum(widths) / 2
for k, (l, wd) in enumerate(zip(letters, widths)):
    if l is not None:
        els.append(El(l, x + wd / 2, 345 + rng.uniform(-6, 6), T_NAO + k * 0.045, rng.uniform(-9, 9), "pop", T_PROX - 0.1, 0.2, "tap"))
    x += wd
els.append(El(label("NO PRÓXIMO VÍDEO", "anton", 70, INK, YEL, 26, 8), 960, 240, T_PROX + 0.1, -2, t_out=T_INSC - 0.1))
els.append(El(PETRI, 380, 600, T_PROX + 0.5, -6, "pop", T_INSC - 0.1, 0.25, "slap"))
els.append(El(stamp("SEGREDO", 70, 330, 120), 380, 600, T_PROX + 1.0, 0, dur=0.12, sfx="stamp", t_out=T_INSC - 0.1))
COUNT_T = T_PROX + 2.0
els.append(El(label("DE VIDAS SALVAS", "type", 46, INK, CREAM), 1450, 560, COUNT_T + 1.4, 3, t_out=T_INSC - 0.1))
els.append(El(Image.new("RGBA", (1, 1)), 0, 0, 0, 0, "pop", None, 0.01, None))
TY2 = Typed(COMMENT_TXT, "type", 46, INK, (250, 250, 250), 960, 345, T_COMENT + 0.5, 0, cps=20)
TY2.el.t_out = T_ATE - 0.1
els.append(TY2)
els.append(El(label("COMENTE AQUI", "anton", 54, CREAM, INK, 22, 8), 960, 245, T_COMENT + 0.2, -2, t_out=T_ATE - 0.1))
els.append(El(label("ATÉ A PRÓXIMA!", "anton", 90, INK, YEL, 30, 10), 960, 250, T_ATE + 0.1, -3, t_out=T_CLOSE - 0.05))
els.append(El(label("cuidado com o que você derruba...", "type", 40, INK, CREAM), 960, 360, T_ATE + 1.6, 2, t_out=T_CLOSE - 0.05))

for t0, kind in ((0.15, "whoosh"), (0.2, "rustle"), (T_ACABOU, "whoosh"), (T_PROX, "hit"), (T_CLICK, "click"), (T_CLICK + 0.05, "twinkle"),
                 (T_SINO + 0.2, "bell"), (T_SINO + 1.0, "bell"), (T_ATE, "whoosh"), (T_FRASCO + 0.9, "tink"), (T_CLOSE, "rustle"),
                 (T_CLOSE, "whoosh"), (T_CLOSE + 0.6, "applause"), (T_INSC + 0.1, "slap"), (T_SINO, "slap")):
    SFX.append((t0, kind))
tk = COUNT_T
while tk < COUNT_T + 1.2:
    SFX.append((tk, "tick"))
    tk += 0.05
confetti = [dict(a=rng.uniform(0, math.tau), sp=rng.uniform(250, 600), col=[YT_RED, GOLD2, (255, 255, 255), (120, 200, 255)][k % 4],
                 rot=rng.uniform(0, 6)) for k in range(60)]


def PUNCH(t):
    if T_PROX <= t < T_PROX + 0.5:
        return 0.05 * math.sin((t - T_PROX) / 0.5 * math.pi)
    return 0


def SHAKE(t):
    if T_CLICK <= t < T_CLICK + 0.25:
        return 6 * (1 - (t - T_CLICK) / 0.25)
    return 0


def draw_front(canvas, t):
    """Curtains + valance on top of everything (they close over the crow at the end)."""
    o = curtain_open(t)
    lx = lerp(PW / 2 + 30, OX + 140, o)
    rx = lerp(PW / 2 - 30, OX + W - 140, o)
    canvas.alpha_composite(CURT, (int(lx - CURT.width), 0))
    canvas.alpha_composite(CURT.transpose(Image.FLIP_LEFT_RIGHT), (int(rx), 0))
    canvas.alpha_composite(VALANCE, (0, OY - 10))
    if t >= T_CLOSE + 0.9:
        d = ImageDraw.Draw(canvas)
        k_ = ease_back((t - T_CLOSE - 0.9) / 0.35)
        f = ImageFont.truetype(F["abril"], int(220 * max(k_, 0.05)))
        center_text(d, (PW / 2, OY + 500), "CROW", f, GOLD2)
        if t >= T_CLOSE + 1.3:
            center_text(d, (PW / 2, OY + 680), "inscreva-se  •  até a próxima", font("type", 52), CREAM)

# ------------------------------------------------------------------ crow professor
CROW = crow_prof.build(CROW_SRC, 1.0)
CROW_SCALE = 1.12
crow_cache = {}


def crow_img(level):
    if level not in crow_cache:
        im = crow_prof.frame(CROW, level / 6)
        crow_cache[level] = im.resize((int(im.width * CROW_SCALE), int(im.height * CROW_SCALE)), Image.LANCZOS)
    return crow_cache[level]


# talking envelope: syllables with pauses where the scenes change
talk = np.zeros(N)
pauses = [(0, 0.4), (3.9, 4.1), (6.6, 6.9), (10.0, 10.3), (15.5, 15.8), (20.6, 20.8), (25.0, 25.3), (30.5, DUR)]
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
# eating: a kernel flies into the beak, the beak snaps shut and chews
for te in EAT_TIMES:
    for i in range(N):
        u = i / FPS - te
        if -0.35 <= u < 0:
            talk[i] = 1.0 * ease_out((u + 0.35) / 0.2)
        elif 0 <= u < 0.6:
            talk[i] = [0.0, 0.0, 0.45, 0.45, 0.0, 0.0, 0.4, 0.4, 0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0][int(u * FPS)]
crumbs = [dict(te=te, vx=rng.uniform(-80, 60), vy=rng.uniform(-60, 40), r=rng.uniform(2.5, 5)) for te in EAT_TIMES for _ in range(10)]


def beak_mouth(t):
    k = ease_back(t / 0.4)
    img_w = int(CROW["size"][0] * CROW_SCALE)
    img_h = int(CROW["size"][1] * CROW_SCALE)
    x = OX + W - img_w + 30 + (1 - k) * 900
    y = OY + H - img_h + 60 + math.sin(t * 2.1) * 6
    return x + 70 * CROW_SCALE, y + 238 * CROW_SCALE


def draw_eating(canvas, t):
    d = ImageDraw.Draw(canvas)
    for te in EAT_TIMES:
        u = t - te
        if -0.45 <= u < 0:
            mx, my = beak_mouth(t)
            p = ease_out((u + 0.45) / 0.45)
            sx, sy = mx - 900, my - 260
            x_ = sx + (mx - sx) * p
            y_ = sy + (my - sy) * p - math.sin(p * math.pi) * 120
            im = KERNEL.rotate(u * 600, resample=Image.BILINEAR, expand=True)
            canvas.alpha_composite(im, (int(x_ - im.width / 2), int(y_ - im.height / 2)))
    for c in crumbs:
        u = t - c["te"]
        if 0 < u < 0.9:
            mx, my = beak_mouth(c["te"])
            x_ = mx + c["vx"] * u
            y_ = my + 10 + c["vy"] * u + 900 * u * u
            d.ellipse((x_ - c["r"], y_ - c["r"], x_ + c["r"], y_ + c["r"]), fill=(250, 210, 70, 255))


def draw_crow(canvas, i, t):
    k = ease_back(t / 0.4)
    img = crow_img(int(round(talk[i] * 6)))
    bob = math.sin(t * 7.0) * 1.2 * (talk[i] > 0.05)
    img = img.rotate(bob, resample=Image.BICUBIC, center=(img.width * 0.6, img.height))
    x = OX + 960 - 330 * CROW_SCALE                       # centre stage: head roughly in the middle
    y = OY + H - img.height + 40 + math.sin(t * 2.1) * 6 + (1 - k) * 900
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
    canvas.alpha_composite(SPOT)
    d = ImageDraw.Draw(canvas)
    for e in els:
        e.draw(canvas, t)
    # floating bob for the item icons is baked into their pop; add little sparkles around them
    if T_MONTAO + 1 <= t < T_ACABOU:
        for k, (x, y) in enumerate(ICON_POS):
            a = t * 2 + k
            sx, sy = OX + x + math.cos(a) * 120, OY + y + math.sin(a * 1.3) * 90
            r_ = 10 + 5 * math.sin(t * 9 + k)
            d.polygon([(sx, sy - r_), (sx + r_ / 3, sy), (sx, sy + r_), (sx - r_ / 3, sy)], fill=(255, 240, 200, 255))
            d.polygon([(sx - r_, sy), (sx, sy + r_ / 3), (sx + r_, sy), (sx, sy - r_ / 3)], fill=(255, 240, 200, 255))
    # 200.000.000 counter for the teaser
    if COUNT_T <= t < T_INSC + 0.25:
        dx = -((t - T_INSC + 0.1) / 0.3) ** 2 * 2200 if t > T_INSC - 0.1 else 0
        val = int(200_000_000 * ease_out((t - COUNT_T) / 1.2))
        s_ = f"{val:,}".replace(",", ".")
        f = font("anton", 86)
        bb = d.textbbox((0, 0), s_, font=f)
        bx, by = OX + 1450 - (bb[2] - bb[0]) / 2 + dx, OY + 420
        d.rectangle((bx - 30, by - 20, bx + bb[2] - bb[0] + 30, by + bb[3] - bb[1] + 40), fill=INK + (255,))
        d.text((bx - bb[0], by - bb[1] + 6), s_, font=f, fill=((255, 90, 80) if val == 200_000_000 else CREAM) + (255,))
    # subscribe button + cursor click + confetti
    if T_INSC <= t < T_ATE:
        k_ = ease_back((t - T_INSC) / 0.3)
        b = SUB_ON if t >= T_CLICK else SUB_OFF
        if T_CLICK <= t < T_CLICK + 0.12:
            b = b.resize((int(b.width * 0.92), int(b.height * 0.92)))
        bx, by = OX + 410, OY + 880
        bb_ = b.resize((max(1, int(b.width * k_)), max(1, int(b.height * k_)))) if k_ < 0.999 else b
        canvas.alpha_composite(bb_, (int(bx - bb_.width / 2), int(by - bb_.height / 2)))
        if T_INSC + 0.4 <= t < T_CLICK + 0.8:
            u = ease_out((t - T_INSC - 0.4) / (T_CLICK - T_INSC - 0.4))
            cx_, cy_ = lerp(bx + 500, bx + 40, u), lerp(by + 300, by + 10, u)
            canvas.alpha_composite(CURSOR, (int(cx_), int(cy_)))
        if T_CLICK <= t < T_CLICK + 1.4:
            u = t - T_CLICK
            for c in confetti:
                px = bx + math.cos(c["a"]) * c["sp"] * u
                py = by + math.sin(c["a"]) * c["sp"] * u + 500 * u * u
                a = c["rot"] + u * 8
                d.polygon([(px + math.cos(a) * 10, py + math.sin(a) * 10), (px + math.cos(a + 1.8) * 10, py + math.sin(a + 1.8) * 10),
                           (px + math.cos(a + 3.3) * 10, py + math.sin(a + 3.3) * 10)], fill=c["col"] + (255,))
    # bell ringing
    if T_SINO <= t < T_ATE:
        k_ = ease_back((t - T_SINO) / 0.3)
        ring = math.sin((t - T_SINO) * 28) * 22 * (max(0, 1 - ((t - T_SINO - 0.2) % 0.8) / 0.6)) if t > T_SINO + 0.2 else 0
        b = BELL.rotate(ring, resample=Image.BICUBIC, center=(BELL.width / 2, 20))
        if k_ < 0.999:
            b = b.resize((max(1, int(b.width * k_)), max(1, int(b.height * k_))))
        canvas.alpha_composite(b, (int(OX + 1560 - b.width / 2), int(OY + 560 - b.height / 2)))
        if t > T_SINO + 0.2:
            for k in range(3):
                r0 = 120 + k * 22
                d.arc((OX + 1560 - r0, OY + 560 - r0, OX + 1560 + r0, OY + 560 + r0), -60, -20, fill=GOLD2 + (255,), width=6)
                d.arc((OX + 1560 - r0, OY + 560 - r0, OX + 1560 + r0, OY + 560 + r0), 200, 240, fill=GOLD2 + (255,), width=6)
    # callback: a flask falls from the top and... tink (it doesn't break)
    if T_FRASCO <= t < T_CLOSE + 1.2:
        u = min(1, (t - T_FRASCO) / 0.9)
        fx, fy = OX + 420, OY + lerp(-200, 860, u * u)
        fl = flask_c((90, 200, 110), "erlen") if "flask_c" in globals() else None
        if fl is None:
            fl = FLASK_STICK
        fl = fl.rotate(lerp(0, 200 if u < 1 else 90, u), resample=Image.BICUBIC, expand=True)
        canvas.alpha_composite(fl, (int(fx - fl.width / 2), int(fy - fl.height / 2)))
        if u >= 1:
            for k in range(6):
                a = -math.pi * (0.1 + k * 0.16)
                d.line((fx, fy, fx + math.cos(a) * 46, fy + math.sin(a) * 46), fill=(255, 255, 255, 255), width=3)
    draw_crow(canvas, i, t)
    draw_front(canvas, t)
    draw_eating(canvas, t)
    # camera: slow push, kick on the stamp
    z = 1.0 + 0.045 * t / DUR + PUNCH(t)
    shake = SHAKE(t)
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
    if kind == "tink":
        n = int(0.9 * SR)
        tt_ = np.arange(n) / SR
        return 0.3 * (np.sin(2 * np.pi * 2900 * tt_) + 0.6 * np.sin(2 * np.pi * 4350 * tt_)) * np.exp(-tt_ / 0.12)
    if kind == "click":
        n = int(0.06 * SR)
        return 0.5 * band(n, 2000, 9000) * env_exp(n, 0.004) + 0.2 * thump(n, 400, 200, 0.01)
    if kind == "bell":
        n = int(1.2 * SR)
        tt_ = np.arange(n) / SR
        out = np.zeros(n)
        for k, f0 in enumerate((1320, 1760)):
            i0 = int(k * 0.16 * SR)
            m = n - i0
            tt2 = np.arange(m) / SR
            out[i0:] += (np.sin(2 * np.pi * f0 * tt2) + 0.4 * np.sin(2 * np.pi * f0 * 2.76 * tt2)) * np.exp(-tt2 / 0.35)
        return 0.16 * out
    if kind == "applause":
        n = int(3.0 * SR)
        out = np.zeros(n)
        for _ in range(420):
            i0 = int(rng.uniform(0, 2.8) * SR)
            m = int(0.02 * SR)
            out[i0:i0 + m] += band(m, 800, 7000) * env_exp(m, 0.004) * rng.uniform(0.3, 1)
        tt_ = np.arange(n) / SR
        return 0.3 * out / (np.abs(out).max() + 1e-9) * np.minimum(1, tt_ / 0.4) * np.minimum(1, (tt_[-1] - tt_) / 0.8)
    if kind == "horn":
        n = int(0.9 * SR)
        tt_ = np.arange(n) / SR
        f = np.where(tt_ < 0.45, 330 + 160 * (tt_ / 0.45), 490 - 200 * ((tt_ - 0.45) / 0.45))
        ph = 2 * np.pi * np.cumsum(f) / SR
        sq = np.tanh(3 * np.sin(ph)) + 0.4 * np.sin(2 * ph)
        return 0.13 * sq * np.minimum(1, tt_ / 0.03) * np.minimum(1, (tt_[-1] - tt_) / 0.08)
    if kind == "rip":
        n = int(0.4 * SR)
        c = (rng.random(n) > 0.5).astype(float)
        return 0.5 * band(n, 1500, 9000) * c * np.linspace(1, 0.2, n)
    if kind == "coins":
        n = int(2.4 * SR)
        out = np.zeros(n)
        for _ in range(26):
            i0 = int(rng.uniform(0, 2.2) * SR)
            m = int(0.12 * SR)
            tt_ = np.arange(m) / SR
            f0 = rng.uniform(2500, 4200)
            out[i0:i0 + m] += (np.sin(2 * np.pi * f0 * tt_) + 0.5 * np.sin(2 * np.pi * f0 * 1.5 * tt_)) * np.exp(-tt_ / 0.04)
        return 0.12 * out[:n]
    if kind == "sad":
        n = int(2.1 * SR)
        out = np.zeros(n)
        for k, (f0, dur) in enumerate(((392, 0.35), (370, 0.35), (349, 0.35), (330, 0.8))):
            i0 = int(k * 0.38 * SR)
            m = int(dur * SR)
            tt_ = np.arange(m) / SR
            f = f0 * (1 + 0.012 * np.sin(2 * np.pi * 6 * tt_)) * (np.where(tt_ > 0.3, 0.97, 1) if k == 3 else 1)
            ph = 2 * np.pi * np.cumsum(f) / SR
            out[i0:i0 + m] += (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)) * np.minimum(1, (m - np.arange(m)) / (0.05 * SR))
        return 0.13 * out
    if kind == "slurp":
        n = int(0.3 * SR)
        tt_ = np.arange(n) / SR
        x = np.linspace(0, 1, n)
        return 0.35 * (band(n, 300, 1200) * (1 - x) + band(n, 1200, 4000) * x) * np.sin(np.pi * x) * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * tt_))
    if kind == "wrong":
        n = int(0.32 * SR)
        tt_ = np.arange(n) / SR
        sq = np.sign(np.sin(2 * np.pi * np.where(tt_ < 0.14, 196, 147) * tt_))
        return 0.12 * sq * ((tt_ % 0.16) < 0.13)
    if kind == "bubble":
        n = int(1.4 * SR)
        out = np.zeros(n)
        for _ in range(16):
            i0 = int(rng.uniform(0, 1.3) * SR)
            m = int(0.05 * SR)
            tt_ = np.arange(m) / SR
            f0 = rng.uniform(350, 900)
            out[i0:i0 + m] += np.sin(2 * np.pi * (f0 + 3000 * tt_) * tt_) * np.exp(-tt_ / 0.012)
        return 0.25 * out[:n]
    if kind == "twinkle":
        n = int(0.9 * SR)
        out = np.zeros(n)
        for k, f0 in enumerate((1568, 2093, 2637, 3136)):
            i0 = int(k * 0.07 * SR)
            m = n - i0
            tt_ = np.arange(m) / SR
            out[i0:] += np.sin(2 * np.pi * f0 * tt_) * np.exp(-tt_ / 0.18)
        return 0.12 * out
    if kind == "thunder":
        n = int(1.6 * SR)
        tt_ = np.arange(n) / SR
        crack = band(n, 800, 7000) * np.exp(-tt_ / 0.05)
        rumble = band(n, 30, 300) * np.exp(-tt_ / 0.6) * (0.6 + 0.4 * np.abs(band(n, 2, 12)))
        return 0.5 * crack + 0.9 * rumble
    if kind == "step":
        n = int(0.08 * SR)
        return 0.25 * thump(n, 120, 70, 0.02) + 0.1 * band(n, 300, 2000) * env_exp(n, 0.01)
    if kind == "buzz":
        n = int(2.2 * SR)
        tt_ = np.arange(n) / SR
        f = 210 + 25 * np.sin(2 * np.pi * 3.1 * tt_) + 15 * np.sin(2 * np.pi * 7.3 * tt_)
        saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
        e = np.minimum(1, tt_ / 0.2) * np.minimum(1, (tt_[-1] - tt_) / 0.3)
        return 0.08 * saw * (0.6 + 0.4 * np.sin(2 * np.pi * 1.7 * tt_)) * e
    if kind == "roll":
        n = int(1.9 * SR)
        tt_ = np.arange(n) / SR
        speed = np.abs(np.cos(tt_ / 1.9 * 2 * np.pi * 2.5 - np.pi / 2))
        return 0.35 * band(n, 60, 500) * speed * np.minimum(1, tt_ / 0.1)
    if kind == "hit":
        n = int(0.9 * SR)
        return 0.9 * thump(n, 160, 50, 0.22) + 0.25 * band(n, 100, 1200) * env_exp(n, 0.05)
    if kind == "snap":
        n = int(0.05 * SR)
        return 0.45 * band(n, 1500, 9000) * env_exp(n, 0.004)
    if kind == "crackle":
        n = int(0.9 * SR)
        out = np.zeros(n)
        for _ in range(40):
            i0 = int(rng.uniform(0, 0.7) * SR)
            m = int(0.03 * SR)
            out[i0:i0 + m] += band(m, 1200, 8000) * env_exp(m, 0.005) * rng.uniform(0.3, 1)
        return 0.4 * out / (np.abs(out).max() + 1e-9)
    if kind == "crunch":
        n = int(0.55 * SR)
        out = np.zeros(n)
        for k, dt in enumerate((0.0, 0.05, 0.11, 0.2, 0.26, 0.37)):
            m = int(0.07 * SR)
            b = band(m, 900, 7000) * env_exp(m, 0.012) * (0.9 if k == 0 else 0.55)
            i0 = int(dt * SR)
            out[i0:i0 + m] += b[: n - i0]
        return 0.55 * out
    if kind == "strike":
        n = int(0.6 * SR)
        tt_ = np.arange(n) / SR
        scratch = band(n, 1500, 9000) * np.exp(-tt_ / 0.05) * (rng.random(n) > 0.35)
        ignite = band(n, 150, 1800) * np.clip(tt_ / 0.06, 0, 1) * np.exp(-tt_ / 0.25)
        return 0.45 * scratch + 0.55 * ignite
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
