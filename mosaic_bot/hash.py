from mosaic_bot import IMAGE_DIR
from PIL import Image
import numpy as np
import cv2

b64_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
reverse_b64_alphabet = {
    b64_alphabet[i]: i for i in range(64)
}


def diff_hash(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count('1')


def encode_hash(hash: int) -> str:
    """
    an implementation of base64 that actually represent numbers under
    the base of 64, which is much better than the standard base64
    implementation in that this requires no padding.
    """
    if hash == 0: return '0'
    encoded = ''
    while hash:
        hash, remainder = divmod(hash, 64)
        encoded += b64_alphabet[remainder]
    return encoded[::-1]


def decode_hash(encoded_hash: str) -> int:
    sum = 0
    for char in encoded_hash:
        sum <<= 6
        bits = reverse_b64_alphabet[char]
        sum += bits
    
    return sum


def compute_image_path_from_hash(hash: int) -> str:
    return IMAGE_DIR / (encode_hash(hash) + '.png')


def hash_image(img: Image.Image) -> int:
    # implemented based on the pHash algorithm in
    # http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    # however, since all the images here are already pixel art, no resizing is necessary
    #
    # Additional ref: https://www.phash.org/docs/pubs/thesis_zauner.pdf,
    # https://github.com/JohannesBuchner/imagehash/blob/2e6eb38f06741286282733470c173a057e186c0a/imagehash.py#L197
    
    img = img.convert('L')
    arr = np.asarray(img)
    w,h=arr.shape
    z = np.zeros((w+1 if w%2 else w,h+1 if h%2 else h),np.float64)
    z[:w,:h]=arr
    freq = cv2.dct(z)[:12, :12]
    return int.from_bytes(np.packbits(freq > np.average(freq[1:,1:])), 'big')


__all__ = ['diff_hash', 'encode_hash', 'decode_hash', 'compute_image_path_from_hash', 'hash_image']
