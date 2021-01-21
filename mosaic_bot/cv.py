import cv2
from PIL import Image
import numpy as np
from collections import Counter
from math import log2
from typing import Union


class ScaleCandidate:
    def __init__(self, scale: int, score: int = 0):
        self.scale = scale
        self.score = score
        self.align = -1
        self.shade: Union[np.array, Image.Image] = None
    
    def __str__(self):
        return str(self.scale)
    
    def __int__(self):
        return self.scale
    
    def __repr__(self):
        return f'<scale: {self.scale}, score:{self.score}, align: {round(self.align, 3)}>'


class DebugData:
    def __init__(self):
        self.candidates: list[ScaleCandidate] = []
        self.labeled: Union[Image.Image, np.ndarray] = None
    
    def __repr__(self):
        return f'<{self.candidates}>'


class NoScaleFound(Exception):pass

def find_scale(PIL_image: Image.Image, debug=False, prioritize_alignment=False) \
        -> Union[int, tuple[int, DebugData]]:
    cropped = PIL_image.crop(PIL_image.getbbox())
    debug_data = DebugData()
    cropped = cropped.convert('RGBA')
    color_img = np.asarray(cropped)
    
    gray_img = cv2.cvtColor(color_img, cv2.COLOR_RGBA2GRAY)
    # color_img = cv2.cvtColor(color_img, cv2.COLOR_RGBA2BGRA)
    
    edges = cv2.Canny(gray_img, 50, 150)
    cnt, hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if debug:
        debug_data.labeled = cv2.drawContours(
                cv2.cvtColor(color_img, cv2.COLOR_RGBA2BGRA),
                cnt, -1, (255, 0, 0, 255), 1
        )
    l = []  # for all the bbox dimensions
    for c in cnt:
        if cv2.contourArea(c) < 4 and cropped.width > 64:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if debug:
            cv2.rectangle(debug_data.labeled, (x, y), (x + w, y + h), (0, 255, 0, 255), 1)
        l.extend((w, h))
    
    candidates = []
    for n, occ in Counter(l).most_common(10):
        # add all candidates
        if cropped.width / n > 80 or cropped.width / n < 8:
            # noise
            continue
        
        candidates.append(ScaleCandidate(n, occ))
        if n > 1:
            candidates.append(ScaleCandidate(n - 1, occ))
        if n > 2:
            candidates.append(ScaleCandidate(n - 2, occ))
        # sometimes the bbox is always 1 or 2 pixels larger
        # because of the compression artifact
    
    candidates.sort(key=lambda c: c.scale)
    
    while True:
        # merge all the duplicate candidates from the last step
        for i in range(len(candidates) - 1):
            if candidates[i].scale == candidates[i + 1].scale:
                candidates[i].score += candidates[i + 1].score
                del candidates[i + 1]
                break
        else:
            break
    
    for c in candidates:
        if log2(c.scale).is_integer() or (c.scale / 5).is_integer():
            # artists tend to choose some "normal" looking numbers, this
            # might be tie breakers for some ridiculously compressed images
            c.score += 5
        c.score += (cropped.width / c.scale).is_integer() * 2
        c.score += (cropped.height / c.scale).is_integer()
        for d in candidates:
            # deduce the relationships between candidates.
            # there should be larger blocks of pixels that are multiples
            # of the correct scale due to the nature of pixel arts
            c.score += (d.scale / c.scale).is_integer()
    
    if cropped.width <= 64:
        # adds a scale of 1 if not exist already
        for c in candidates:
            if c.scale == 1: break
        else:
            candidates.append(ScaleCandidate(1, 1))
    
    if not candidates:
        raise NoScaleFound
    
    align_factor = max(candidates, key=lambda c: c.score).score * 5
    
    for c in candidates:
        # calculate the alignment score
        
        if c.scale == 1:
            # a scale of 1 always has perfect alignment so we need to
            # do something special about it so it can focus on the larger image
            c.score += align_factor * 0.95
            c.align = 1
            if debug:
                c.shade = debug_data.labeled  # of course no shading can happen
            continue
        
        nw = color_img.shape[1] // c.scale
        nh = color_img.shape[0] // c.scale
        
        resized = cv2.resize(color_img, (nw, nh), interpolation=cv2.INTER_NEAREST_EXACT)
        # use the computed scale in case of some cropping issues which causes non-integer ratios
        resized = cv2.resize(resized, None, fx=c.scale, fy=c.scale, interpolation=cv2.INTER_NEAREST_EXACT)
        
        rh = resized.shape[0]
        ah = color_img.shape[0]
        rw = resized.shape[1]
        aw = color_img.shape[1]
        if (rh < ah or rw < aw) and not (rh > ah or rw > aw):
            # if the resized image is somehow larger than the source this is
            # probably the wrong scale anyway, so whatever
            
            template = cv2.cvtColor(resized, cv2.COLOR_RGBA2GRAY)
            match = cv2.matchTemplate(gray_img, template, cv2.TM_SQDIFF)
            # using grayscale for faster matching
            
            corner = cv2.minMaxLoc(match)[2]
            aligned_source = color_img[corner[1]:corner[1] + nh * c.scale, corner[0]:corner[0] + nw * c.scale]
        else:
            corner = (0, 0)
            aligned_source = color_img
        
        h = min(aligned_source.shape[0], resized.shape[0])
        w = min(aligned_source.shape[1], resized.shape[1])
        
        aligned_source = aligned_source[:h, :w]
        resized = resized[:h, :w]
        
        diff = cv2.absdiff(resized, aligned_source)
        total_diff = np.sum(diff)
        total_values = np.sum(aligned_source)
        
        c.align = (total_values - total_diff) / total_values
        # using colored diff instead of binary because the feathered pixels
        # around each "pixel" in the source file should have similar color
        # to the resized ones, therefore should incur less alignment penalty
        # than the drastically different color.
        c.score += round(c.align * align_factor, 2)
        
        if debug:
            shade = np.sum(diff, axis=2) // 3
            shade = cv2.cvtColor(shade.astype(np.uint8), cv2.COLOR_GRAY2RGBA)
            
            # set the non-shaded pixels to transparent
            shade[:, :, 3] = np.where(shade[:, :, 0] > 0,
                                      np.full(shade.shape[:2], 255),
                                      np.zeros(shade.shape[:2]))
            
            shade[:, :, 1] = 0  # set it to magenta
            
            container = np.zeros(debug_data.labeled.shape, dtype=np.uint8)
            container[corner[1]:h + corner[1], corner[0]:w + corner[0]] = \
                shade[:h, :w]
            
            c.shade = Image.fromarray(
                    cv2.cvtColor(
                            cv2.addWeighted(debug_data.labeled, 1, container, 1, 0),
                            cv2.COLOR_BGRA2RGBA
                    ))
        
        if c.align >= 0.99:
            c.score += align_factor * c.align
            # perfect alignment is conclusive so it gets bonus score to ensure
            # its victory
            break
    
    if prioritize_alignment:
        candidates.sort(key=lambda c: c.align, reverse=True)
    else:
        candidates.sort(key=lambda c: c.score, reverse=True)
    
    if debug:
        debug_data.candidates = candidates
        debug_data.labeled = Image.fromarray(
                cv2.cvtColor(debug_data.labeled, cv2.COLOR_BGRA2RGBA)
        )
        return candidates[0].scale, debug_data


__all__ = ['find_scale', 'DebugData']
