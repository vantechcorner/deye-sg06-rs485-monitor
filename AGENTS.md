# Agent notes — Deye SG06 RS485 Monitor

Read **[docs/HANDOFF.md](docs/HANDOFF.md)** before changing Modbus maps, IRIV JSON, or ESP32 pollers.

## Project role

Monitor a **Deye SG05/SG06** hybrid inverter via **Modbus RTU slave** on the datalogger RS485 port. This repo does **not** talk to the JK BMS over RS485 (that is the sister repo `jk-pb-rs485-monitor`).

## Layout

- `iriv/` — IRIV job generator + import JSON  
- `emulator/` — Deye Modbus slave + `rs485_emu/`  
- `esphome/` — NodeMCU master YAML  
- `homeassistant/` · `web/` · `docs/` (incl. protocol PDF)

## Hard constraints

- **One Modbus master per RS485 bus** (IRIV **or** ESPHome **or** ESP32 — never two).
- Baud **9600** 8N1, slave **1**.
- Cytron IRIV IOC: **max 26 enabled poll jobs**. A 27th enabled job caused **reboot + wipe** of all jobs in lab firmware.
- Prefer battery SOC/V/I from **inverter** registers when the pack is on **CAN** to Deye.
- Regenerate IRIV jobs only via `python iriv/_gen_iriv_jobs.py`.

## Sister repo

`../jk-pb-rs485-monitor` — JK-PB UART1 Modbus @ 115200, slave 15. Pylon-style BMS emulator: `emulator/bms-pylon-emu.py`.
