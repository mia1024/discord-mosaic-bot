import setuptools
import sys, pathlib

sys.path.append(pathlib.Path(__file__).resolve().parent)
from mosaic_bot import __version__

setuptools.setup(
        name='discord-mosaic-bot',
        author='Jerie Wang',
        url='https://mosaic.by.jerie.wang/',
        author_email='mail@jerie.wang',
        python_requires='>=3.9',
        version=__version__,
        install_requires=[
            'discord',
            'aiohttp',
            'chardet',
            'cchardet',
            'aiodns',
            'requests',
            'numpy',
            'pillow',
            'SQLAlchemy',
            'gunicorn',
            'flask'
        ],
        packages = ['mosaic_bot','mosaic_bot.bot'],
        zip_safe = False
)
