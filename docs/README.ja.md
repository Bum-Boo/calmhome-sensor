# CalmHome Sensor

[English](../README.md) | [한국어](README.ko.md) | [日本語](README.ja.md) | [中文](README.zh-CN.md)

カメラ、マイク、個人識別を使わず、部屋単位の在室・安全状態を確認する privacy-first の Home Assistant + ESPHome 構成です。在室、動き、転倒疑い、長時間の無活動、ドア開放を単純な状態として表示します。

> **安全上の注意:** 本プロジェクトはベータ版の家庭内状態補助ツールであり、医療機器、緊急サービス、転倒検知を保証する装置ではありません。対象の部屋で全センサーと通知を検証し、別の救助要請手段を維持してください。

## プライバシーと安全境界

- 監視空間を利用する全員から事前に同意を得てください。
- 処理はローカルネットワーク上の Home Assistant と ESPHome 内で行う設計です。
- ルーターは通信専用です。Wi-Fi パケット盗聴、ルーター型センシング、壁越し検知は行いません。
- カメラ、マイク、顔・個人認識、シルエット、raw radar point cloud、認証情報収集、公開 port forwarding は対象外です。
- 通常は診断 entity を無効にし、Wi-Fi 情報、API key、個人 entity ID、部屋固有メモを commit しないでください。
- 遠隔接続には直接公開ではなく Tailscale 等の VPN または Home Assistant Cloud を使ってください。

導入前に[プライバシーモデル](PRIVACY.md)と[実行時テスト計画](RUNTIME_TEST_PLAN.md)を確認してください。

## 要件

- Home Assistant host（Home Assistant Green、Raspberry Pi、mini PC など）
- ESPHome 対応在室センサー（[ハードウェアガイド](HARDWARE.md)参照）
- 任意: 転倒状態、PIR、ドア接点センサー
- ローカル検証用 Python 3 と `requirements.txt` の package

## クイックスタート

```bash
python -m pip install -r requirements.txt
python scripts/validate_configs.py
python -m pytest tests
python scripts/simulate_events.py normal_activity
python scripts/simulate_events.py fall_suspected
```

1. `homeassistant/packages/calmhome.yaml` と `calmhome_mock.yaml` を追加します。
2. mock mode ですべての scenario を試します。
3. `esphome/` の例を実機に合わせます。
4. `config/entities.local.example.yaml` を Git 除外済みの `config/entities.local.yaml` にコピーし、実 entity ID を設定します。
5. `dashboards/calmhome_dashboard.yaml` を import または再構築します。
6. [Home Assistant](INSTALL_HOME_ASSISTANT.md)、[ESPHome](INSTALL_ESPHOME.md)、[配置](SENSOR_PLACEMENT.md)、[実行時テスト](RUNTIME_TEST_PLAN.md)の各ガイドを完了してから通知を有効にします。

## 構成

`config/` は entity mapping、`dashboards/` は dashboard YAML、`esphome/` は device 例、`homeassistant/packages/` は実運用・mock package、`scripts/` と `tests/` は検証ツールです。

## 制限事項

- 全ての部屋・センサー構成で実機検証済みではありません。
- 転倒疑いと長時間無活動には誤検知・見逃しがあります。
- 状態だけでは人物や事象の原因を特定できません。
- 家具、カーテン、ファン、センサー位置を変えた場合は再テストが必要です。
- 直接確認、専門ケア、火災・CO 警報器、緊急システムの代替ではありません。

## クレジット

フォーク、デモ、記事、派生物を公開する際は、[@Bum-Boo](https://github.com/Bum-Boo) と[元のリポジトリ](https://github.com/Bum-Boo/Wifi-home-protector)への言及をお願いします。これは礼儀としてのお願いであり、追加のライセンス条件や制限ではありません。
