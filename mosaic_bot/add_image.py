import os
from mosaic_bot import DATA_PATH
from PIL import Image
from mosaic_bot import db
import shutil
from mosaic_bot.hash import hash_image
import datetime

conflicts = []
if os.path.exists(DATA_PATH / 'images'):
    shutil.rmtree(DATA_PATH / 'images')
os.mkdir(DATA_PATH / 'images')
for file in os.listdir(DATA_PATH / 'all_images'):
    if not file.endswith('.png'):
        continue
    path=DATA_PATH / 'all_images' / file
    img = Image.open(path)
    last_mod=datetime.datetime.fromtimestamp(os.stat(path).st_mtime)
    try:
        db.add_image(img, file[:-4].replace('_', ' '), 1,last_mod)
    except db.ImageExists as e:
        conflicts.append(e.args[0])
    else:
        name = db.get_image_path(hash_image(img))
        shutil.copy(DATA_PATH / 'all_images' / file, DATA_PATH / name)
print('Conflicts: ')
for c in conflicts:
    print(c)
