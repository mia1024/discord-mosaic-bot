import os
from mosaic_bot import BASE_PATH
from PIL import Image
from mosaic_bot.db import add_image, ImageExists

conflicts=[]
for file in os.listdir(BASE_PATH / 'images'):
    if not file.endswith('.png'):
        continue
    img = Image.open(BASE_PATH / 'images' / file)
    print('Adding',file)
    try:
        add_image(img, file[:-4])
    except ImageExists as e:
        conflicts.append(e.args[0])
print('Conflicts: ')
for c in conflicts:
    print(c)
