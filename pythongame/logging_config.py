"""게임/맵 편집기 CLI가 명시적으로 호출하는 로깅 설정.

모듈 import만으로 파일이나 콘솔 핸들러를 생성하지 않는다. --help와 테스트
수집이 실제 실행 환경에 영향을 주지 않게 하기 위해서다. 기본 출력은 stderr,
--log-file 지정 시에만 UTF-8 회전 로그를 추가한다.

검증: tests/unit/test_logging_and_crashes.py의 중복 출력·회전·traceback 검사.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# root logger나 pytest의 caplog 핸들러를 제거하지 않도록 직접 만든 것만 추적한다.
_handlers: list[logging.Handler] = []
LOG_MAX_BYTES = 1_048_576
LOG_BACKUP_COUNT = 3


def configure_logging(log_file: str | Path | None = None, level: str = "INFO") -> None:
    """이전 자체 핸들러를 교체해 반복 호출에도 같은 메시지가 중복되지 않게 한다.

    파일은 append로 열며 최대 1 MiB, 백업 3개를 유지한다. 로그 파일 생성에
    실패하면 기존 설정을 제거하기 전에 예외를 전달해 실패 원인을 숨기지 않는다.
    """
    logger = logging.getLogger("pythongame")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(
            path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8",
        ))
    shutdown_logging()
    logger.setLevel(level)
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    _handlers.extend(handlers)


def shutdown_logging() -> None:
    """앱 소유 핸들러만 닫는다. 반복 호출해도 안전하며 로그 파일 잠금도 해제한다."""
    logger = logging.getLogger("pythongame")
    for handler in _handlers:
        logger.removeHandler(handler)
        handler.close()
    _handlers.clear()
