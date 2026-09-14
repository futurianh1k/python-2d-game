# 진단과 리팩터링 기록

대상은 Python 3.14 전환이 완료된 `7c5c96b` 커밋의 코드다. 기존 unittest 6개는
재실행에서 모두 통과했다. 정상 흐름이 통과하는 상태에서도 파일 손상·백업 실패 같은
예외 경로는 드러나지 않아, 해당 위험을 우선으로 재현하고 리팩터링했다.

## 확인한 문제와 처리

| ID | 재현 조건 / 확인 근거 | 원인과 변경 | 회귀 TC 위치 |
| --- | --- | --- | --- |
| D01 | 저장 폴더에 `notes.txt`가 있으면 다음 번호 계산에서 `ValueError` | 모든 파일을 정수 이름으로 해석하던 코드를 분리. 일반 JSON만 목록화하고 숫자/사용자 이름을 안정적으로 정렬 | `tests/unit/test_player_files.py`의 mixed_directory |
| D02 | 기존 `1.json`에 직렬화 불가능한 값을 저장하면 예외 후 원본 바이트가 달라짐 | 직접 `open('w')`하던 쓰기를 같은 폴더의 임시 파일 → fsync → 닫기 → replace로 공통화 | `tests/unit/test_json_files.py`의 failed_write |
| D03 | 게임 루프 `RuntimeError` 뒤 비상 저장 `OSError`가 나면 호출자는 OSError만 받음 | 백업 실패를 별도로 기록하고 최초 예외를 bare raise로 보존. 플레이 시간도 저장하며 일시정지 래퍼 내부 시간까지 처리 | `tests/unit/test_logging_and_crashes.py`의 crash_backup |
| D04 | 코드 추적상 `--file` 복원 시 `character_file=None` 전달 | 복원 파일명을 유지해 이후 저장이 새 번호를 만들지 않게 수정 | `tests/integration/test_gameplay.py`의 save_legacy_reload |
| D05 | 메뉴에서 손상 JSON 하나를 읽으면 전체 초기화 실패 | JSON 구조 검증 추가. 메뉴는 읽기 실패 파일을 경고와 함께 건너뛰며 파일명/캐릭터 인덱스를 동시에 구성 | player_files의 invalid_save, gameplay의 menu_skips_corrupt |
| D06 | `Grid`가 없는 편집기 저장에서 `self.grid.serialize()` 호출 | 그리드 없는 맵은 JSON `null`로 보존 | `tests/integration/test_files_and_editor.py`의 editor_save |
| D07 | 창 포커스 이동 후 KEYUP을 받지 못하는 입력 전이 | `WINDOWFOCUSLOST`에서 이동·스킬·Shift 상태 초기화 | `tests/unit/test_cli_and_input.py`의 focus_loss |
| D08 | 같은 인터프리터의 게임 재시작 시 사운드 전역 캐시 잔류 | `shutdown_sound_player()`에서 음원·캐시·음소거 상태 정리. 실제 종료와 fixture가 같은 정리 함수를 사용 | gameplay의 start_quit_can_repeat |
| D09 | print/RuntimeWarning 중심이라 로그 레벨·파일 기록·회전을 확인하기 어려움 | lifecycle, 파일 I/O, 저장 스키마, 오디오 부재를 logging으로 기록. CLI에 파일/레벨 옵션과 핸들러 종료 추가 | logging_and_crashes, cli_process |
| D10 | 문자열 subprocess 시나리오 내부 assert는 실패 행동과 영웅을 세분화하기 어려움 | 단위/통합 디렉터리, fixture, parameter, marker로 pytest 재구성. 프로세스는 CLI 경계만 사용 | `tests/` 전체 |

D01–D03은 변경 전 임시 디렉터리에서 실제 재현했다. 나머지는 코드 경로 분석 후
전용 회귀 테스트를 추가했다. 모든 항목을 Python 버전 때문에 새로 발생한 오류라고
분류하지 않는다. 오래된 구조에서 발견한 일반적인 안정성 문제도 포함한다.

## 경계와 책임

- `pythongame/json_files.py`: UTF-8, JSON 직렬화, 임시 파일, 교체, I/O 로그.
- `pythongame/player_file.py`: 캐릭터 구조/파일명/목록 정책. 저장 위치를 주입받는다.
- `pythongame/logging_config.py`: 앱 소유 콘솔/회전 파일 핸들러 설정과 정리.
- `run.py`, `map_editor.py`: GUI import 전에 인수 검증, 실행 전 로그 설정, 종료 시 닫기.
- `Main.main_loop()`: 최초 충돌 기록과 비상 저장. 백업 실패가 원인을 바꾸지 않게 한다.

불필요한 전체 게임 엔진 재작성은 하지 않았다. 데이터 등록 전역 상태는 남아 있고,
통합 fixture는 명시적인 직렬 실행·오디오 정리·고정 난수로 그 상태를 관리한다.

## 호환성과 남은 범위

기본 저장 위치 `현재 작업 폴더/saved_characters`와 JSON 필드명은 유지한다. 구형
선택 필드 누락은 허용한다. 일반 JSON 이외의 파일과 링크는 메뉴 후보에서 제외한다.
직접 `--file`로 지정한 파일이 잘못되면 실패 종료와 오류 로그를 남긴다.

스키마 검증은 구조/기본 범위/열거형 이름을 다룬다. 아이템 능력치 문자열의 모든 의미,
영웅별 특성 티어 수·게임 밸런스의 모든 제약까지 검증하는 것은 아니다. 여러 프로세스의
동시 새 저장 번호 예약, 전원 장애 중 디렉터리 메타데이터 내구성, 악의적인 동시 경로
교체 방어는 이번 파일 교체 보장의 범위 밖이다. 임시 파일 정리 실패는 경고를 남기며
최초 오류를 보존한다.

전체 화면 크기는 SDL 드라이버가 제공하는 모드에 따라 달라진다. 첫 pytest 실행에서
`전체 화면도 반드시 800×600`이라는 테스트 가정이 실패했으므로, 전체 화면에서는
렌더링/최소 논리 크기, 창 모드에서는 정확한 800×600 복귀를 판정하도록 수정했다.

상세 TC는 [test-design.md](test-design.md), 실행 증거는 [validation.md](validation.md)를 참고한다.
