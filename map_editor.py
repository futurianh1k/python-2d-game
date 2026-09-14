#!/usr/bin/env python3

import argparse

from pythongame.logging_config import configure_logging, shutdown_logging


def parse_args(argv=None):
    """게임 실행기와 같은 로그 옵션을 제공하며 편집기 초기화 전에 도움말을 처리한다."""
    parser = argparse.ArgumentParser(description="Launch the map editor.")
    parser.add_argument('--map')
    parser.add_argument('--log-file', help='Write a rotating UTF-8 log to this path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    return parser.parse_args(argv)


def cli(argv=None):
    """편집기 종료·실패 경로 모두에서 로그 파일을 닫는 CLI 경계."""
    args = parse_args(argv)
    configure_logging(args.log_file, args.log_level)
    try:
        from pythongame.map_editor import map_editor
        map_editor.main(args.map)
    finally:
        shutdown_logging()


if __name__ == '__main__':
    cli()
