"""Vox-style collage on blue paper: corn → Corn Flakes, the sugar fight, Kellogg's 1906 and the recap (green TVs = real footage slots).
Crow professor talks in the corner; synthesized paper/whoosh/stamp/typewriter SFX are muxed in."""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crow_prof

CROW_SRC, OUT = sys.argv[1], sys.argv[2]
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
W, H, FPS = 1920, 1080, 30
DUR = 31.0
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
BG = (np.array([30, 72, 146], np.float32)[None, None] + tex[..., None] * np.array([0.35, 0.55, 1.0])).clip(0, 255)
BG = Image.fromarray(BG.astype(np.uint8))
bd = ImageDraw.Draw(BG, "RGBA")
for _ in range(1500):
    x, y = rng.uniform(0, PW), rng.uniform(0, PH)
    a = rng.uniform(0, math.pi)
    L = rng.uniform(5, 20)
    bd.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=(150, 190, 245, int(rng.uniform(20, 55))), width=1)
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
    shadow = Image.new("RGBA", img.size, (0, 10, 40, 255))
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
    shadow = Image.new("RGBA", big.size, (0, 10, 40, 255))
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


TRIGO, MILHO = sack_img("TRIGO", (204, 170, 120)), sack_img("MILHO", (226, 196, 110))
COB, TV, RAYS, JAR, BOLT, CLOUD, FACTORY, BOX = cob_img(), tv_img(), sunburst(), jar_img(), bolt_img(), cloud_img(), factory_img(), box_img()
FLAKES = [flake_img(k) for k in range(6)]
KERNEL = FLAKES[0]
EAT_TIMES = (2.75, 30.1)

# ---- timeline (s), following the narration
T_TRIGO_OUT, T_MILHO, T_CF, T_HIST, T_ANOS, T_JAR, T_JOHN, T_BRIGA, T_EMP, T_HOJE, T_RESUMO = (
    1.0, 1.2, 2.9, 5.3, 7.6, 8.9, 10.8, 15.6, 17.2, 20.6, 23.2)

top_els = []
top_els.append(El(TRIGO, TCX - 80, TABLE_Y - 130, 0.15, -4, "pop", T_TRIGO_OUT, 0.22, "tap"))
top_els.append(El(MILHO, TCX - 80, TABLE_Y - 130, T_MILHO, 4, t_out=T_CF - 0.05))
for k, (dx_, rot) in enumerate(((120, -20), (190, 15))):
    top_els.append(El(COB, TCX + dx_, TABLE_Y - 125, 1.6 + k * 0.18, rot, "pop", T_CF - 0.05, 0.22, "tap"))
TABLE_EL = El(TABLE, TCX, TABLE_Y + 170, 0.0, 0, "pop", T_CF - 0.05, 0.01, None)
TV1 = El(TV, 620, 520, T_CF + 0.15, -2, t_out=T_HIST - 0.1)
top_els.append(TV1)
top_els.append(El(label("CORN FLAKES", "anton", 90, INK, YEL, 30, 8), 600, 180, T_CF + 0.5, -4, t_out=T_HIST - 0.1))
SFX.append((T_CF + 0.15, "hit"))
SFX.append((T_CF + 0.2, "ding"))

HIST = Typed("mas a história não termina aí...", "type", 62, INK, CREAM, 620, 420, T_HIST + 0.15, -2, cps=24)
HIST.el.t_out = T_ANOS - 0.1
top_els.append(HIST)
SFX.append((T_HIST + 0.05, "hit"))

CAL_W, CAL_H = 300, 300
CAL_BLANK, _ = scrap(CAL_W, CAL_H, CREAM)
cd_ = ImageDraw.Draw(CAL_BLANK)
cd_.rectangle((30, 30, 30 + CAL_W, 30 + 80), fill=RED + (255,))
for x_ in (90, 150, 210, 270):
    cd_.ellipse((x_, 18, x_ + 18, 42), fill=INK + (255,))
CAL = El(CAL_BLANK, 560, 310, T_ANOS, -5, t_out=T_JOHN - 0.15)
top_els.append(CAL)
top_els.append(El(label("ANOS DEPOIS", "anton", 64, CREAM, INK, 20, 8), 570, 540, T_ANOS + 0.3, 4, t_out=T_JOHN - 0.15))
for k in range(12):
    SFX.append((T_ANOS + 0.2 + k * 0.08, "tick"))
SFX.append((T_JAR, "slap"))

top_els.append(El(stamp("NÃO!", 150, 380, 200), 330, 330, T_JOHN + 0.5, 0, dur=0.14, sfx="stamp", t_out=T_BRIGA - 0.15))
top_els.append(El(label("DOCE = FAZ MAL", "anton", 62, CREAM, RED, 22, 8), 640, 190, T_JOHN + 2.3, -3, t_out=T_BRIGA - 0.15))
SFX.append((T_BRIGA, "thunder"))
SFX.append((T_BRIGA + 0.3, "whoosh"))

top_els.append(El(FACTORY, 430, 560, T_EMP + 0.6, 0, t_out=T_HOJE - 0.1))
top_els.append(El(label("1906", "anton", 120, INK, YEL, 30, 6), 260, 230, T_EMP + 1.4, -6, t_out=T_HOJE - 0.1))
top_els.append(El(label("EMPRESA PRÓPRIA", "type", 54, INK, CREAM), 520, 880, T_EMP + 0.9, 3, t_out=T_HOJE - 0.1))
for k in range(6):
    SFX.append((T_EMP + 0.1 + k * 0.27, "step"))

TV2 = El(TV, 600, 520, T_HOJE + 0.1, 2, t_out=T_RESUMO - 0.1)
top_els.append(TV2)
top_els.append(El(label("ATÉ HOJE", "anton", 90, INK, YEL, 30, 8), 600, 180, T_HOJE + 0.6, 3, t_out=T_RESUMO - 0.1))

# recap board
POT_SMALL = POT.resize((int(POT.width * 0.8), int(POT.height * 0.8)), Image.LANCZOS)


def board_card(kind):
    img, pad = scrap(330, 300, CREAM)
    if kind == "pot":
        img.alpha_composite(POT_SMALL, (int(pad + 165 - POT_SMALL.width / 2), int(pad + 40)))
        txt = "massa esquecida"
    else:
        for k, who in enumerate(("john", "will")):
            dl = doll(who, eyes="angry", mouth="yuck", arm_l=60 if k else 8, arm_r=8 if k else 60)
            dl = dl.resize((int(dl.width * 0.36), int(dl.height * 0.36)), Image.LANCZOS)
            img.alpha_composite(dl, (int(pad + 10 + k * 150), int(pad - 10)))
        b = BOLT.resize((int(BOLT.width * 0.35), int(BOLT.height * 0.35)))
        img.alpha_composite(b, (int(pad + 165 - b.width / 2), int(pad + 40)))
        txt = "briga de irmãos"
    d = ImageDraw.Draw(img)
    f = font("mark", 38)
    bb = d.textbbox((0, 0), txt, font=f)
    d.text((pad + 165 - (bb[2] - bb[0]) / 2 - bb[0], pad + 238), txt, font=f, fill=INK + (255,))
    return img


BOARD = [(board_card("pot"), 290, 360, T_RESUMO + 3.3, -5), (board_card("briga"), 560, 720, T_RESUMO + 5.0, 4)]
for img, x, y, t0, rot in BOARD:
    top_els.append(El(img, x, y, t0, rot))
BOX_EL = El(BOX, 960, 470, T_RESUMO + 0.8, 3, dur=0.18)
top_els.append(BOX_EL)
top_els.append(El(label("o cereal mais famoso do mundo", "type", 46, INK, CREAM), 560, 120, T_RESUMO + 0.5, -2))
STRING_T = T_RESUMO + 5.6

hearts = [dict(t0=T_CF + 0.6 + k * 0.25, x=rng.choice([170, 1060]) + rng.uniform(-60, 60), vy=rng.uniform(90, 160))
          for k in range(8)]
for h_ in hearts:
    SFX.append((h_["t0"], "tap"))
smoke = [dict(t0=T_EMP + 0.9 + k * 0.35, dx=rng.uniform(-20, 20)) for k in range(30)]
rain = [dict(t0=T_RESUMO + 1.0 + rng.uniform(0, 7), x=rng.uniform(60, 1180), img=FLAKES[k % 6], spin=rng.uniform(-200, 200),
             sp=rng.uniform(260, 420)) for k in range(46)]
for te in EAT_TIMES:
    SFX.append((te - 0.45, "whoosh"))
    SFX.append((te, "crunch"))

doll_cache = {}


def doll_img(who, p):
    key = (who,) + tuple(round(v) if isinstance(v, float) else v for v in p.values())
    if key not in doll_cache:
        doll_cache[key] = doll(who, **p)
    return doll_cache[key]


def walk(p, t, speed=9):
    ph = t * speed
    p.update(leg_l=18 * math.sin(ph), leg_r=-18 * math.sin(ph))
    return -abs(math.sin(ph)) * 14


def pose_at(who, t):
    """x, vertical offset, pose dict, visible?"""
    p = dict(arm_l=8, arm_r=8, len_l=175, len_r=175, leg_l=0, leg_r=0, eyes="dot", mouth="line")
    bob, vis = 0, True
    if who == "john":
        if t < T_CF:
            x = 260
            if t > 1.6:
                p.update(eyes="happy", mouth="smile")
        elif t < T_BRIGA:
            x = 170
            if t < T_HIST:
                u = t - T_CF
                p.update(eyes="happy", mouth="smile", arm_l=150 + 10 * math.sin(u * 8), arm_r=150 - 10 * math.sin(u * 8))
            elif t >= T_JOHN:
                p.update(eyes="angry", mouth="yuck", arm_r=150, len_r=175)
                bob = -10 * max(0, 1 - (t - T_JOHN) / 0.25)
        elif t < T_EMP:
            x = lerp(170, 470, (t - T_BRIGA) / 0.3) + math.sin(t * 40) * 8
            p.update(eyes="angry", mouth="yuck", arm_l=60 + 60 * math.sin(t * 25), arm_r=60 - 60 * math.sin(t * 25))
        else:
            x = lerp(470, -320, (t - T_EMP) / 1.3)
            bob = walk(p, t)
            p.update(eyes="angry", mouth="yuck")
            vis = t < T_EMP + 1.4
    else:
        if t < T_CF:
            x = 1000
            if 0.9 < t < 2.2:
                p.update(arm_l=75)
            if t > 1.6:
                p.update(eyes="happy", mouth="smile")
        elif t < T_ANOS:
            x = 1060
            if t < T_HIST:
                u = t - T_CF
                p.update(eyes="happy", mouth="smile", arm_l=150 - 10 * math.sin(u * 8), arm_r=150 + 10 * math.sin(u * 8))
        elif t < T_BRIGA:
            x = 1000
            if T_JAR <= t < T_JOHN:
                p.update(arm_l=140, len_l=170, eyes="happy", mouth="smile")
            elif t >= T_JOHN:
                p.update(mouth="o", eyes="angry" if t > T_JOHN + 2.4 else "dot")
        elif t < T_EMP:
            x = lerp(1000, 760, (t - T_BRIGA) / 0.3) + math.sin(t * 37) * 8
            p.update(eyes="angry", mouth="yuck", arm_l=60 - 60 * math.sin(t * 23), arm_r=60 + 60 * math.sin(t * 23))
        elif t < T_RESUMO:
            if t < T_EMP + 1.0:
                x = lerp(760, 950, (t - T_EMP) / 1.0)
                bob = walk(p, t)
            else:
                x = 950 if t < T_HOJE else 1060
                p.update(eyes="happy", mouth="smile", arm_l=120)
        else:
            x = 1060
            bob = (ease_out((t - T_RESUMO) / 0.35)) * 900
            vis = t < T_RESUMO + 0.4
    return x, bob, p, vis


def PUNCH(t):
    for t0, t1, amt in ((T_BRIGA, T_EMP, 0.07),):
        if t0 <= t < t1:
            return amt * ease_out((t - t0) / 0.15)
        if t1 <= t < t1 + 0.3:
            return amt * (1 - ease_out((t - t1) / 0.3))
    return 0


def SHAKE(t):
    s = 0
    for t0, amp, ln in ((T_CF + 0.15, 9, 0.3), (T_JOHN + 0.5, 12, 0.35), (T_BRIGA, 10, 1.4), (T_RESUMO + 0.8, 8, 0.3)):
        if t0 <= t < t0 + ln:
            s = max(s, amp * (1 - (t - t0) / ln))
    return s

HEART_IMG = heart_img()
els = []

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
pauses = [(0, 0.2), (2.6, 3.0), (5.1, 5.4), (7.3, 7.7), (10.6, 10.9), (15.4, 15.7), (17.0, 17.3), (20.4, 20.7), (23.0, 23.3), (29.6, DUR)]
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
    # ---- background moods: darker for the suspense line, red flashes during the fight
    if T_HIST <= t < T_ANOS + 0.3:
        k_ = min(1, (t - T_HIST) / 0.3) * (1 - max(0, (t - T_ANOS) / 0.3))
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (5, 10, 30, int(130 * k_))))
    if T_BRIGA <= t < T_EMP:
        fl_ = 0.5 + 0.5 * math.sin((t - T_BRIGA) * 22)
        canvas.alpha_composite(Image.new("RGBA", canvas.size, (200, 20, 30, int(90 * fl_))))
    # sunburst behind the TVs and the cereal box
    for t0, t1, cx0 in ((T_CF, T_HIST, 620), (T_HOJE, T_RESUMO, 600), (T_RESUMO + 0.7, 99, 960)):
        if t0 <= t < t1:
            k_ = min(1, (t - t0) / 0.4)
            r_ = RAYS.rotate((t - t0) * 12, resample=Image.BILINEAR)
            if k_ < 1:
                r_.putalpha(r_.getchannel("A").point(lambda v: int(v * k_)))
            canvas.alpha_composite(r_, (int(OX + cx0 - r_.width / 2), int(OY + 520 - r_.height / 2)))
    if t < T_CF + 0.3:
        TABLE_EL.draw(canvas, t)
    # brothers
    for who in ("john", "will"):
        x, bob, p, vis = pose_at(who, t)
        if vis:
            im = doll_img(who, p)
            canvas.alpha_composite(im, (int(OX + x - im.width / 2), int(OY + FEET_Y - im.height + 70 + bob)))
    # sugar jar in Will's raised hand
    if T_JAR <= t < T_JOHN + 0.3:
        x, bob, p, vis = pose_at("will", min(t, T_JOHN - 0.01))
        hx_ = x - 78 - math.sin(math.radians(140)) * 170
        hy_ = FEET_Y + 70 - PD.CH + PD.SHOULDER_Y + math.cos(math.radians(140)) * 170
        k_ = ease_back((t - T_JAR) / 0.25)
        dx = -((t - T_JOHN) / 0.3) ** 2 * 2200 if t > T_JOHN else 0
        jim = JAR if k_ >= 0.999 else JAR.resize((max(1, int(JAR.width * k_)), max(1, int(JAR.height * k_))))
        canvas.alpha_composite(jim, (int(OX + hx_ - jim.width / 2 + dx), int(OY + hy_ - jim.height + 30)))
        d = ImageDraw.Draw(canvas)
        for k in range(5):  # sparkles
            a = t * 3 + k * 1.3
            sx, sy = OX + hx_ + math.cos(a) * 110 + dx, OY + hy_ - 110 + math.sin(a * 1.3) * 80
            r_ = 10 + 6 * math.sin(t * 9 + k)
            d.polygon([(sx, sy - r_), (sx + r_ / 3, sy), (sx, sy + r_), (sx - r_ / 3, sy)], fill=(255, 255, 255, 255))
            d.polygon([(sx - r_, sy), (sx, sy + r_ / 3), (sx + r_, sy), (sx, sy - r_ / 3)], fill=(255, 255, 255, 255))
    # fight: dust cloud + lightning
    if T_BRIGA + 0.25 <= t < T_EMP:
        k_ = ease_back((t - T_BRIGA - 0.25) / 0.2)
        c_ = CLOUD.rotate(math.sin(t * 30) * 4, resample=Image.BILINEAR)
        c_ = c_.resize((max(1, int(c_.width * k_)), max(1, int(c_.height * k_))), Image.BILINEAR)
        canvas.alpha_composite(c_, (int(OX + 615 - c_.width / 2 + math.sin(t * 50) * 6), int(OY + 640 - c_.height / 2)))
        if int(t * 8) % 2 == 0:
            canvas.alpha_composite(BOLT, (int(OX + 615 - BOLT.width / 2), int(OY + 90)))
    # hearts around the celebrating brothers
    for h_ in hearts:
        u = t - h_["t0"]
        if 0 < u < 1.4:
            hy_ = OY + 420 - h_["vy"] * u
            k_ = min(1, u / 0.15) * (1 - max(0, (u - 1.0) / 0.4))
            im = HEART_IMG.resize((max(1, int(HEART_IMG.width * k_)), max(1, int(HEART_IMG.height * k_))))
            canvas.alpha_composite(im, (int(OX + h_["x"] - im.width / 2 + math.sin(u * 6) * 14), int(hy_)))
    # chimney smoke
    d = ImageDraw.Draw(canvas)
    for s_ in smoke:
        u = t - s_["t0"]
        if 0 < u < 2.2 and t < T_HOJE:
            r_ = 18 + u * 26
            sx, sy = OX + 430 - 310 + 500 + s_["dx"] + u * 40, OY + 560 - 210 + 20 - u * 120
            d.ellipse((sx - r_, sy - r_, sx + r_, sy + r_), fill=(236, 232, 226, int(220 * (1 - u / 2.2))))
    for e in top_els:
        e.draw(canvas, t)
    # calendar years flipping 1895 → 1906
    if T_ANOS + 0.15 <= t < T_JOHN + 0.15:
        yr = 1895 + min(11, int((t - T_ANOS - 0.15) / 0.08))
        dx = -((t - T_JOHN + 0.15) / 0.3) ** 2 * 2200 if t > T_JOHN - 0.15 else 0
        d = ImageDraw.Draw(canvas)
        f = font("anton", 110)
        s_ = str(yr)
        bb = d.textbbox((0, 0), s_, font=f)
        d.text((OX + 560 - (bb[2] - bb[0]) / 2 - bb[0] + dx, OY + 340 - (bb[3] - bb[1]) / 2 - bb[1]), s_, font=f,
               fill=(RED if yr == 1906 else INK) + (255,))
    # red strings on the recap board, and flakes raining
    if t >= STRING_T:
        d = ImageDraw.Draw(canvas)
        u = ease_out((t - STRING_T) / 0.6)
        for (_, x, y, _, _) in BOARD:
            p0 = (OX + x, OY + y - 150)
            p1 = (OX + 960, OY + 260)
            d.line((p0, (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)), fill=RED + (255,), width=7)
            d.ellipse((p0[0] - 16, p0[1] - 16, p0[0] + 16, p0[1] + 16), fill=RED + (255,), outline=(120, 20, 20, 255), width=3)
        d.ellipse((OX + 944, OY + 244, OX + 976, OY + 276), fill=RED + (255,), outline=(120, 20, 20, 255), width=3)
    for r_ in rain:
        u = t - r_["t0"]
        if 0 < u < 4:
            y_ = OY - 60 + r_["sp"] * u
            im = r_["img"].rotate(r_["spin"] * u, resample=Image.BILINEAR, expand=True)
            canvas.alpha_composite(im, (int(OX + r_["x"] - im.width / 2), int(y_)))
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
