# Deye SG06 RS485 Monitor

Field tools to **monitor** a Deye SG05/SG06 hybrid inverter over **Modbus RTU (RS485)**: IRIV IOC MQTT templates, ESPHome example, PC slave emulator, MQTT web dashboard, and (planned) ESP32 UART→RS485 poller.

> Vietnamese: [README-vn.md](README-vn.md)  
> **Cursor / agent handoff:** [AGENTS.md](AGENTS.md) · [docs/HANDOFF.md](docs/HANDOFF.md) · `.cursor/rules/lab-context.mdc`

**Sister project:** [jk-pb-rs485-monitor](../jk-pb-rs485-monitor) — JK-PB* BMS Modbus (separate bus / baud). Pylon-style BMS bench slave lives there too.

```text
  [ IRIV / ESPHome / ESP32 ]  = Modbus MASTER
              |
         RS485 A/B @ 9600
              |
  [ Deye SG06  or  emulator/deye-sg06-ivt-emu ]  = Modbus SLAVE
```

**One master per RS485 bus.**

```bash
pip install -r requirements.txt
```

---

## Layout

| Path | Contents |
|------|----------|
| [`iriv/`](iriv/) | `iriv-ioc-config.json` (import on firmware ≥ V1.2.6), `iriv-ioc-config-26.json` (older firmware), `_gen_iriv_jobs.py` |
| [`emulator/`](emulator/) | Deye Modbus **slave** emulator + `rs485_emu/` |
| [`esphome/`](esphome/) | `deye-sg06-nodemcu.yaml` |
| [`homeassistant/`](homeassistant/) | MQTT sensors for `iriv/ivt/#` |
| [`web/`](web/) | Static MQTT WebSocket dashboard |
| [`docs/`](docs/) | HANDOFF, ESP32 stub, images, protocol PDF |
| [`handoff/`](handoff/) | Package for the LCD firmware repo |

---

## Field-tested

| Hardware | Verified |
|----------|----------|
| **Deye 6 kW SG06** + **16S 51.2 V 100 Ah** (JK-PB1A16S10P on **CAN** to inverter) | Inverter Modbus @ **9600**, slave **1** → IRIV MQTT `iriv/ivt/...` / ESPHome |

Battery SOC/V/I for the ESS pack: prefer **inverter** holding registers (CAN already feeds the inverter). Do not put a second master on the Deye↔JK CAN cable.

<!-- Placeholder: add your full rack photo -->
![Setup — Deye SG06 + 16S pack](docs/images/setup-deye-sg06-16s-100ah.jpg)

*Placeholder: save as `docs/images/setup-deye-sg06-16s-100ah.jpg`.*

---

## Key Modbus parameters

| Parameter | Value |
|-----------|--------|
| Baud | **9600** 8N1 |
| Slave ID | **1** |
| FC | 03 / 10 |
| Protocol PDF | [`docs/protocol/Deye SG05 Modbus Protocol.V118.pdf`](docs/protocol/Deye%20SG05%20Modbus%20Protocol.V118.pdf) |

Notable field corrections on SG06: charge/discharge today **70 / 71**; PV current scale **0.1**; Grid Current **160** ×0.01 (matches Deye logger; ×0.1 was 10× high); Load Current **179** ×0.01. IOC firmware **before V1.2.6** wiped all jobs if a 27th poll job was enabled. **V1.2.6** fixes that.

### IRIV

```bash
python iriv/_gen_iriv_jobs.py   # regenerates both IRIV JSON files
```

Import JSON on Cytron IRIV IOC MQTT Gateway. MQTT base: `iriv/ivt`. Default host in file: `iriv-pi-control`. Broker auth in the template: user `admin`, password `12345678`.

On firmware **≥ V1.2.6**, import [`iriv/iriv-ioc-config.json`](iriv/iriv-ioc-config.json) — **27** jobs, including PV2 voltage/current/power (regs **111 / 112 / 187**) and Inverter Frequency. Firmware **before V1.2.6** still reboots and wipes the list at job 27; use [`iriv/iriv-ioc-config-26.json`](iriv/iriv-ioc-config-26.json) on those builds (drops only PV2 Current).

Periods: **V/I/P = 1 s**; temp/SOC/Hz = 10 s; `*_today` = 30 s.

### Emulator

```bash
python emulator/deye-sg06-ivt-emu.py --port COM35 --debug --scenario day
```

### ESPHome

Flash [`esphome/deye-sg06-nodemcu.yaml`](esphome/deye-sg06-nodemcu.yaml) (hostname `sg06-nodemcu`). Keep ~15 s poll + throttle to avoid `Frame already active`.

### Web dashboard

```bash
cd web && python -m http.server 8080
```

Open `http://127.0.0.1:8080` — MQTT over WebSockets (broker listener **9001**). Details: [`web/README.md`](web/README.md).

---

## ESP32 / S3 + UART→RS485 (planned)

See [docs/esp32/README.md](docs/esp32/README.md). Same register map and **one-master** rule as IRIV.

---

## License / lab note

Lab toolkit for personal ESS monitoring. Protocol PDF is Deye’s document — redistribute per their terms.
