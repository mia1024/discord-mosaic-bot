import os
from mosaic_bot import BASE_PATH
from PIL import Image
from mosaic_bot import db
import shutil
from mosaic_bot.hash import hash_image

conflicts = []
if os.path.exists(BASE_PATH/'images'):
    shutil.rmtree(BASE_PATH / 'images')
os.mkdir(BASE_PATH / 'images')
for file in os.listdir(BASE_PATH / 'all_images'):
    if not file.endswith('.png'):
        continue
    img = Image.open(BASE_PATH / 'all_images' / file)
    try:
        db.add_image(img, file[:-4].replace('_', ' '), 1)
    except db.ImageExists as e:
        conflicts.append(e.args[0])
    else:
        name = db.get_image_path(hash_image(img))
        shutil.copy(BASE_PATH / 'all_images' / file, BASE_PATH / name)
print('Conflicts: ')
for c in conflicts:
    print(c)
