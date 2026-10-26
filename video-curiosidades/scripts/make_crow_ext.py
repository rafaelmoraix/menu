"""Extend the channel crow (red background) to the right so its body runs off the bottom of the
frame instead of ending in the source image's hard vertical edge. Used by vox_encerramento.py."""
import sys
import numpy as np
from PIL import Image

src = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
EXT = 260
ext = src[:, ::-1][:, :EXT].copy()
ys = np.arange(src.shape[0])[:, None]
ks = np.arange(EXT)[None, :]
ext[ys < 595 + 1.1 * (ks + 1)] = (189, 31, 32)  # continue the shoulder line; outside it is background red
Image.fromarray(np.concatenate([src, ext], axis=1)).save(sys.argv[2])
