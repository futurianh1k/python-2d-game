"""UTF-8 JSON I/O that preserves existing files when a write fails."""

import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


def read_json(path: str | Path) -> Any:
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
    """Write beside the destination, then replace it only after flush succeeds."""
    path = Path(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except (OSError, TypeError, ValueError):
        logger.exception("Failed to write JSON: %s", path)
        raise
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove temporary JSON file: %s", temporary_path, exc_info=True)
    logger.info("Saved JSON: %s", path)
