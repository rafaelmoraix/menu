"""Crow 'professor' sticker: cut out of its red background, mortarboard + glasses,
white paper border, and a hinged lower beak so it can talk."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

MOUTH = (70, 14, 20)
HINGE = (238, 258)
# lower mandible, in source pixels: mouth line on top, beak underside below
JAW = [(20, 218), (80, 228), (140, 240), (200, 252), (238, 258), (232, 280), (200, 288), (160, 274), (110, 256), (60, 238), (24, 222)]


def load(src):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    red = a[..., 0] - np.maximum(a[..., 1], a[..., 2])
    alpha = Image.fromarray(((130 - red) / 70 * 255).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    rgba = im.convert("RGBA")
    ImageDraw.Draw(alpha).rectangle((205, 320, 236, 362), fill=0)  # artist's tick mark under the beak
    rgba.putalpha(alpha)
    return rgba


def accessories(img):
    d = ImageDraw.Draw(img)
    # glasses (one lens visible in profile) + arm back to the ear
    cx, cy, r = 292, 236, 30
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(232, 196, 110, 255), width=6)
    d.line((cx + r - 2, cy - 6, 392, cy - 18), fill=(232, 196, 110, 255), width=6)
    # mortarboard: skull cap + tilted board + tassel
    d.polygon([(338, 178), (470, 166), (476, 128), (344, 132)], fill=(22, 22, 24, 255))
    board = [(300, 118), (430, 84), (540, 112), (412, 150)]
    d.polygon([(p[0], p[1] + 12) for p in board], fill=(10, 10, 12, 255))
    d.polygon(board, fill=(30, 30, 34, 255), outline=(85, 85, 92, 255))
    d.ellipse((413, 109, 427, 121), fill=(228, 180, 60, 255))
    d.line((420, 116, 532, 116, 540, 168), fill=(228, 180, 60, 255), width=6, joint="curve")
    d.polygon([(532, 164), (548, 164), (552, 204), (528, 204)], fill=(228, 180, 60, 255))
    return img


def build(src, scale):
    base = accessories(load(src))
    # sticker border
    a = base.getchannel("A")
    border = a.point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(17)).filter(ImageFilter.GaussianBlur(1.5))
    # jaw piece and the base with the jaw area painted as open mouth
    jmask = Image.new("L", base.size, 0)
    ImageDraw.Draw(jmask).polygon(JAW, fill=255)
    jaw = Image.new("RGBA", base.size, (0, 0, 0, 0))
    jaw.paste(base, (0, 0), jmask)
    mouth_base = base.copy()
    ImageDraw.Draw(mouth_base).polygon(JAW, fill=MOUTH + (255,))
    W = (int(base.width * scale), int(base.height * scale))
    return dict(base=base, mouth_base=mouth_base, jaw=jaw, border=border, size=W, scale=scale)


def frame(asset, open_amt):
    """open_amt 0..1 -> RGBA sticker at asset scale."""
    if open_amt > 0.02:
        img = asset["mouth_base"].copy()
        ang = 9 * open_amt  # degrees, tip swings down
        jaw = asset["jaw"].rotate(ang, resample=Image.BICUBIC, center=HINGE)
        img.alpha_composite(jaw)
        a = Image.fromarray(np.maximum(np.asarray(img.getchannel("A")), np.asarray(jaw.getchannel("A"))))
        border = Image.fromarray(np.maximum(np.asarray(asset["border"]),
                                            np.asarray(jaw.getchannel("A").filter(ImageFilter.MaxFilter(17)))))
    else:
        img = asset["base"].copy()
        border = asset["border"]
    sticker = Image.new("RGBA", img.size, (246, 240, 226, 0))
    sticker.putalpha(border)
    sticker.alpha_composite(img)
    return sticker.resize(asset["size"], Image.LANCZOS)


if __name__ == "__main__":
    import sys
    a = build(sys.argv[1], 1.0)
    out = Image.new("RGBA", (1500, 760), (180, 30, 32, 255))
    out.alpha_composite(frame(a, 0), (0, 0))
    out.alpha_composite(frame(a, 1), (760, 0))
    out.convert("RGB").save(sys.argv[2])
