#!/usr/bin/env python3
"""정적 검사·pytest·파일 무결성 결과를 한 번의 실행으로 보관한다.

실행: .venv314/bin/python scripts/verify.py
산출물: artifacts/{validation-summary.json,junit.xml,coverage.json,coverage.xml,
                  pytest.log,tests-output.log,compile-output.log,dependencies-output.log}

결과를 추정하지 않고 각 명령의 종료 코드, JUnit 수치, 실행 전후 SHA-256을 읽는다.
실패한 단계가 있어도 다른 진단 결과를 수집한 다음 스크립트 자체가 1로 종료한다.
이 스크립트는 기존 저장 파일/리소스를 수정하지 않으며 Git 작업도 수행하지 않는다.
"""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def protected_file_hashes() -> dict[str, str]:
    """실제 게임 데이터와 저장 파일의 내용은 노출하지 않고 경로/해시만 수집한다.

    파일의 추가·삭제도 비교할 수 있도록 전체 경로 목록을 해시 사전의 키로 사용한다.
    테스트 산출물과 가상환경은 쓰기가 예상되는 영역이므로 비교에서 제외한다.
    """
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in (ROOT / "resources", ROOT / "saved_characters")
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def run_step(name: str, args: list[str], output: Path) -> dict:
    """같은 Python으로 검사하고 stdout/stderr를 UTF-8 증거 파일에 함께 보관한다."""
    command = [sys.executable, *args]
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=300)
        returncode = result.returncode
        text = result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        # 시간 초과도 성공으로 처리하지 않는다. subprocess.run은 자식 프로세스를 정리한다.
        returncode = 124
        text = f"Timed out after {exc.timeout}s: {command!r}\n"
    log_path = output / f"{name}-output.log"
    log_path.write_text(text, encoding="utf-8")
    print(f"{name}: {'PASS' if returncode == 0 else 'FAIL'} ({log_path.relative_to(ROOT)})", flush=True)
    return {"name": name, "command": command, "returncode": returncode,
            "log": str(log_path.relative_to(ROOT))}


def main() -> int:
    """JUnit/커버리지와 실제 파일 해시를 교차 확인한 요약을 JSON으로 기록한다."""
    started = datetime.now(timezone.utc)
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    before = protected_file_hashes()
    checks = [
        run_step("compile", ["-W", "error", "-m", "compileall", "-q", "pythongame", "tests", "scripts",
                             "run.py", "map_editor.py"], output),
        run_step("dependencies", ["-m", "pip", "--disable-pip-version-check", "--no-cache-dir", "check"], output),
        run_step("tests", ["-m", "pytest", "--cov", "--cov-report=term", "--cov-report=html",
                           f"--cov-report=json:{output / 'coverage.json'}",
                           f"--cov-report=xml:{output / 'coverage.xml'}",
                           f"--junitxml={output / 'junit.xml'}",
                           f"--log-file={output / 'pytest.log'}", "--log-file-level=DEBUG"], output),
    ]
    after = protected_file_hashes()
    unchanged = before == after
    summary = {
        "started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "dependencies": {name: version(name) for name in ("pygame-ce", "pytest", "pytest-cov", "coverage")},
        "checks": checks, "protected_files": len(before), "protected_files_unchanged": unchanged,
        "changed_protected_paths": sorted(path for path in before.keys() | after.keys()
                                          if before.get(path) != after.get(path)),
    }
    # 이전 실행의 파일을 새 결과로 오인하지 않도록 생성 시각도 확인한다.
    junit = output / "junit.xml"
    if junit.exists() and junit.stat().st_mtime >= started.timestamp():
        suites = ET.parse(junit).getroot().iter("testsuite")
        counts = {name: 0 for name in ("tests", "failures", "errors", "skipped")}
        for suite in suites:
            for name in counts:
                counts[name] += int(suite.attrib.get(name, 0))
        summary["pytest"] = counts
    coverage = output / "coverage.json"
    if coverage.exists() and coverage.stat().st_mtime >= started.timestamp():
        summary["coverage"] = json.loads(coverage.read_text(encoding="utf-8"))["totals"]
    success = all(check["returncode"] == 0 for check in checks) and unchanged
    summary["success"] = success
    (output / "validation-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"Protected files unchanged: {unchanged}; summary: artifacts/validation-summary.json", flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
