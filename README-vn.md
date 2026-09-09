# Deye SG06 RS485 Monitor

Cong cu **monitor** bien tan Deye SG05/SG06 qua **Modbus RTU (RS485)**: IRIV MQTT, ESPHome, emulator, va (sap toi) ESP32 UART→RS485.

> English: [README.md](README.md)

**Du an chi em:** [jk-pb-rs485-monitor](../jk-pb-rs485-monitor) — BMS JK-PB* (bus/baud rieng).

## Da thu nghiem

**Deye 6 kW SG06** + pin **16S 51.2 V 100 Ah** (JK qua **CAN**). Modbus inverter **9600**, slave **1** → MQTT `iriv/ivt/...`.

## Nhanh

```bash
pip install -r requirements.txt
python _gen_iriv_jobs.py
python deye-sg06-ivt-emu.py --port COM35 --debug --scenario day
```

IRIV: import `iriv-ioc-config.json`. Toi da **26** job bat (job 27 → reboot + mat config). V/I/P = 1 s; khong poll PV2.

ESP32: xem `docs/esp32/README.md`.
