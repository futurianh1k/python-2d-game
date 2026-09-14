# TC 설계와 pytest 구조

## 설계 원칙

정상 입력만 확인하지 않고 동치분할, 경계값, 상태 전이, 오류 주입, 저장 후 복원을
함께 사용한다. 한 테스트 함수가 하나의 관찰 가능한 계약을 검증하도록 나누며
영웅·맵·난이도·잘못된 필드는 `parametrize` 또는 fixture parameter로 독립 수집한다.
실행 건수는 아래 설계 행 수와 다르며 JUnit의 `tests` 값으로 확인한다.

| TC | 대상 / 기법 | 전제·입력·절차 | 판정 기준 | 구현 파일 / 함수 식별자 |
| --- | --- | --- | --- | --- |
| F01 | UTF-8/정상 왕복 | 한글·이모지·중첩 JSON 저장 후 읽기 | 의미 동일, UTF-8 원문, 종료 개행, INFO/DEBUG 로그, 본문 비노출 | unit/test_json_files: utf8_round_trip |
| F02 | 읽기 오류 동치분할 | 없는 파일 / 잘린 JSON / 잘못된 UTF-8 | 원래 예외 타입, 경로와 traceback ERROR 로그 | unit/test_json_files: read_failures |
| F03 | 쓰기 장애 4단계 | 임시 생성 / 부분 직렬화 / fsync / replace에 ENOSPC 주입 | 원본 SHA-256 동일, 예외 객체 동일, 임시 파일 없음, 성공 로그 없음 | unit/test_json_files: failed_write |
| F04 | 직렬화 경계 | 지원하지 않는 객체 / NaN | 새 대상·임시 파일 미생성, TypeError/ValueError | unit/test_json_files: unserializable_data |
| F05 | 덮어쓰기 | 기존 정상 JSON에 새 값 저장 | 새 JSON 전체만 남음 | unit/test_json_files: successful_overwrite |
| F06 | 이중 장애 | 직렬화 실패 + 임시 파일 unlink 거부 | 최초 TypeError 유지, 정리 경고, 원본/대상 미생성 | unit/test_json_files: cleanup_failure |
| S01 | 구형 하위 호환 | 선택 필드 4개 제거 후 복원 | 기본값 적용, 다시 직렬화 가능 | unit/test_player_files: legacy_optional |
| S02 | 필드 타입·경계 | level 0/True/1.5, 음수 exp/money, 잘못된 목록·enum 등 | SaveFileError, 실패 필드 분리 | unit/test_player_files: invalid_field |
| S03 | 루트/필수 값 | null, 배열, 빈 객체, 필수 필드 누락 | 스키마 오류로 거부 | unit/test_player_files: invalid_root |
| S04 | 허용 경계 | level=1, exp/money=0, 슬롯 None, 추가 필드 | 정상 복원, None과 0 구분 | unit/test_player_files: zero_boundaries |
| S05 | 폴더 혼합 | 2/10/named JSON + 메모/tmp/20.json 디렉터리 | 숫자순→이름순, 다음 번호 21, 무관 파일 제외 | unit/test_player_files: mixed_directory |
| S06 | 위치·파일명 | 새/기존 중첩 폴더, 양 OS의 경로 탈출/절대 경로, 심볼릭 링크 | 생성 재사용 가능, 경로/링크 거부, 외부 파일 보존 | unit/test_player_files: directory, names, symlink |
| S07 | 스키마 오류 파일 | 잘못된 hero와 기존 정상 파일 갱신 실패 | 기존 바이트 동일, 경로만 로그, 원문 비노출 | unit/test_player_files: invalid_save, failed_validation |
| L01 | 레벨·중복·UTF-8 | 로깅 재설정 2회, DEBUG/한글 INFO 출력 | INFO 한 번, DEBUG 제외, 파일·콘솔 확인 | unit/test_logging_and_crashes: utf8_levels |
| L02 | 회전 경계 | 테스트에서만 작은 최대 크기/백업 2개 | 백업 수·크기 제한, UTF-8, 최신 기록 유지 | unit/test_logging_and_crashes: rotating_log |
| L03 | traceback 영속성 | 실제 예외를 logger.exception으로 기록 | 파일에 ERROR/Traceback/예외 타입·메시지 | unit/test_logging_and_crashes: traceback |
| L04 | 재설정 실패 | 새 로그 부모가 디렉터리가 아닌 파일 | 예외 전달, 기존 핸들러 계속 동작 | unit/test_logging_and_crashes: failed_log_reconfiguration |
| C01 | 비상 저장 결정표 | 플레이/일시정지 × 백업 성공/실패 | 최초 예외 객체 유지, 원래 시간 전달, 상황별 로그 | unit/test_logging_and_crashes: crash_backup |
| C02 | 캐릭터 없음 | 메뉴 상태 또는 game_state=None에서 충돌 | 백업 미시도, 이유 경고 | unit/test_logging_and_crashes: crash_without_character |
| C03 | 초기화 중 실패 | pygame.init 이후 생성자 예외 | finally에서 SDL 종료 | unit/test_logging_and_crashes: partial_initialization |
| A01 | CLI 경계 | 기본값/1/0/일반 정수/음수/문자/잘못된 선택지 | 올바른 타입, 잘못된 인수는 exit 2 | unit/test_cli_and_input: integer, invalid_cli |
| A02 | 옵션 호환/실행 | 두 창 모드 표기, 로그 옵션, 시작 예외 | 전달 인수 일치, 로그 핸들 종료 | unit/test_cli_and_input: windowed, log_options, dispatch |
| I01 | 방향 상태 전이 | 좌→우→우 해제→좌 해제 | 우→좌→정지 | unit/test_cli_and_input: latest_direction |
| I02 | 이벤트 이상 | 반복 KEYDOWN, 대응 없는 KEYUP | 예외·잔여 이동 없음 | unit/test_cli_and_input: duplicate_keydown |
| I03 | 포커스 전이 | 이동+Q+Shift 후 WINDOWFOCUSLOST | 모든 held-key 상태 초기화 | unit/test_cli_and_input: focus_loss |
| G01 | 실제 이동 | 3영웅, 오른쪽 이동 후 해제 | x 증가, 해제 후 위치 고정 | integration/test_gameplay: movement |
| G02 | 실제 스킬 | 3영웅, 스폰 보호 종료 후 Q | 마나 감소와 쿨다운 활성 | integration/test_gameplay: cast |
| G03 | 일시정지 | 3영웅, 이동 중 정지/복귀 | 시간·위치 정지, 복귀 후 키 초기화 | integration/test_gameplay: pause |
| G04 | 저장·복원 상태 전이 | 3영웅 저장→구형 필드 제거→복원→2회 저장 | 영웅/레벨/돈/시간, 동일 파일명·파일 수 유지 | integration/test_gameplay: save_legacy_reload |
| G05 | 메뉴 선택 | 새 캐릭터 선택 / 손상 파일과 정상 파일 혼합 | 선택 영웅 또는 정상 저장 파일로 진입, 손상 원본 보존 | integration/test_gameplay: new_game, menu_skips |
| G06 | SDL 모드 | 전체 화면→창 모드 | 렌더링 지속, 창 크기 800×600 복귀 | integration/test_gameplay: fullscreen |
| G07 | 오디오/종료 | 없는 드라이버 / 2회 시작-QUIT | WARNING과 플레이 진입 / stale audio 없음, SDL 해제 | integration/test_gameplay: audio_unavailable, start_quit |
| M01 | 맵 전수 왕복 | 번들 JSON 각각 복사·직렬화·복원 | 의미 동일, 원본 SHA-256 동일, tmp 정리 | integration/test_files_and_editor: bundled_maps |
| M02 | 난이도 분할 | 난이도 1–4, 각 고정 seed | 벽·장식·NPC 존재, 월드 내부 스폰 | integration/test_files_and_editor: dungeons |
| M03 | 편집 저장 분기 | 스마트 그리드 있음/없음 | grid 문자열/null 보존, 플레이어 위치, 성공 로그 | integration/test_files_and_editor: editor_save |
| M04 | 편집 실행 | 실제 한 프레임 flip 후 QUIT 주입 | 1200×750 Surface, 정상 종료·로그 | integration/test_files_and_editor: editor_renders |
| M05 | 리소스 경로 | 외부 cwd, 프로젝트 상대/외부 절대 경로 | 번들 파일 발견, 절대 경로 그대로 | integration/test_files_and_editor: absolute_and_project |
| P01 | import/도움말 | 새 프로세스에서 import, 두 실행기의 --help | pygame 미로딩, exit 0 | integration/test_cli_process: importing, cli_help |
| P02 | CLI 실패 영속성 | 없는 --file과 --log-file 지정 | exit 1, 파일 ERROR/traceback/종료 로그, 가짜 저장 없음 | integration/test_cli_process: missing_save |
| P03 | 기존 도구 | 능력/소모품/적/아이템/전리품 출력 실행 | exit 0와 내용 존재 | integration/test_cli_process: data_utilities |

## fixture와 격리

`tests/conftest.py`는 테스트마다 cwd를 `tmp_path`로 옮기고 난수 상태를 복원한다.
실제 사용자 저장 파일은 이 위치에 있지 않다. `saved_data`는 매번 새 컨테이너를
반환해 parameter 사이의 오염을 막는다. `caplog`는 레벨/예외/메시지를 검사하고
`capsys`는 콘솔 중복을 검사한다.

`tests/integration/conftest.py`는 실제 `Main`, 이미지, 폰트, 음원을 사용한다.
`advance`는 입력을 첫 프레임에만 전달하고 16ms씩 시간을 진행한다. 반복 입력 자체를
가짜로 만들지 않고 실제 held-key 상태를 검사하기 위해서다. 종료 시에는 실제 앱과
같은 sound cleanup을 호출하고 `pygame.quit()` 한다. GUI를 실행하는 무한 루프는
QUIT을 주입해 유한하게 끝내며 CI 작업에도 10분 상한을 둔다.

`unit`, `integration`, `process` marker를 등록하고 `--strict-markers`,
`--strict-config`, `filterwarnings=error`를 적용한다. process는 integration의
일부이므로 두 마커의 건수를 단순 합산하면 중복된다. 현재 xdist는 구성하지 않았다.

## 판단의 한계

헤드리스 테스트는 실제 Surface/폰트/음원을 로드하지만 GPU, 창 관리자별 DPI,
스피커 출력 품질, 사람이 보는 픽셀 배치의 모든 정확성은 판정하지 않는다.
던전 4개 seed의 성공은 모든 랜덤 맵에 대한 증명이 아니다. 회전 테스트의 작은
임계값은 정책을 빨리 재현하는 장치이며 실제 설정은 1 MiB/백업 3개다.
심볼릭 링크 생성 권한이 없는 OS에서는 해당 TC만 이유를 명시하고 skip한다.

TC 함수와 fixture의 한국어 docstring은 전제·격리·주입 범위·assertion 근거를 설명한다.
표와 코드가 어긋나지 않도록 함수명을 기준으로 추적하며 실제 수집 목록은
`python -m pytest --collect-only -q`로 확인한다.

설계에 사용한 기능은 [pytest fixture 문서](https://docs.pytest.org/en/stable/builtin.html)와
[pytest 로깅 문서](https://docs.pytest.org/en/stable/how-to/logging.html)를 따른다.
