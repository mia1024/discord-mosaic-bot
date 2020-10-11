import cv2
from PIL import Image
import numpy as np
from collections import Counter
from math import log2
from typing import List


class ScaleCandidate:
    def __init__(self, scale: int, score=0):
        self.scale = scale
        self.score = score
    
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


class DebugData:
    def __init__(self):
        self.candidates: List[ScaleCandidate] = None
        self.labeled: np.ndarray = None


def find_scale(PIL_image: Image.Image, debug: DebugData = None):
    cropped = PIL_image.crop(PIL_image.getbbox())
    if cropped.mode not in ('RGB', 'RGBA'):
        cropped = cropped.convert('RGBA')
    if cropped.width <= 21:
        return 1
    arr = np.array(cropped)
    if cropped.mode == 'RGBA':
        im = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
    else:
        im = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    
    edges = cv2.Canny(im, 50, 150)
    cnt, hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if debug is not None:
        debug.labeled = cv2.drawContours(
                cv2.cvtColor(arr, cv2.COLOR_RGB2BGR if PIL_image.mode == 'RGB' else cv2.COLOR_RGBA2BGRA),
                cnt, -1, (255, 0, 0, 255), 4
        )
    l = []
    
    for c in cnt:
        if cv2.contourArea(c) < 4:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if debug is not None:
            cv2.rectangle(debug.labeled, (x, y), (x + w, y + h), (255, 0, 255, 255), 2)
        
        l.extend((w, h))
    
    candidates = []
    for n, occ in Counter(l).most_common(5):
        if cropped.width / n > 50:
            # noise
            continue
        
        candidates.append(ScaleCandidate(n - 1, occ))  # the bbox is always 1 or 2 pixels larger
        candidates.append(ScaleCandidate(n - 2, occ))
    
    candidates.sort(key=lambda c: c.scale)
    while True:
        for i in range(len(candidates) - 1):
            if candidates[i].scale == candidates[i + 1].scale:
                candidates[i].score += candidates[i + 1].score
                del candidates[i + 1]
                break
        else:
            break
    
    for c in candidates:
        if log2(c.scale).is_integer() or (c.scale / 5).is_integer():
            # artists tend to choose some "normal" looking numbers
            # used as tie breakers for some ridiculously compressed images
            c.score += 1
        c.score += (cropped.width / c.scale).is_integer()
        for d in candidates:
            c.score += (d / c).is_integer()
    
    candidates.sort(key=lambda c: c.score, reverse=True)
    
    if debug is not None:
        debug.candidates = candidates
    if not candidates:
        return cropped.width // 20 + 1
    return candidates[0].scale


__all__ = ['find_scale', 'DebugData']
