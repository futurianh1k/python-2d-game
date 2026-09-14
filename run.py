#!/usr/bin/env python3

import argparse

from pythongame import main

def cli():
    parser = argparse.ArgumentParser(description="Launch the 2D action RPG.")
    parser.add_argument('--map')
    parser.add_argument('--hero', choices=['MAGE', 'ROGUE', 'WARRIOR', 'GOD'])
    parser.add_argument('--level', type=int)
    parser.add_argument('--money', type=int)
    parser.add_argument('--file')
    parser.add_argument('--disable_fullscreen', '--disable-fullscreen', action='store_true')
    args = parser.parse_args()

    main.start(args.map, args.hero, args.level, args.money, args.file, not args.disable_fullscreen)


if __name__ == '__main__':
    cli()
