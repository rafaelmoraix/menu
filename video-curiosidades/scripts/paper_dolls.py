"""Paper-doll versions of the Kellogg brothers, posable per frame.
John: white suit, white hair + goatee, round glasses, black bow tie.
Will: brown suit, bowler hat, brown moustache, red tie."""
import math
from PIL import Image, ImageDraw, ImageFilter

CW, CH = 440, 780
HIP = (220, 520)
SHOULDER_Y = 345
SKIN = (240, 204, 172)
INK = (24, 20, 20)

LOOK = {
    "john": dict(suit=(238, 234, 224), suit_line=(150, 144, 132), trousers=(226, 222, 210), hair=(246, 246, 246),
                 tie="bow", tie_col=(20, 20, 22), hat=None, beard=(246, 246, 246), stache=(246, 246, 246)),
    "will": dict(suit=(92, 64, 48), suit_line=(50, 34, 26), trousers=(74, 52, 40), hair=(70, 46, 30),
                 tie="long", tie_col=(186, 36, 40), hat="bowler", beard=None, stache=(80, 52, 34)),
    "bened": dict(suit=(54, 70, 120), suit_line=(24, 30, 60), trousers=(44, 56, 96), hair=(52, 36, 28),
                  tie="bow", tie_col=(200, 36, 40), hat="beret", beard=None, stache=(52, 36, 28)),
    "fahl": dict(suit=(50, 48, 54), suit_line=(18, 18, 22), trousers=(42, 40, 46), hair=(60, 50, 40),
                 tie="bow", tie_col=(236, 234, 228), hat=None, beard=None, stache=None),
}


def _limb(d, x0, y0, ang, length, width, col, end_col, end_r, side):
    a = math.radians(ang)
    x1 = x0 + side * math.sin(a) * length
    y1 = y0 + math.cos(a) * length
    d.line((x0, y0, x1, y1), fill=col, width=width)
    r = width / 2
    d.ellipse((x0 - r, y0 - r, x0 + r, y0 + r), fill=col)
    d.ellipse((x1 - end_r, y1 - end_r, x1 + end_r, y1 + end_r), fill=end_col)
    return x1, y1


def draw(kind, arm_l=8, arm_r=8, len_l=175, len_r=175, leg_l=0, leg_r=0, eyes="dot", mouth="line", head=True):
    """Angles in degrees: 0 = hanging down, 90 = straight out sideways, 180 = straight up.
    Returns an RGBA cutout (no border yet) with feet at the bottom centre."""
    L = LOOK[kind]
    im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hx, hy = HIP
    # legs
    for side, ang in ((-1, leg_l), (1, leg_r)):
        x1, y1 = _limb(d, hx + side * 30, hy - 10, ang, 200, 40, L["trousers"], L["trousers"], 0, side)
        d.ellipse((x1 - 30 + side * 8, y1 - 10, x1 + 30 + side * 8, y1 + 22), fill=(34, 28, 26))
    # torso (suit jacket) + shirt V + tie
    torso = [(hx - 80, SHOULDER_Y - 18), (hx + 80, SHOULDER_Y - 18), (hx + 66, hy + 4), (hx - 66, hy + 4)]
    d.polygon(torso, fill=L["suit"], outline=L["suit_line"])
    d.polygon([(hx - 26, SHOULDER_Y - 18), (hx + 26, SHOULDER_Y - 18), (hx, SHOULDER_Y + 70)], fill=(252, 250, 244))
    d.line((hx, SHOULDER_Y + 70, hx, hy), fill=L["suit_line"], width=3)
    for k in range(3):
        d.ellipse((hx + 8, SHOULDER_Y + 90 + k * 34, hx + 18, SHOULDER_Y + 100 + k * 34), fill=L["suit_line"])
    if L["tie"] == "bow":
        d.polygon([(hx, SHOULDER_Y - 6), (hx - 24, SHOULDER_Y - 18), (hx - 24, SHOULDER_Y + 6)], fill=L["tie_col"])
        d.polygon([(hx, SHOULDER_Y - 6), (hx + 24, SHOULDER_Y - 18), (hx + 24, SHOULDER_Y + 6)], fill=L["tie_col"])
        d.ellipse((hx - 7, SHOULDER_Y - 13, hx + 7, SHOULDER_Y + 1), fill=L["tie_col"])
    else:
        d.polygon([(hx - 9, SHOULDER_Y - 14), (hx + 9, SHOULDER_Y - 14), (hx + 13, SHOULDER_Y + 50), (hx, SHOULDER_Y + 66),
                   (hx - 13, SHOULDER_Y + 50)], fill=L["tie_col"])
    # arms
    for side, ang, ln in ((-1, arm_l, len_l), (1, arm_r, len_r)):
        _limb(d, hx + side * 78, SHOULDER_Y, ang, ln, 36, L["suit"], SKIN, 20, side)
        _limb(d, hx + side * 78, SHOULDER_Y, ang, ln, 3, L["suit_line"], SKIN, 20, side)  # sleeve seam
    if not head:  # caller pastes its own head (e.g. a photo cut-out)
        return im
    # neck + head
    hcx, hcy, r = hx, SHOULDER_Y - 95, 64
    d.rectangle((hx - 18, SHOULDER_Y - 50, hx + 18, SHOULDER_Y - 10), fill=SKIN)
    d.ellipse((hcx - r - 8, hcy - 8, hcx - r + 12, hcy + 22), fill=SKIN)  # ears
    d.ellipse((hcx + r - 12, hcy - 8, hcx + r + 8, hcy + 22), fill=SKIN)
    d.ellipse((hcx - r, hcy - r, hcx + r, hcy + r), fill=SKIN)
    if L["beard"]:
        d.polygon([(hcx - 30, hcy + 38), (hcx + 30, hcy + 38), (hcx, hcy + 100)], fill=L["beard"])
    # hair / hat
    if L["hat"] == "bowler":
        d.chord((hcx - r - 2, hcy - r - 6, hcx + r + 2, hcy + r - 20), 180, 360, fill=L["hair"])
        d.ellipse((hcx - r - 26, hcy - r + 16, hcx + r + 26, hcy - r + 40), fill=(36, 30, 28))
        d.chord((hcx - r + 6, hcy - r - 54, hcx + r - 6, hcy - r + 60), 180, 360, fill=(36, 30, 28))
        d.rectangle((hcx - r + 8, hcy - r + 14, hcx + r - 8, hcy - r + 26), fill=(110, 30, 30))
    elif L["hat"] == "beret":
        d.chord((hcx - r - 4, hcy - r - 10, hcx + r + 4, hcy + r - 14), 180, 360, fill=L["hair"])
        d.ellipse((hcx - r - 18, hcy - r - 30, hcx + r + 10, hcy - r + 22), fill=(30, 30, 36))
        d.ellipse((hcx - 6, hcy - r - 44, hcx + 8, hcy - r - 26), fill=(30, 30, 36))
    else:
        d.chord((hcx - r - 4, hcy - r - 10, hcx + r + 4, hcy + r - 14), 180, 360, fill=L["hair"])
        d.ellipse((hcx - r - 8, hcy - 26, hcx - r + 18, hcy + 14), fill=L["hair"])
        d.ellipse((hcx + r - 18, hcy - 26, hcx + r + 8, hcy + 14), fill=L["hair"])
    # eyes + glasses
    for ex in (hcx - 24, hcx + 24):
        ey = hcy + 2
        if eyes == "wide":
            d.ellipse((ex - 14, ey - 14, ex + 14, ey + 14), fill=(255, 255, 255))
            d.ellipse((ex - 6, ey - 6, ex + 6, ey + 6), fill=INK)
        elif eyes == "happy":
            d.arc((ex - 10, ey - 6, ex + 10, ey + 12), 200, 340, fill=INK, width=4)
        else:
            d.ellipse((ex - 6, ey - 6, ex + 6, ey + 6), fill=INK)
        d.ellipse((ex - 17, ey - 17, ex + 17, ey + 17), outline=(60, 50, 40), width=3)
        if eyes == "angry":  # brows slanting down toward the nose
            inner = 1 if ex < hcx else -1
            d.line((ex - 18 * inner, ey - 30, ex + 14 * inner, ey - 20), fill=INK, width=7)
    d.line((hcx - 7, hcy + 2, hcx + 7, hcy + 2), fill=(60, 50, 40), width=3)
    d.ellipse((hcx - 6, hcy + 10, hcx + 6, hcy + 24), fill=(222, 170, 140))  # nose
    if L["stache"]:
        d.chord((hcx - 26, hcy + 18, hcx + 26, hcy + 44), 180, 360, fill=L["stache"])
    my = hcy + 42
    if mouth == "o":
        d.ellipse((hcx - 10, my - 4, hcx + 10, my + 20), fill=(90, 30, 30))
    elif mouth == "smile":
        d.chord((hcx - 22, my - 12, hcx + 22, my + 16), 0, 180, fill=(90, 30, 30))
    elif mouth == "yuck":
        d.line([(hcx - 20, my + 6), (hcx - 10, my), (hcx, my + 6), (hcx + 10, my), (hcx + 20, my + 6)], fill=(90, 30, 30), width=4)
    else:
        d.line((hcx - 14, my + 4, hcx + 14, my + 4), fill=(90, 30, 30), width=4)
    return im


def with_border(im, r=7, col=(250, 246, 236)):
    a = im.getchannel("A").point(lambda v: 255 if v > 30 else 0)
    border = a.filter(ImageFilter.MaxFilter(2 * r + 1))
    sh = border.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.4))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", im.size, (0, 10, 40, 255))
    shadow.putalpha(sh)
    out.alpha_composite(shadow, (6, 9))
    paper = Image.new("RGBA", im.size, col + (255,))
    paper.putalpha(border)
    out.alpha_composite(paper)
    out.alpha_composite(im)
    return out


if __name__ == "__main__":
    import sys
    bg = Image.new("RGBA", (CW * 4, CH), (30, 72, 146, 255))
    poses = [("john", {}), ("will", {}), ("john", dict(arm_l=150, arm_r=150, eyes="wide", mouth="smile")),
             ("will", dict(arm_l=160, len_l=140, eyes="wide", mouth="o"))]
    for k, (kind, p) in enumerate(poses):
        bg.alpha_composite(with_border(draw(kind, **p)), (k * CW, 0))
    bg.convert("RGB").save(sys.argv[1])
