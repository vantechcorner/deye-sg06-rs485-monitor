# ESP32 / ESP32-S3 + UART → RS485 poller (Deye)

**Status:** guide stub — implement next.

## Goal

Run Modbus RTU **master** on ESP32/S3 (Hardware UART + RS485 transceiver, e.g. MAX3485 / Waveshare) to poll the same Deye holding registers as `iriv/iriv-ioc-config.json`, then publish MQTT (or expose HTTP).

## Constraints

| Item | Value |
|------|--------|
| Baud | 9600 8N1 |
| Slave | 1 |
| Bus | **One master only** — do not run with IRIV on the same A/B |
| Poll budget | Sparse map; throttle commands (see ESPHome YAML) |

## Suggested stack

- ESP-IDF or Arduino `ModbusMaster` / `eModbus`, or ESPHome `modbus_controller`
- MQTT → same topics as IRIV (`iriv/ivt/...`) for drop-in HA sensors

## Register list

Start from `iriv/_gen_iriv_jobs.py` / `iriv/iriv-ioc-config.json` (enabled jobs). Critical: Load Current **179**, Charge/Discharge **70/71**, PV current **0.1**, Grid Current **160** ×0.01.
