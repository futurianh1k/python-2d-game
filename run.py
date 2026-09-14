#!/usr/bin/env python3

import argparse

from pythongame.logging_config import configure_logging, shutdown_logging


def parse_args(argv=None):
    """GUI 초기화 없이 인수를 검증한다. argv 주입으로 오류 경계값을 직접 테스트한다."""
    parser = argparse.ArgumentParser(description="Launch the 2D action RPG.")
    parser.add_argument('--map')
    parser.add_argument('--hero', choices=['MAGE', 'ROGUE', 'WARRIOR', 'GOD'])
    parser.add_argument('--level', type=int)
    parser.add_argument('--money', type=int)
    parser.add_argument('--file')
    parser.add_argument('--disable_fullscreen', '--disable-fullscreen', action='store_true')
    parser.add_argument('--log-file', help='Write a rotating UTF-8 log to this path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    args = parser.parse_args(argv)
    if args.level is not None and args.level < 1:
        parser.error('--level must be at least 1')
    if args.money is not None and args.money < 0:
        parser.error('--money must be at least 0')
    return args


def cli(argv=None):
    """인수 검증 → 로깅 설정 → 게임 import/실행 순서를 지켜 --help를 가볍게 유지한다."""
    args = parse_args(argv)
    configure_logging(args.log_file, args.log_level)
    try:
        from pythongame import main
        main.start(args.map, args.hero, args.level, args.money, args.file, not args.disable_fullscreen)
    finally:
        # 게임이 예외나 SystemExit로 끝나더라도 파일 핸들을 닫아 기록을 완결한다.
        shutdown_logging()


if __name__ == '__main__':
    cli()
