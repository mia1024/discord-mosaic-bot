# Questions that nobody asked but thought I should elaborate anyway

## Discord shows From: invalid-user

It's a [known Discord bug](https://bugs.discord.com/T1196), which, unfortunately, is currently labeled as
`wontfix` by Discord. Workaround: use the desktop/web version of Discord. 

## Where does the id of an image come from??

```python
import numpy as np
from scipy import fft
from PIL.Image import Image

def compute_id(img:Image) -> int:
    result = fft.dct(
            fft.dct(np.asarray(img.convert('L')), axis=0, norm='ortho'),
            axis=1, norm='ortho'
    )[:12, :12]
    return int.from_bytes(np.packbits(result > np.average(result[1:,1:])), 'big')
```

It is left to the reader as an exercise to figure out what exactly this code is
doing. 
