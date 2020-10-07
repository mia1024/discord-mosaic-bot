from typing import Tuple


def int_to_rgb(color: int) -> Tuple[int,int,int]:
    return color >> 16, (color >> 8) % 256, color % 256


def rgb_to_int(r: int, g: int, b: int) -> int:
    return (r << 16) + (g << 8) + b
