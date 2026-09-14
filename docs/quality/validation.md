# 실행 결과와 파일·로그 검증

2026-09-14에 로컬 Linux/WSL2 환경에서 실행했다. 결과는
`python scripts/verify.py`가 생성한 JUnit·coverage JSON·종료 코드·SHA-256 비교를
읽어 기록했다. 문서의 수치는 전체 게임의 모든 동작을 보장한다는 뜻이 아니다.

## 실행 환경과 결과

| 항목 | 확인 결과 |
| --- | --- |
| Python | 3.14.4 |
| pygame-ce / SDL | 2.5.8 / 2.32.10 |
| pytest / pytest-cov / coverage | 9.1.1 / 7.1.0 / 7.16.1 |
| OS | Linux/WSL2 x86_64, glibc 2.43 |
| 그래픽·오디오 | SDL dummy 드라이버; 실제 화면·스피커 없음 |
| 변경 전 기준 | unittest 6개 통과, 그 밖의 저장 장애 D01–D03 재현 |
| 최종 pytest | **119개 통과, 실패 0, 오류 0, skip 0** |
| 컴파일 검사 | `-W error -m compileall` 종료 코드 0 |
| 의존성 검사 | `pip check` 종료 코드 0 |
| 실제 데이터 무결성 | **리소스·저장 파일 270개의 실행 전후 경로와 SHA-256 동일** |
| PyInstaller | 6.22.2 빌드 성공; 외부 임시 cwd에서 WARRIOR 레벨 5 실행 3초 후 종료 코드 0 |
| 빌드 결과 로그 | `Starting game` / `Game stopped` 기록, ERROR·traceback 없음 |
| 플랫폼 범위 | Windows/macOS는 CI 구성 완료. 이 로컬 실행에서 검증하지 않음 |

동일 실행의 기계 판독용 요약은 [verification.json](verification.json)에 보관한다.
원시 산출물은 저장소 루트 `artifacts/`에 있으며 Git에서는 제외한다.

## 커버리지 해석

| 범위 | 실행 줄 / 전체 줄 | 줄 커버리지 | 분기 커버리지 | 줄+분기 합산 |
| --- | --- | --- | --- | --- |
| 전체 측정 범위 | 9,422 / 13,115 | 71.84% | 35.83% | 65.90% |
| json_files.py | 37 / 37 | 100.00% | 50.00% | 97.44% |
| player_file.py | 102 / 102 | 100.00% | 100.00% | 100.00% |
| logging_config.py | 26 / 26 | 100.00% | 83.33% | 96.88% |
| main.py | 117 / 133 | 87.97% | 33.33% | 83.45% |
| map_file.py | 130 / 133 | 97.74% | 분기 없음 | 97.74% |

측정 대상은 `pythongame`, `run`, `map_editor`다. CLI를 새 프로세스에서 실행하는
테스트도 통과했지만 해당 자식 프로세스 실행량은 이 커버리지에 합산하지 않는다.
import 시 등록되는 게임 데이터도 분모/분자에 들어가므로 전체 수치를 게임 행동의
검증 비율과 동일시하지 않는다. 줄 100%가 모든 분기 검증을 뜻하지 않도록 둘을 구분했다.

전체 게임의 전투·퀘스트·상호작용 분기는 아직 낮다. 이번에는 파일/로그/초기화/복원
실패 경로를 우선했으며 임의의 높은 전체 커버리지 기준을 통과했다고 표시하지 않는다.
HTML 리포트에서 남은 줄/분기를 확인한 후 다음 TC의 우선순위를 정할 수 있다.

## 파일과 로그 판정

- 실제 캐릭터와 맵 파일은 임시 파일 생성/부분 직렬화/fsync/replace 실패를 주입해
  **대상 파일의 이전 SHA-256이 유지되는지** 검사했다. 정상 저장은 새 JSON 전체가
  읽히는지와 임시 파일 제거를 함께 검사했다.
- 읽기 오류는 없음, JSON 잘림, UTF-8 오류로 나누었다. 스키마 검증은 루트/필수 필드/
  타입/기본 범위/enum을 다룬다. 일부 게임 의미 검증의 한계는 진단 문서에 명시했다.
- 로그는 실제 파일의 UTF-8 해독, 레벨 필터, 중복 핸들러 방지, 회전 후 백업 개수,
  최신 메시지 보존, traceback과 종료 기록을 검사했다.
- 비상 저장이 실패해도 최초 게임 오류가 유지되는지 예외 객체 동일성과 로그를
  함께 비교했다. 플레이/일시정지 × 백업 성공/실패의 네 조합을 실행했다.
- `artifacts/pytest.log`의 ERROR에는 **의도적으로 실패를 주입한 음성 TC**가 포함된다.
  ERROR 문자열 존재 여부만으로 전체 테스트 실패를 판정하지 않는다. JUnit의
  failures/errors와 해당 TC의 기대 로그 assertion을 함께 확인해야 한다.

## 재실행과 산출물

```sh
.venv314/bin/python -m pip install -r requirements-dev.txt
.venv314/bin/python scripts/verify.py
```

원하는 그룹만 실행하거나 수집 목록을 확인하려면:

```sh
.venv314/bin/python -m pytest -m unit
.venv314/bin/python -m pytest -m integration
.venv314/bin/python -m pytest -m process
.venv314/bin/python -m pytest --collect-only -q
```

| 산출물 | 용도 |
| --- | --- |
| artifacts/validation-summary.json | 실행 환경, 단계별 명령/종료 코드, 테스트/커버리지 수치, 보호 파일 비교 |
| artifacts/junit.xml | TC별 이름·시간과 실패/오류/skip |
| artifacts/coverage.json, coverage.xml | 기계 판독용 실행 줄/분기 |
| artifacts/coverage-html/index.html | 미실행 줄/분기를 살펴보는 HTML |
| artifacts/pytest.log | 각 TC의 DEBUG 이상 로그와 예상 오류 경로 |
| artifacts/tests-output.log | pytest 콘솔 요약과 커버리지 표 |
| artifacts/compile-output.log, dependencies-output.log | 정적/의존성 검사 결과 |
| artifacts/build-smoke.log | 별도로 수행한 빌드 결과의 시작/종료 로그 |

`verify.py`는 이전 JUnit/coverage를 새 결과로 오인하지 않도록 수정 시각을 확인한다.
검사 하나라도 실패하거나 보호 파일이 달라지면 종료 코드 1을 반환한다. CI는 실패한
실행에서도 `artifacts/`를 업로드한다. 이 문서는 위 날짜의 스냅샷이며 새 실행 후에는
산출물의 환경과 수치를 기준으로 갱신해야 한다.
