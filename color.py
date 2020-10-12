from typing import Tuple


def int_to_rgb(color: int) -> Tuple[int, int, int]:
    return color >> 16, (color >> 8) % 256, color % 256


def rgb_to_int(r: int, g: int, b: int) -> int:
    # apparently rgb can occasionally be np.int64 and it breaks the hash method
    return int((r << 16) + (g << 8) + b)


class Color:
    def __init__(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b
        self.hex = hex(rgb_to_int(r, g, b))[2:].zfill(6)
    
    def approx_12bit(self):
        tmp = [0, 0, 0]
        
        for i in range(3):
            hbits = self[i] >> 4
            comp = (hbits << 4) + hbits - self[i]
            # there's 17 difference between each color
            if comp < -9:
                tmp[i] = ((hbits + 1) << 4) + hbits + 1
                # this shouldn't overflow because
                # 0xff-0xff is 0 so this will
                # never be true
            elif comp > 8:
                tmp[i] = ((hbits - 1) << 4) + hbits - 1
            else:
                tmp[i] = (hbits << 4) + hbits
        return Color(*tmp)
    
    @classmethod
    def from_int(cls, n: int):
        return Color(*int_to_rgb(n))
    
    @classmethod
    def from_hex(cls, s: str):
        return Color(int(s[:2], 16), int(s[2:4], 16), int(s[4:], 16))
    
    def __iter__(self):
        return iter((self.r, self.g, self.b))
    
    def __getitem__(self, idx: int):
        if not isinstance(idx, int):
            raise TypeError('Index must be an int')
        
        if idx == 0:
            return self.r
        if idx == 1:
            return self.g
        if idx == 2:
            return self.b
        raise IndexError
    
    def __hash__(self):
        return rgb_to_int(*self)
    
    def __eq__(self, other):
        return all(self[i] == other[i] for i in range(3))
    
    def __str__(self):
        return '#' + self.hex
    
    def __repr__(self):
        return f'<{str(self)}>'
    
    def __int__(self):
        return rgb_to_int(*self)


__all__ = ['rgb_to_int', 'int_to_rgb', 'Color']
