from mosaic_bot.credentials import MOSAIC_BOT_TOKEN
from mosaic_bot.bot import client
import argparse
import sys

parser=argparse.ArgumentParser(description='Run part of the file', prog='mosaic_bot')
parser.add_argument('component',choices=['bot','server'])
args=parser.parse_args()

if args.component=='bot':
    client.run(MOSAIC_BOT_TOKEN)


