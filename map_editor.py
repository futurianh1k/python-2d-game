#!/usr/bin/env python3

import argparse

from pythongame.logging_config import configure_logging, shutdown_logging


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Launch the map editor.")
    parser.add_argument('--map')
    parser.add_argument('--log-file', help='Write a rotating UTF-8 log to this path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    return parser.parse_args(argv)


def cli(argv=None):
    args = parse_args(argv)
    configure_logging(args.log_file, args.log_level)
    try:
        from pythongame.map_editor import map_editor
        map_editor.main(args.map)
    finally:
        shutdown_logging()


if __name__ == '__main__':
    cli()
