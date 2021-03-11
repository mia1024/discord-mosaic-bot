from mosaic_bot.bot import run_bot
from mosaic_bot.server import run_server
import argparse

parser=argparse.ArgumentParser(description='Run part of the file', prog='mosaic_bot')
parser.add_argument('component',choices=['bot','server'])
args=parser.parse_args()

if args.component=='bot':
    run_bot()
else:
    run_server()

