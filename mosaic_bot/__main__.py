from mosaic_bot.bot import run_bot
from mosaic_bot.server import run_server
from mosaic_bot import DATA_PATH
import argparse, os

parser = argparse.ArgumentParser(description = 'Run part of the file', prog = 'mosaic_bot')
parser.add_argument('component', choices = ['bot', 'server', 'gunicorn'])
args = parser.parse_args()

if args.component == 'bot':
    run_bot()
elif args.component == 'server':
    run_server()
else:
    os.execvp('gunicorn', ['gunicorn','mosaic_bot.server.wsgi',
                           '--access-logfile', '-',
                           '--workers', '1',
                           '--bind', '0.0.0.0:80'])
