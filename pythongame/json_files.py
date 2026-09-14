"""캐릭터·맵 파일이 공유하는 UTF-8 JSON 입출력 경계.

기존 파일을 직접 'w'로 열면 직렬화나 디스크 쓰기 도중 실패해도 원본이 이미
잘려 있다. 같은 디렉터리의 임시 파일에 완성한 후 os.replace로 교체해야
독자는 완성된 이전 파일 또는 완성된 새 파일을 보게 된다.

검증: tests/unit/test_json_files.py. 이는 단일 파일 교체에 대한 보장이며,
여러 게임 프로세스의 저장 순서 조정이나 전원 장애 복구까지 보장하지 않는다.
"""

import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


def read_json(path: str | Path) -> Any:
    """파일 경로·traceback을 기록하고 원래 읽기/디코딩 예외를 호출자에게 전달한다.

    읽기와 게임별 스키마 검증은 분리한다. JSON 배열 같은 값도 이 계층에서는
    유효하며, 캐릭터 파일인지 여부는 PlayerStateJson에서 판단한다.
    """
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        logger.exception("Failed to read JSON: %s", path)
        raise
    logger.debug("Loaded JSON: %s", path)
    return data


def write_json_atomic(path: str | Path, data: Any) -> None:
    """직렬화 → flush/fsync → 닫기 → 교체 순서로 저장하고 임시 파일을 정리한다.

    부모 디렉터리를 자동 생성하지 않는다. 저장 위치 선택과 생성 책임은
    SaveFileHandler 또는 맵 편집기 호출자에게 있어 경로 오타를 숨기지 않는다.
    """
    path = Path(path)
    temporary_path = None
    try:
        # 같은 파일시스템에서 rename/replace하도록 대상 파일 옆에 생성한다.
        # Windows에서도 교체할 수 있도록 with 블록을 빠져나와 핸들을 먼저 닫는다.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            # 한글은 UTF-8 원문으로 보존하고 표준 JSON에 없는 NaN/Infinity는 거부한다.
            json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # 이 지점 전의 실패는 기존 파일을 건드리지 않는다. 성공 로그도 교체 후에만 쓴다.
        os.replace(temporary_path, path)
    except (OSError, TypeError, ValueError):
        logger.exception("Failed to write JSON: %s", path)
        raise
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                # 정리 실패가 디스크 오류 등 원래 예외를 덮어쓰지 않도록 경고만 남긴다.
                logger.warning("Could not remove temporary JSON file: %s", temporary_path, exc_info=True)
    logger.info("Saved JSON: %s", path)
