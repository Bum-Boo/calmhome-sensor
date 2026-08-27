# CalmHome Sensor

[English](../README.md) | [한국어](README.ko.md) | [日本語](README.ja.md) | [中文](README.zh-CN.md)

카메라·마이크·신원 인식 없이 방 단위의 재실 및 안전 상태를 확인하는 개인정보 보호 중심 Home Assistant + ESPHome 구성입니다. 재실, 움직임, 낙상 의심, 장시간 비활동, 문 열림을 단순 상태로 표시합니다.

> **안전 안내:** 이 프로젝트는 베타 단계의 가정 상태 보조 도구이며 의료기기, 응급 서비스 또는 낙상 보장을 제공하는 장치가 아닙니다. 실제 방에서 모든 센서와 알림을 검증하고 별도의 도움 요청 수단을 유지하세요.

## 개인정보 보호 및 안전 경계

- 모니터링 공간을 이용하는 모든 사람의 사전 동의를 받으세요.
- 처리는 로컬 네트워크의 Home Assistant와 ESPHome 안에서 수행하도록 설계되었습니다.
- 공유기는 네트워크 전송에만 사용하며 Wi-Fi 패킷 감청, 공유기 기반 감지, 투과 감지를 하지 않습니다.
- 카메라, 마이크, 얼굴·신원 인식, 실루엣, 원시 레이더 포인트 클라우드, 자격 증명 수집, 공개 포트 포워딩은 범위 밖입니다.
- 평소에는 진단 엔티티를 끄고 Wi-Fi 정보, API 키, 개인 엔티티 ID, 방별 메모를 커밋하지 마세요.
- 원격 접속은 직접 공개 대신 Tailscale 같은 VPN 또는 Home Assistant Cloud를 사용하세요.

배포 전 [개인정보 보호 모델](PRIVACY.md)과 [런타임 테스트 계획](RUNTIME_TEST_PLAN.md)을 읽으세요.

## 요구 사항

- Home Assistant 호스트(Home Assistant Green, Raspberry Pi, mini PC 등)
- ESPHome 호환 재실 센서([하드웨어 안내](HARDWARE.md)의 예시 참고)
- 선택 사항: 낙상 상태, PIR, 문 접점 센서
- 로컬 검증용 Python 3 및 `requirements.txt` 패키지

## 빠른 시작

```bash
python -m pip install -r requirements.txt
python scripts/validate_configs.py
python -m pytest tests
python scripts/simulate_events.py normal_activity
python scripts/simulate_events.py fall_suspected
```

1. `homeassistant/packages/calmhome.yaml`과 `calmhome_mock.yaml`을 추가합니다.
2. mock mode에서 모든 시나리오를 시험합니다.
3. `esphome/` 예시를 실제 센서에 맞게 수정합니다.
4. `config/entities.local.example.yaml`을 Git에서 제외되는 `config/entities.local.yaml`로 복사하고 실제 엔티티 ID를 매핑합니다.
5. `dashboards/calmhome_dashboard.yaml`을 가져오거나 재구성합니다.
6. [Home Assistant 설치](INSTALL_HOME_ASSISTANT.md), [ESPHome 설치](INSTALL_ESPHOME.md), [배치](SENSOR_PLACEMENT.md), [런타임 테스트](RUNTIME_TEST_PLAN.md)를 완료한 뒤 알림을 켭니다.

## 구성

`config/`는 엔티티 매핑, `dashboards/`는 대시보드 YAML, `esphome/`은 장치 예시, `homeassistant/packages/`는 실제·mock 패키지, `scripts/`와 `tests/`는 검증 도구를 담습니다.

## 제한 사항

- 모든 방과 센서 조합에서 실제 하드웨어가 검증된 것은 아닙니다.
- 낙상 의심과 장시간 비활동에는 오탐과 미탐이 있을 수 있습니다.
- 상태만으로 사람을 식별하거나 사건 원인을 알 수 없습니다.
- 가구, 커튼, 선풍기, 센서 위치가 바뀌면 다시 테스트해야 합니다.
- 직접 확인, 전문 돌봄, 화재·CO 경보기 또는 응급 시스템을 대체하지 않습니다.

## 출처 표기

포크, 데모, 글 또는 파생 작업을 공개할 때 [@Bum-Boo](https://github.com/Bum-Boo)와 [원본 저장소](https://github.com/Bum-Boo/Wifi-home-protector)를 함께 언급해 주시면 감사하겠습니다. 이는 예의상 부탁드리는 크레딧 요청이며 추가 라이선스 조건이나 제한이 아닙니다.
