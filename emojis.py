from utils import int_to_rgb
from typing import Tuple
from math import inf

f = open('emoji_ids.txt')
emojis = {}
for line in f.readlines():
    name, id = line.split()
    emojis[int_to_rgb(int(name[1:7], 16))] = id


def find_closest_color(r: int, g: int, b: int) -> Tuple[int, int, int]:
    min_distance = inf
    min_value = (0, 0, 0)
    for r_, g_, b_ in emojis.keys():
        distance = abs(r - r_) + abs(g - g_) + abs(b - b_)
        if distance <= 32:
            return r_, g_, b_
        if distance < min_distance:
            min_distance = distance
            min_value = (r_, g_, b_)
    return min_value


def get_emoji_by_rgb(r, g, b) -> str:
    if (r,g,b) in emojis:
        return emojis[r,g,b]
    return emojis[find_closest_color(r,g,b)]



