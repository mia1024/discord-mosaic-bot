import cv2
from PIL import Image
import numpy as np
from collections import Counter
from math import log2


class ScaleCandidate:
    def __init__(self, scale: int):
        self.scale = scale
        self.score = 0
    
    def __str__(self):
        return str(self.scale)
    
    def __int__(self):
        return self.scale
    
    def __repr__(self):
        return f'<scale: {self.scale}, score:{self.score}>'
    
    def __eq__(self, other):
        return id(self) == id(other)
    
    def __truediv__(self, other):
        return self.scale / other.scale


def find_scale(PIL_image: Image.Image):
    cropped = PIL_image.crop(PIL_image.getbbox())
    if cropped.width<=25:
        return 1
    arr = np.array(cropped)
    im = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY if PIL_image.mode == 'RGB' else cv2.COLOR_RGBA2GRAY)
    edges = cv2.Canny(im, 50, 150)
    cnt, hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    l = []
    
    for c in cnt:
        if cv2.contourArea(c) < 4:
            continue
        x, y, w, h = cv2.boundingRect(c)
        l.extend((w, h))
    
    candidates = []
    for n, occ in Counter(l).most_common(5):
        if cropped.width / n > 50:
            # noise
            continue
        
        candidates.append(ScaleCandidate(n - 1))  # the bbox is always 1 or 2 pixels larger
        candidates.append(ScaleCandidate(n - 2))
    
    candidates.sort(key=lambda c:c.scale)
    for c in candidates:
        if log2(c.scale).is_integer() or (c.scale/5).is_integer():
            # artists tend to choose some "normal" looking numbers
            # used as tie breakers for some ridiculously compressed images
            c.score+=1
        c.score += (cropped.width / c.scale).is_integer()
        for d in candidates:
            c.score += (d / c).is_integer()

    candidates.sort(key=lambda c:c.score,reverse=True)
    return candidates[0].scale
