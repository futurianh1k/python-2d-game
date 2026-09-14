#!/usr/bin/env python3

import argparse

from pythongame.map_editor import map_editor

def cli():
    parser = argparse.ArgumentParser(description="Launch the map editor.")
    parser.add_argument('--map')
    args = parser.parse_args()

    map_editor.main(args.map)


if __name__ == '__main__':
    cli()
