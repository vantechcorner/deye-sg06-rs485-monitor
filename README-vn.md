# Deye SG06 RS485 Monitor

Công cụ **monitor** biến tần Deye SG05/SG06 qua **Modbus RTU (RS485)**: IRIV MQTT, ESPHome, emulator, web dashboard, và (sắp tới) ESP32 UART→RS485.

> English: [README.md](README.md)

**Dự án chị em:** [jk-pb-rs485-monitor](../jk-pb-rs485-monitor) — BMS JK-PB* (bus/baud riêng). Emulator Pylon-style BMS nằm ở đó.

## Cấu trúc

| Thư mục | Nội dung |
|---------|----------|
| `iriv/` | Config IRIV + script gen job |
| `emulator/` | Slave Modbus Deye + `rs485_emu/` |
| `esphome/` | YAML NodeMCU |
| `homeassistant/` | Sensor MQTT |
| `web/` | Dashboard MQTT WebSocket |
| `docs/` | HANDOFF, ESP32, ảnh, PDF protocol |

## Đã thử nghiệm

**Deye 6 kW SG06** + pin **16S 51.2 V 100 Ah** (JK qua **CAN**). Modbus inverter **9600**, slave **1** → MQTT `iriv/ivt/...`.

## Nhanh

```bash
pip install -r requirements.txt
python iriv/_gen_iriv_jobs.py
python emulator/deye-sg06-ivt-emu.py --port COM35 --debug --scenario day
cd web && python -m http.server 8080
```

IRIV: import `iriv/iriv-ioc-config.json`. Tối đa **26** job bật (job 27 → reboot + mất config). V/I/P = 1 s; không poll PV2.

Dashboard web (MQTT WS): `web/` — mặc định broker `:9001`.

ESP32: xem `docs/esp32/README.md`.
