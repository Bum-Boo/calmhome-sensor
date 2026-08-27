# CalmHome Sensor

[English](../README.md) | [한국어](README.ko.md) | [日本語](README.ja.md) | [中文](README.zh-CN.md)

无需摄像头、麦克风或身份识别的隐私优先 Home Assistant + ESPHome 房间状态方案。它以简单状态显示有人、活动、疑似跌倒、长时间无活动和开门事件。

> **安全提示：** 本项目是测试阶段的家庭状态辅助工具，不是医疗设备、紧急服务或能够保证识别跌倒的设备。请在目标房间逐项验证传感器和通知，并保留独立的求助方式。

## 隐私与安全边界

- 必须事先取得所有可能进入监测空间人员的知情同意。
- 系统设计为在本地网络中的 Home Assistant 与 ESPHome 内处理数据。
- 路由器仅用于网络传输；项目不嗅探 Wi-Fi 流量，不使用路由器感知或穿墙感知。
- 摄像头、麦克风、人脸/身份识别、人体轮廓、原始雷达点云、凭据采集和公网端口转发均不在范围内。
- 日常使用时关闭诊断实体；不要提交 Wi-Fi 信息、API 密钥、个人实体 ID 或房间隐私记录。
- 远程访问请使用 Tailscale 等 VPN 或 Home Assistant Cloud，不要直接暴露 Home Assistant。

部署前请阅读[隐私模型](PRIVACY.md)和[运行测试计划](RUNTIME_TEST_PLAN.md)。

## 要求

- Home Assistant 主机（如 Home Assistant Green、Raspberry Pi 或迷你电脑）
- ESPHome 兼容的人体存在传感器（参见[硬件指南](HARDWARE.md)）
- 可选：跌倒状态、PIR 或门磁传感器
- 用于本地验证的 Python 3 与 `requirements.txt` 中的软件包

## 快速开始

```bash
python -m pip install -r requirements.txt
python scripts/validate_configs.py
python -m pytest tests
python scripts/simulate_events.py normal_activity
python scripts/simulate_events.py fall_suspected
```

1. 添加 `homeassistant/packages/calmhome.yaml` 和 `calmhome_mock.yaml`。
2. 在 mock mode 中测试全部场景。
3. 根据实际传感器调整 `esphome/` 中的示例。
4. 将 `config/entities.local.example.yaml` 复制为已被 Git 忽略的 `config/entities.local.yaml`，并填写真实实体 ID。
5. 导入或重建 `dashboards/calmhome_dashboard.yaml`。
6. 完成 [Home Assistant](INSTALL_HOME_ASSISTANT.md)、[ESPHome](INSTALL_ESPHOME.md)、[布置](SENSOR_PLACEMENT.md)与[运行测试](RUNTIME_TEST_PLAN.md)指南后再启用通知。

## 项目结构

`config/` 保存实体映射，`dashboards/` 保存面板 YAML，`esphome/` 保存设备示例，`homeassistant/packages/` 保存正式与 mock package，`scripts/` 和 `tests/` 提供验证工具。

## 局限

- 并非所有房间和传感器组合都经过真实硬件验证。
- 疑似跌倒和长时间无活动都可能误报或漏报。
- 状态摘要无法识别人，也不能说明事件原因。
- 家具、窗帘、风扇或传感器位置变化后必须重新测试。
- 本项目不能替代人工确认、专业照护、烟雾/一氧化碳报警器或紧急系统。

## 致谢与署名

如果您公开分支、演示、文章或衍生作品，烦请提及 [@Bum-Boo](https://github.com/Bum-Boo) 和[原始仓库](https://github.com/Bum-Boo/Wifi-home-protector)。此项仅为礼貌性的署名请求，不构成额外的许可条件或限制。
