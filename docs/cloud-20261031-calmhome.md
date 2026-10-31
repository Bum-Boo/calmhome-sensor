# CalmHome 카메라 없는 재실 로직 시뮬레이션 점검 보고서 (2026-10-31)

브랜치 `claude/presence-logic-simulator-cptf5g`, 기준 `main` 6897516. 모든 센서 데이터는 합성 값이며 외부 서비스 호출은 없습니다. 저장소에는 AGENTS.md/CLAUDE.md/CONTRIBUTING 및 CI 설정이 없어 README와 기존 코드 관례를 따랐습니다.

## 1. 한 일 요약

- **시뮬레이터** `scripts/presence_sim.py`: `homeassistant/packages/calmhome.yaml`(+mock)을 그대로 읽어 패키지의 Jinja 템플릿을 렌더링하고, `delay_on/delay_off`, `availability`, 상태/시간 트리거 자동화, `for:` 대기, `input_datetime`을 모의 시계로 재현합니다(`scripts/presence_sim.py:144`, `:348`, `:463`). 합성 스트림 10종(빈 방, 정지 재실, 연속 움직임, 낙상 유사, 짧은 낙상 펄스, 센서 끊김, 노이즈, 재실 없는 낙상 신호, 낙상 센서만 끊김, 재실 중 문 열림)을 `STREAMS`(`:526`)로 제공하고 `replay()`(`:581`)로 재생합니다. CLI: `python scripts/presence_sim.py sensor_dropout`.
- **실제 HA 교차 검증** `scripts/ha_runtime_check.py`: Home Assistant core를 프로세스 안에서 임시 설정 디렉터리로 띄우고(장치가 이미 재실을 보고하는 상태의 부팅은 하위 프로세스에서 한 번 더) 합성 상태를 넣어 17개 항목을 확인합니다(선택 실행, 별도 venv에 `homeassistant` 필요). 시뮬레이터의 HA 의미론(naive datetime 처리, `as_local`, `int` 필터, 존재하지 않는 엔티티 = `unknown` 등)은 HA 2026.2.3에서 직접 확인했습니다.
- **테스트**: `tests/test_presence_sim.py`, `tests/test_config_handling.py`, `tests/test_template_entities.py` 추가, `tests/test_simulate_events.py` 확장. Jinja2가 없으면 시뮬레이터 테스트 2개 파일은 skip됩니다.
- **결함 수정 + 문서 정비**(아래 표). 커밋은 수정 단위로 분리했습니다.
- **독립 리뷰**: 수정 후 별도 서브에이전트가 diff를 검토해, 제 4번 수정(`from: "off"`)이 만든 회귀(부팅 직후 거짓 장시간 비활동, 아래 18번)와 시뮬레이터의 부팅 모델 한계(19번), 문서 불일치(20번), 상태 우선순위 문제(21번)를 찾았습니다. 모두 직접 재현한 뒤 수정하고 회귀 테스트를 추가했습니다.

## 2. 발견 사항

| # | 분류 | 내용 | 위치 | 조치 |
|---|---|---|---|---|
| 1 | 검증된 결함 | 템플릿 `sensor`에 `entity_category`가 있어 HA가 **template sensor 블록 전체를 거부** → `sensor.calmhome_room_state`, 마지막 활동 시간, 개인정보 상태가 아예 생성되지 않음. HA `check_config`는 오류를 로그로만 남기고 종료 코드 0. | `homeassistant/packages/calmhome.yaml:284` | 옵션 제거, `validate_template_entities()`가 HA가 거부하는 옵션을 검출(`scripts/validate_configs.py:99`, `:281`) |
| 2 | 검증된 결함 | `input_datetime`(naive 로컬 시각)을 `as_datetime().isoformat()`으로 timestamp 센서에 넣어 HA가 "timestamp without timezone"으로 거부 → 마지막 활동 시간이 항상 `unknown`, **실제 모드에서 장시간 비활동이 절대 켜지지 않음**(mock에서도 마지막 활동 표시 불가). | `calmhome.yaml:268`, `:272` | `as_local(as_datetime(...))` |
| 3 | 검증된 결함 | 활동 시각을 신호가 켜질 때만 기록 → 계속 움직이는 사람이 임계값을 넘기면 "long inactivity"로 표시될 수 있음(2번에 가려져 있던 문제). | `calmhome.yaml:220`, `:299-316` | 움직임 신호가 on이면 비활동 아님, 움직임이 멈춘 시점도 활동으로 기록 |
| 4 | 검증된 결함 | 센서 장치가 끊기면(엔티티 `unavailable`) 모든 신호가 off가 되어 방 상태가 **`stable`(빈 방처럼)** 으로 표시. 재연결(unavailable→on)이 새 활동으로 기록되어 비활동 타이머가 초기화. 낙상 센서만 끊긴 경우는 offline으로도 잡히지 않음. | `calmhome.yaml:78-146`, `:168`, `:240`, `:309` | 신호에 `availability` 추가, Sensor Offline에 radar/낙상 신호 `unavailable` 포함, 방 상태 `sensor offline`(낙상 의심·장시간 비활동 다음 우선순위), 기록 트리거 `from: "off"` |
| 5 | 검증된 결함 | mock 모드에서 센서 오프라인을 시험할 방법이 없음(README의 "모든 상태를 mock으로" 주장과 불일치). | `calmhome_mock.yaml:20`, `calmhome.yaml:164` | `sensor_offline` mock 시나리오 추가, 검증기 필수 목록에 추가 |
| 6 | 검증된 결함 | 검증기: 빈 섹션(`input_boolean:` 등)은 `TypeError`, 파싱 불가 매핑 파일은 `YAMLError` 트레이스백으로 **크래시**. 사용자의 `config/entities.local.yaml`은 전혀 검사하지 않아 `sensor.wrong domain` 같은 값도 "Validation passed". | `scripts/validate_configs.py:144-262` | 오류를 보고서로 반환, 엔티티 ID 형식·도메인 검사, local 매핑 파일이 있으면 검사 |
| 7 | 검증된 결함 | `python scripts/presence_sim.py` 직접 실행 시 `ModuleNotFoundError`(본 작업 중 생긴 문제, 커밋 전 CLI 테스트로 확인). | `scripts/presence_sim.py` | 직접 실행 지원, Jinja2 없으면 안내 메시지 |
| 8 | 검증된 결함(문서) | `input_text` 매핑 헬퍼와 `input_number` 임계값에 `initial:`이 있어 **UI에서 바꾼 값이 재시작 시 초기화**됨(HA 2026.2 `input_text/__init__.py:268`, `input_number/__init__.py:284` 확인). 문서는 UI에서 바꾸라고 안내. | `calmhome.yaml:7`, `docs/INSTALL_HOME_ASSISTANT.md` | 패키지 파일의 `initial:`을 고치도록 주석·문서 수정(동작 변경은 하지 않음: `initial` 제거 시 임계값 기본이 최소값 15분이 됨) |
| 9 | 검증된 결함(문서) | 번역 README 3종의 출처 링크가 옛 저장소 `Wifi-home-protector`를 가리킴(영문은 7833965에서 수정됨). | `docs/README.{ko,ja,zh-CN}.md:58` | `calmhome-sensor`로 수정 |
| 10 | 정적 위험 | HA는 ESPHome 엔티티 ID에 장치 이름을 접두사로 붙임(`entity_registry.py:447-451`). 예시 설정이면 `binary_sensor.calmhome_presence_calmhome_presence_detected`처럼 되어 패키지 기본값과 불일치할 가능성이 큼. 실제 장치로는 미확인. | `docs/INSTALL_ESPHOME.md`, `docs/HARDWARE.md` | 문서에 경고 추가. 수정 후에는 매핑 전 상태가 `sensor offline`으로 정직하게 표시됨 |
| 11 | 정적 위험 | radar 모듈 UART가 멈추고 ESP32는 연결 상태로 남으면 마지막 값이 유지되어 "stale"을 감지할 수 없음(HA 쪽 정보 부족). | README Limitations | 문서화. 장치 측 heartbeat 필요 |
| 12 | 정적 위험 | 재실 신호 노이즈(선풍기·커튼)가 off→on마다 활동으로 기록되어 장시간 비활동이 늦어질 수 있음. 1초 단위 노이즈는 움직임 디바운스(2초)로 걸러지지만 재실 신호에는 디바운스가 없어 방 상태가 깜빡임. | `tests/test_presence_sim.py`(`test_noisy_presence_flicker_counts_as_activity`) | 테스트로 동작 고정, README에 한계 명시 |
| 13 | 검증된 결함 → 18번에서 처리 | 새로 설치하면 `input_datetime` 기본값이 오늘 0시. | `calmhome.yaml:58-61` | 18번 참조 |
| 14 | 정적 위험 | ESPHome 2026.10.1 `esphome config`는 두 예시 모두 통과하나 OTA password 방식에 대해 encryption 권장 경고. MR60FDA2 예시 UART(tx GPIO17/rx GPIO16)가 XIAO ESP32C6 키트 배선과 맞는지는 하드웨어 없이 확인 불가. | `esphome/*.yaml` | 보고만 함 |
| 15 | 정적 위험 | `sensor_online`은 한 장치만 매핑 가능. 두 번째 장치(MR60FDA2)는 엔티티가 `unavailable`이 될 때만 offline으로 잡힘(4번 수정). 문 센서 `unavailable`은 진단 카드에만 보이고 offline에는 포함하지 않음. | `calmhome.yaml:168` | 문서화 |
| 16 | 이미 처리됨 | 재실 없이 낙상 신호만 있어도 `fall suspected` 표시(안전 우선), 10초짜리 낙상 펄스는 30초 재확인으로 알림 없음, 빈 방에서 문 열림은 이벤트 아님. | 기존 템플릿 | 테스트 추가(`test_conflicting_fall_without_presence_still_reports_fall`, `test_short_fall_blip_is_not_reported`) |
| 17 | 문제 아님 | `simulate_events.py`는 디바운스 이후 상태를 받으므로 5초 시점에 `fall suspected`를 출력함(실제는 30초 후). | `scripts/simulate_events.py:1-7` | docstring에 명시, 패키지 방 상태 템플릿과의 전 조합 일치 테스트 추가 |
| 18 | 검증된 결함(본 작업의 회귀, 리뷰에서 발견) | 4번의 `from: "off"` 이후, HA 시작 시 이미 사람이 있으면(unknown→on) 활동이 기록되지 않고 저장값은 0시 기본값 → **부팅 직후 `long inactivity`와 알림**. 센서가 끊긴 동안 들어와 앉은 경우도 오래된 활동 시각으로 판정. 실제 HA에서 재현(`last=...15:00:00+00:00`, room `long inactivity`). | `calmhome.yaml:326` | `CalmHome Activity Baseline` 자동화: HA 시작 시 활동 기준을 지금으로, 재연결 시 max(저장값, 끊김 시작 시각)으로. 비활동은 마지막 시작/끊김 이전부터는 세지 않음(끊긴 시간 자체는 비활동으로 셈) |
| 19 | 검증된 결함(테스트 도구) | 시뮬레이터가 장치 엔티티 없이 시작해 첫 프레임이 off→on이 되어 18번을 가림. | `scripts/presence_sim.py` | `initial_states`, `homeassistant start` 트리거, 트리거 변수 지원 |
| 20 | 검증된 결함(문서) | 문서가 문/거리 엔티티 `unavailable`도 offline으로 잡는다고 서술했으나 코드는 presence/movement/still/fall만 검사. 런타임 테스트 9번의 "1분 분리"는 HA가 끊김을 알아채기 전에 끝날 수 있음(ESPHome keepalive, 기억에 의존한 추정). | `docs/INSTALL_HOME_ASSISTANT.md`, `docs/RUNTIME_TEST_PLAN.md` | 문구 수정, 테스트 절차를 "offline 표시를 확인한 뒤 재연결"로 변경 |
| 21 | 검증된 결함 | 별도 낙상 센서만 끊긴 상태에서 장시간 비활동 알림이 나가도 방 상태는 `sensor offline`으로 표시되어 알림과 화면이 어긋남. | `calmhome.yaml:238-241`, `scripts/simulate_events.py` | 우선순위를 fall → long inactivity → sensor offline으로 변경(재실 센서가 끊기면 long inactivity는 어차피 off) |
| 22 | 정적 위험 | 시뮬레이터는 상태 템플릿 렌더 오류를 `unavailable`로 처리하지만 HA는 availability 템플릿이 있으면 `unknown`으로 둠. 현재 패키지에는 영향 없음. | `scripts/presence_sim.py` `_evaluate` | 보고만 함 |

## 3. 실행한 명령과 결과 (이 VM, Python 3.13.18)

| 명령 | 변경 전 (`main`) | 변경 후 (브랜치) |
|---|---|---|
| `python -m pip install -r requirements.txt` (PyYAML 6.0.3, pytest 9.2.0) | 성공 | 성공 |
| `python -m pytest tests` (Jinja2 없음, requirements만) | 17 passed | 29 passed, 2 skipped |
| `python -m pytest tests` (+ Jinja2 3.1.6) | 17 passed | 60 passed |
| 브랜치의 테스트·스크립트 + `main`의 `homeassistant/` 패키지 | 21 failed, 39 passed | — |
| `python scripts/validate_configs.py` | Validation passed (단, 새 검사 기준으로는 entity_category 오류) | Validation passed |
| `python scripts/simulate_events.py fall_suspected` / `normal_activity` | 성공 | 성공 (+ `sensor_dropout`) |
| `hass --script check_config` (HA 2026.2.3, 합성 config) | 종료 코드 0이지만 `Invalid config for 'template' ... entity_category` 로그, sensor 블록 누락 | 종료 코드 0, 오류 없음 |
| `python scripts/ha_runtime_check.py` (HA 2026.2.3) | `main` 패키지: 4 passed, 13 failed / 리뷰 전 브랜치(09613d1): 13 passed, 4 failed | 17 passed, 0 failed |
| `esphome config esphome/ld2410_presence_example.yaml` / `mr60fda2_fall_example.yaml` (ESPHome 2026.10.1, 가짜 secrets) | 둘 다 rc=0 (OTA 경고) | 변경 없음 |
| `ruff check scripts tests` (임시 설치, 저장소에 설정 없음) | 6건 | 19건, 대부분 새 파일의 스타일 규칙(UP017 `datetime.UTC`, EXE001 등; 기존 코드 관례 `timezone.utc` 유지) |
| `mypy scripts --ignore-missing-imports` (임시 설치) | 1건 (기존 `validate_configs.py` report dict 타입) | 같은 기존 1건 + `homeassistant` 미설치로 인한 import 2건 |

저장소에는 lint/type-check/build 명령이 정의되어 있지 않습니다(`Makefile`, `package.json`은 test/validate/simulate만). ruff/mypy는 참고용으로만 실행했고 저장소 의존성에는 추가하지 않았습니다.

## 4. 이 VM에서 확인하지 못한 것

- 실제 LD2410/MR60FDA2/ESP32 장치, 배선, 펌웨어 플래시(`esphome compile`/업로드 미실행), 방 배치에 따른 레이더 동작.
- 실제 ESPHome 장치를 HA에 붙였을 때의 엔티티 ID(접두사 여부는 소스 추적만), 실제 Wi-Fi 끊김 시 상태 전이 타이밍.
- Home Assistant OS/Green, Supervisor 애드온, 실제 모바일 앱 알림(`notify.notify`는 스텁으로 대체), 대시보드 UI 렌더링(GUI 미확인), 장기간 실행과 재시작 후 상태 복원.
- HA 2026.2.3 외 버전, Windows/macOS(PowerShell 안내 포함).
- 시뮬레이터는 HA의 모든 동작(템플릿 rate limit, 자동화 실행 순서의 미세한 경쟁 등)을 재현하지 않습니다. 핵심 17개 시나리오만 실제 HA로 교차 확인했습니다. 실제 HA 검사는 시간을 빨리 돌릴 수 없어 저장된 활동 시각을 과거로 설정하는 방식으로 경과 시간을 흉내 냈습니다.

## 5. 소유자를 위한 다음 단계

1. 이 브랜치를 검토 후 병합하고, 실제 HA에 패키지를 다시 넣어 `sensor.calmhome_room_state`가 생기는지 먼저 확인하세요(1번 결함 때문에 기존 설치에는 이 엔티티가 없었을 가능성이 높습니다).
2. 장시간 비활동이 "마지막 HA 시작 또는 센서 끊김 시작 이전부터는 세지 않는다"는 새 규칙(18번)이 돌봄 의도에 맞는지 판단하세요. 잦은 Wi-Fi 끊김은 알림을 늦출 수 있습니다. 더 정밀하게 하려면 끊김 직전 재실 여부를 helper에 저장하는 방식을 검토할 수 있습니다.
3. `docs/RUNTIME_TEST_PLAN.md`의 새 9~11번(끊김 중 정지 재실, 실제 장시간 비활동, mock 센서 오프라인)을 실제 방에서 수행하세요.
4. Developer Tools에서 실제 엔티티 ID를 확인해 `calmhome.yaml`의 `initial:` 값에 반영하고 `python scripts/validate_configs.py`로 확인하세요.
5. `Jinja2`를 `requirements.txt`(또는 개발용 requirements)에 넣을지 결정하세요. 이번 작업에서는 의존성 파일을 바꾸지 않아 기본 설치에서는 시뮬레이터 테스트가 skip됩니다.
6. GitHub Actions 등 CI에 `validate_configs.py`, `pytest`(Jinja2 포함)를 추가하고, 가능하면 주기적으로 `ha_runtime_check.py`와 `esphome config`를 돌리세요. HA `check_config`는 이번 오류에서 종료 코드 0이었으므로 로그의 `Invalid config`도 확인해야 합니다.
7. ESPHome 예시의 OTA를 password 대신 encryption으로 바꾸는 것과 MR60FDA2 UART 핀을 키트 문서와 대조하는 것을 검토하세요.
8. CHANGELOG/버전은 릴리스 메타데이터라 손대지 않았습니다. 릴리스 시 반영하세요.
