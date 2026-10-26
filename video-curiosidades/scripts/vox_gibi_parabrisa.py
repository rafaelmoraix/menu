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
DUR = 18.5
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

# ---- #7 PARA-BRISA (comic / pop-art look): "Em 1903, na França ... mas isso não aconteceu."
EAT_TIMES = ()
BLACK = (18, 16, 18)
WHITE = (255, 255, 255)
YEL2 = (255, 214, 40)
CYAN = (150, 220, 240)
BANG = f"{FD}/Bangers.ttf"
WORLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo", "world", "package", "countries-110m.json")

# --- pop-art background: warm yellow-orange with halftone dots growing toward the edges
_bg = Image.new("RGBA", (PW, PH), (252, 176, 44, 255))
_d = ImageDraw.Draw(_bg)
for y in range(0, PH, 24):
    for x in range((y // 24 % 2) * 12, PW, 24):
        dist = math.hypot((x - PW / 2) / (PW / 2), (y - PH / 2) / (PH / 2))
        r_ = 2 + 7 * min(1, dist) ** 1.4
        _d.ellipse((x - r_, y - r_, x + r_, y + r_), fill=(240, 134, 30, 255))
_n = rng.normal(0, 5, (PH, PW, 1))
BG = Image.fromarray((np.asarray(_bg, np.float32)[..., :3] + _n).clip(0, 255).astype(np.uint8)).convert("RGBA")


def ink(img, r=6):
    """Comic look: thick black outline instead of the paper border."""
    return sticker(img, r, BLACK)


def comic_text(text, size, fill=YEL2, stroke=10, shadow=True):
    f = ImageFont.truetype(BANG, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f, stroke_width=stroke)
    w, h = bb[2] - bb[0] + 30, bb[3] - bb[1] + 30
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        d.text((15 - bb[0] + 8, 15 - bb[1] + 8), text, font=f, fill=BLACK + (255,), stroke_width=stroke, stroke_fill=BLACK + (255,))
    d.text((15 - bb[0], 15 - bb[1]), text, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=BLACK + (255,))
    return im


def burst(r_out, r_in, n, fill, seed=0):
    rr = np.random.default_rng(seed)
    s = int(r_out * 2 + 40)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    pts = []
    for k in range(2 * n):
        a = k / (2 * n) * math.tau
        r_ = (r_out * rr.uniform(0.85, 1.05)) if k % 2 == 0 else r_in
        pts.append((c + math.cos(a) * r_, c + math.sin(a) * r_))
    d.polygon([(c + (x - c) * 1.06, c + (y - c) * 1.06) for x, y in pts], fill=BLACK + (255,))
    d.polygon(pts, fill=fill + (255,))
    return im


def caption(text, size=46):
    """Rectangular comic narration box."""
    f = ImageFont.truetype(BANG, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    w, h = bb[2] - bb[0] + 44, bb[3] - bb[1] + 30
    im = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((10, 10, w + 10, h + 10), fill=BLACK + (255,))
    d.rectangle((0, 0, w, h), fill=(255, 246, 200, 255), outline=BLACK + (255,), width=5)
    d.text((22 - bb[0], 15 - bb[1]), text, font=f, fill=BLACK + (255,))
    return im


def speech(text, size=60, tail="left"):
    f = ImageFont.truetype(BANG, size)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=f)
    w, h = bb[2] - bb[0] + 90, bb[3] - bb[1] + 70
    im = Image.new("RGBA", (w + 20, h + 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tx = 50 if tail == "left" else w - 50
    d.polygon([(tx - 20, h - 12), (tx + 22, h - 12), (tx - 30 if tail == "left" else tx + 30, h + 60)], fill=BLACK + (255,))
    d.ellipse((0, 0, w, h), fill=BLACK + (255,))
    d.ellipse((7, 7, w - 7, h - 7), fill=WHITE + (255,))
    d.polygon([(tx - 13, h - 18), (tx + 15, h - 18), (tx - 24 if tail == "left" else tx + 24, h + 46)], fill=WHITE + (255,))
    d.text((w / 2 - (bb[2] - bb[0]) / 2 - bb[0], h / 2 - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=BLACK + (255,))
    return im


def france_map(width):
    topo = json.load(open(WORLD))
    tr = topo["transform"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * tr["scale"][0] + tr["translate"][0], y * tr["scale"][1] + tr["translate"][1]))
        arcs.append(pts)
    g = [g for g in topo["objects"]["countries"]["geometries"] if g.get("id") == "250"][0]
    rings = []
    for poly in g["arcs"]:
        pts = []
        for i in poly[0]:
            seg = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(seg if not pts else seg[1:])
        lon_c = sum(p[0] for p in pts) / len(pts)
        if -6 < lon_c < 10 and 40 < sum(p[1] for p in pts) / len(pts) < 52:  # mainland + Corsica only
            rings.append(pts)
    k = math.cos(math.radians(46))
    xs = [p[0] * k for r in rings for p in r]
    ys = [-p[1] for r in rings for p in r]
    s = width / (max(xs) - min(xs))
    tf = lambda p: ((p[0] * k - min(xs)) * s + 10, (-p[1] - min(ys)) * s + 10)
    im = Image.new("RGBA", (width + 20, int((max(ys) - min(ys)) * s) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for r in rings:
        d.polygon([tf(p) for p in r], fill=(80, 140, 230, 255))
    for x in range(0, im.width, 14):  # halftone shading on the map
        for y in range(0, im.height, 14):
            if im.getpixel((x, y))[3] and (x + y) % 28 == 0:
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(60, 110, 200, 255))
    return ink(im, 7), tf((2.35, 48.86))


def flask_c(liquid, kind):
    im = Image.new("RGBA", (150, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "erlen":
        d.polygon([(60, 6), (90, 6), (90, 70), (144, 196), (6, 196), (60, 70)], fill=CYAN + (255,))
        d.polygon([(38, 126), (112, 126), (140, 192), (10, 192)], fill=liquid + (255,))
    else:
        d.rectangle((62, 6, 88, 80), fill=CYAN + (255,))
        d.ellipse((14, 60, 136, 196), fill=CYAN + (255,))
        d.chord((18, 64, 132, 192), 10, 170, fill=liquid + (255,))
    d.line((70, 20, 70, 64), fill=WHITE + (255,), width=5)
    return ink(im, 5)


def shelf_img():
    im = Image.new("RGBA", (560, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 560, 26), fill=(150, 96, 52, 255))
    for x in (40, 500):
        d.polygon([(x, 26), (x + 20, 26), (x + 20, 68), (x - 20, 26)], fill=(120, 76, 40, 255))
    return ink(im, 5)


def floor_img():
    im = Image.new("RGBA", (PW, 140), (176, 110, 60, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, PW, 160):
        d.line((x, 0, x, 140), fill=(140, 84, 44, 255), width=4)
    d.line((0, 2, PW, 2), fill=BLACK + (255,), width=6)
    return im


def bened(**pose):
    return PD.with_border(PD.draw("bened", **pose), 6, BLACK)


MAP_FR, PARIS = france_map(560)
FLASKS_C = [flask_c(c, k) for c, k in (((90, 200, 110), "erlen"), ((220, 70, 140), "round"), ((255, 170, 40), "erlen"),
                                       ((150, 90, 230), "round"))]
SHELF, FLOOR = shelf_img(), floor_img()
TITLE_BURST = burst(330, 240, 18, (230, 40, 40), 1)
TITLE7 = comic_text("#7", 260, YEL2, 14)
TITLE_TXT = comic_text("PARA-BRISA", 150, WHITE, 12)
CRASH = comic_text("CRASH!!", 120, (250, 80, 40), 10)
NADA = comic_text("...NADA?!", 150, YEL2, 12)

# ---- timeline (s)
T_TITLE, T_FR, T_PIN, T_BEN, T_LAB, T_BUMP, T_FALL, T_FREEZE, T_ESP, T_POP, T_LAND = (
    0.05, 1.8, 2.5, 3.7, 6.1, 8.8, 9.0, 11.4, 11.6, 15.1, 15.3)
SHELF_X, SHELF_Y = 780, 400
FLASK_X = [600, 700, 820, 930]
DOLL_X = 640
LAND = (910, 985)

els = []
els.append(El(TITLE_BURST, 600, 520, T_TITLE, 0, "pop", T_FR - 0.1, 0.25, "hit"))
els.append(El(TITLE7, 600, 430, T_TITLE + 0.15, -6, "pop", T_FR - 0.1, 0.22, "slap"))
els.append(El(TITLE_TXT, 600, 640, T_TITLE + 0.4, 3, "pop", T_FR - 0.1, 0.22, "slap"))
els.append(El(caption("1903 • FRANÇA", 56), 280, 110, T_FR, -2, "pop", T_BEN - 0.1, 0.2, "tap"))
els.append(El(MAP_FR, 620, 580, T_FR + 0.2, 0, "pop", T_BEN - 0.1, 0.25, "slap"))
els.append(El(burst(110, 80, 12, YEL2, 3), 360, 320, T_FR + 0.35, 0, "pop", T_BEN - 0.1, 0.2, None))
els.append(El(comic_text("1903", 80, (230, 40, 40), 8, False), 360, 320, T_FR + 0.4, -8, "pop", T_BEN - 0.1, 0.2, "tap"))
SFX.append((T_PIN, "tap"))
els.append(El(caption("ÉDOUARD BÉNÉDICTUS", 60), 640, 110, T_BEN + 0.3, -2, "pop", T_LAB - 0.1, 0.2, "slap"))
els.append(El(caption("químico (e artista!)", 44), 700, 210, T_BEN + 0.8, 2, "pop", T_LAB - 0.1, 0.2, "tap"))
els.append(El(caption("arrumando o laboratório...", 46), 420, 110, T_LAB + 0.2, -2, "pop", T_FALL, 0.2, "tap"))
els.append(El(speech("OPS!", 80, "left"), 380, 330, T_BUMP + 0.15, -4, "pop", T_FREEZE, 0.2, "tap"))
els.append(El(caption("em câmera lenta...", 44), 1000, 110, T_FALL + 0.4, 2, "pop", T_ESP, 0.2, None))
els.append(El(NADA, 600, 170, T_LAND + 0.35, -4, "pop", None, 0.25, "hit"))
SFX.append((T_BUMP, "tap"))
SFX.append((T_FALL, "whoosh"))
SFX.append((T_ESP, "tension"))
SFX.append((T_POP, "tap"))
SFX.append((T_LAND, "tink"))
for k in range(5):
    SFX.append((T_BEN + 0.05 + k * 0.25, "step"))
shards = [dict(a=rng.uniform(0, math.tau), sp=rng.uniform(80, 220), rot=rng.uniform(-400, 400), s=rng.uniform(10, 26))
          for _ in range(26)]
cracks = []
for k in range(7):
    a = rng.uniform(0, math.tau)
    pts = [(0, 0)]
    for j in range(3):
        a += rng.uniform(-0.5, 0.5)
        pts.append((pts[-1][0] + math.cos(a) * 18, pts[-1][1] + math.sin(a) * 18))
    cracks.append(pts)


def flask_fall(t):
    """Position/rotation of the knocked flask (index 2)."""
    x0, y0 = FLASK_X[2], SHELF_Y - 90
    if t < T_FALL:
        wob = math.sin((t - T_BUMP) * 40) * 8 * max(0, 1 - (t - T_BUMP) / 0.2) if t >= T_BUMP else 0
        return x0, y0, wob
    if t < T_FREEZE:
        u = (t - T_FALL) / (T_FREEZE - T_FALL)
        return lerp(x0, LAND[0], u), lerp(y0, LAND[1] - 60, u ** 1.6), 200 * u
    if t < T_LAND:
        return LAND[0], LAND[1] - 60, 200   # frozen in the air
    u = min(1, (t - T_LAND) / 0.12)
    return LAND[0], lerp(LAND[1] - 60, LAND[1], u), lerp(200, 270, u)


def bened_pose(t):
    p = dict(arm_l=8, arm_r=8, len_l=175, len_r=175, leg_l=0, leg_r=0, eyes="dot", mouth="line")
    bob, x = 0, DOLL_X
    if t < T_BEN:
        return None
    if t < T_BEN + 1.3:
        u = (t - T_BEN) / 1.3
        x = lerp(-250, 420, ease_out(u))
        ph = t * 9
        p.update(leg_l=18 * math.sin(ph), leg_r=-18 * math.sin(ph), arm_l=8 - 14 * math.sin(ph), arm_r=8 + 14 * math.sin(ph))
        bob = -abs(math.sin(ph)) * 14
    elif t < T_LAB:
        x = 420
        p.update(mouth="smile", arm_l=60)
    else:
        x = lerp(420, DOLL_X, (t - T_LAB) / 0.5)
        if t < T_BUMP:
            p.update(arm_r=176, len_r=262 + 8 * math.sin(t * 6))
        elif t < T_FALL + 0.4:
            u = (t - T_BUMP) / 0.25
            p.update(arm_r=lerp(176, 150, u), len_r=265, mouth="o")
        elif t < T_ESP:
            p.update(eyes="wide", mouth="o", arm_l=40, arm_r=40)
        elif t < T_LAND:
            p.update(eyes="happy", mouth="o", arm_l=168, arm_r=168, len_l=118, len_r=118)   # covering the ears
            bob = math.sin(t * 30) * 3
        else:
            p.update(eyes="wide", mouth="o", arm_l=25, arm_r=25)
    return x, bob, p


bened_cache = {}


def bened_img(p):
    key = tuple(round(v) if isinstance(v, float) else v for v in p.values())
    if key not in bened_cache:
        bened_cache[key] = bened(**p)
    return bened_cache[key]


def PUNCH(t):
    if T_ESP <= t < T_POP:
        return 0.06 * ease_out((t - T_ESP) / 3.4)
    if T_POP <= t < T_POP + 0.3:
        return 0.06 * (1 - ease_out((t - T_POP) / 0.3))
    if t < 0.4:
        return 0.08 * (1 - ease_out(t / 0.4))
    return 0


def SHAKE(t):
    s = 0
    for t0, amp, ln in ((T_TITLE, 10, 0.35), (T_BUMP, 6, 0.25), (T_LAND + 0.35, 9, 0.35)):
        if t0 <= t < t0 + ln:
            s = max(s, amp * (1 - (t - t0) / ln))
    if T_ESP + 2.0 <= t < T_POP:
        s = max(s, 3 * (t - T_ESP - 2.0))  # tension builds
    return s

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
pauses = [(0, 0.2), (1.6, 1.8), (3.5, 3.7), (5.9, 6.1), (11.4, 11.6), (15.0, 15.2), (16.8, DUR)]
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
    d = ImageDraw.Draw(canvas)
    # radial speed lines on the title and on the "nada" reveal
    for t0, t1 in ((T_TITLE, T_FR - 0.1), (T_LAND + 0.3, T_LAND + 1.2)):
        if t0 <= t < t1:
            for k in range(40):
                a = k / 40 * math.tau + t * 0.3
                r0 = 330 + 40 * math.sin(k * 7.1 + t * 9)
                d.line((OX + 600 + math.cos(a) * r0, OY + 520 + math.sin(a) * r0 * 0.75,
                        OX + 600 + math.cos(a) * 1300, OY + 520 + math.sin(a) * 1000), fill=(255, 238, 170, 255), width=5)
    if t >= T_BEN:
        canvas.alpha_composite(FLOOR, (0, OY + 1000))
    for e in els:
        e.draw(canvas, t)
    # Paris pin
    if T_PIN <= t < T_BEN:
        px = OX + 620 - MAP_FR.width / 2 + 31 + PARIS[0]
        py = OY + 580 - MAP_FR.height / 2 + 31 + PARIS[1]
        drop = ease_back((t - T_PIN) / 0.3)
        ty_ = py - (1 - drop) * 400
        d.polygon([(px, ty_), (px - 22, ty_ - 44), (px + 22, ty_ - 44)], fill=BLACK + (255,))
        d.ellipse((px - 32, ty_ - 94, px + 32, ty_ - 30), fill=BLACK + (255,))
        d.ellipse((px - 25, ty_ - 87, px + 25, ty_ - 37), fill=(230, 40, 40, 255))
        if t > T_PIN + 0.3:
            f = ImageFont.truetype(BANG, 54)
            d.text((px + 40, ty_ - 90), "PARIS", font=f, fill=WHITE + (255,), stroke_width=6, stroke_fill=BLACK + (255,))
    # lab shelf + flasks
    if t >= T_LAB:
        k_ = ease_back((t - T_LAB) / 0.3)
        canvas.alpha_composite(SHELF, (int(OX + SHELF_X - SHELF.width / 2), int(OY + SHELF_Y - (1 - k_) * 500)))
        for k, fim in enumerate(FLASKS_C):
            if k == 2:
                continue
            canvas.alpha_composite(fim, (int(OX + FLASK_X[k] - fim.width / 2), int(OY + SHELF_Y - fim.height + 14 - (1 - k_) * 500)))
    # Bénédictus
    st = bened_pose(t)
    if st:
        x, bob, p = st
        im = bened_img(p)
        canvas.alpha_composite(im, (int(OX + x - im.width / 2), int(OY + FEET_Y - im.height + 70 + bob)))
    # the falling flask (+ motion lines)
    if t >= T_LAB:
        fx, fy, rot = flask_fall(t)
        if t < T_LAB + 0.3:
            fy -= (1 - ease_back((t - T_LAB) / 0.3)) * 500
        fim = FLASKS_C[2].rotate(-rot, resample=Image.BICUBIC, expand=True)
        canvas.alpha_composite(fim, (int(OX + fx - fim.width / 2), int(OY + fy - fim.height / 2)))
        if T_FALL <= t < T_FREEZE:
            for k in range(4):
                d.line((OX + fx - 60 + k * 30, OY + fy - 90 - k * 8, OX + fx - 80 + k * 30, OY + fy - 170 - k * 8),
                       fill=BLACK + (255,), width=5)
        if t >= T_LAND + 0.05:  # cracks spread, but nothing flies
            u = min(1, (t - T_LAND - 0.05) / 0.35)
            for c in cracks:
                n = max(2, int(len(c) * u) + 1)
                d.line([(OX + fx + x_ * 1.6, OY + fy + y_ * 1.6) for x_, y_ in c[:n]], fill=WHITE + (255,), width=4)
    # thought bubble: what he EXPECTED (glass exploding)
    if T_ESP + 0.1 <= t < T_POP + 0.15:
        k_ = ease_back((t - T_ESP - 0.1) / 0.3)
        if t >= T_POP:
            k_ = 1 + (t - T_POP) / 0.15 * 0.4
        bx, by = OX + 960, OY + 330
        al = 255 if t < T_POP else int(255 * (1 - (t - T_POP) / 0.15))
        for cx_, cy_, r_ in ((DOLL_X + 120, 390, 14), (DOLL_X + 170, 360, 22)):
            d.ellipse((OX + cx_ - r_ - 5, OY + cy_ - r_ - 5, OX + cx_ + r_ + 5, OY + cy_ + r_ + 5), fill=BLACK + (al,))
            d.ellipse((OX + cx_ - r_, OY + cy_ - r_, OX + cx_ + r_, OY + cy_ + r_), fill=WHITE + (al,))
        for (dx, dy, r_) in ((-120, 0, 120), (0, -40, 140), (120, 0, 120), (0, 60, 110), (-60, 50, 100), (70, 50, 100)):
            rr = r_ * k_
            d.ellipse((bx + dx * k_ - rr - 7, by + dy * k_ - rr - 7, bx + dx * k_ + rr + 7, by + dy * k_ + rr + 7), fill=BLACK + (al,))
        for (dx, dy, r_) in ((-120, 0, 120), (0, -40, 140), (120, 0, 120), (0, 60, 110), (-60, 50, 100), (70, 50, 100)):
            rr = r_ * k_
            d.ellipse((bx + dx * k_ - rr, by + dy * k_ - rr, bx + dx * k_ + rr, by + dy * k_ + rr), fill=WHITE + (al,))
        if t < T_POP:
            u = ((t - T_ESP) % 1.1) / 1.1
            for s_ in shards:
                sx = bx + math.cos(s_["a"]) * s_["sp"] * u
                sy = by + 20 + math.sin(s_["a"]) * s_["sp"] * u * 0.7
                a2 = math.radians(s_["rot"] * u)
                r_ = s_["s"]
                tri = [(sx + math.cos(a2 + q) * r_, sy + math.sin(a2 + q) * r_) for q in (0, 2.3, 4.0)]
                d.polygon(tri, fill=CYAN + (255,), outline=BLACK + (255,))
            cr = CRASH.rotate(math.sin(t * 25) * 4, resample=Image.BILINEAR, expand=True)
            canvas.alpha_composite(cr, (int(bx - cr.width / 2), int(by - 40 - cr.height / 2)))
    # comic panel border (the crow breaks out of it)
    d.rectangle((OX + 18, OY + 18, OX + W - 18, OY + H - 18), outline=BLACK + (255,), width=14)
    draw_crow(canvas, i, t)
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
    if kind == "tension":
        n = int(3.6 * SR)
        tt_ = np.arange(n) / SR
        f = 90 + 140 * (tt_ / tt_[-1]) ** 2
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = np.sin(ph) + 0.5 * np.sin(2.01 * ph) + 0.3 * band(n, 100, 900)
        return 0.22 * tone * (tt_ / tt_[-1]) ** 1.5
    if kind == "tink":
        n = int(0.9 * SR)
        tt_ = np.arange(n) / SR
        return 0.3 * (np.sin(2 * np.pi * 2900 * tt_) + 0.6 * np.sin(2 * np.pi * 4350 * tt_) + 0.3 * np.sin(2 * np.pi * 6100 * tt_)) * np.exp(-tt_ / 0.12)
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
