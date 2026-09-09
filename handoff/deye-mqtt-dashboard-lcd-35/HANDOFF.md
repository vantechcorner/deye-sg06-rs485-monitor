# Technical handoff — `deye-mqtt-dashboard-lcd-35`

**Status:** New firmware project (standalone). Do **not** implement Modbus RTU or RS485 on this device.  
**Role:** MQTT subscriber + LVGL UI on Waveshare ESP32-Touch-LCD-3.5.  
**Upstream data:** IRIV IOC MQTT Gateway → broker → this display.

---

## 1. Goal

Build firmware that shows **real-time Deye SG05/SG06 hybrid inverter** telemetry on a 3.5" touch LCD by subscribing to MQTT topics published by **IRIV IOC MQTT Gateway**.

This device is a **viewer only**. Polling the inverter remains on IRIV (Modbus master). Home Assistant may also consume the same topics independently.

```text
Deye SG06 (Modbus slave)
        │ RS485
        ▼
IRIV IOC MQTT Gateway (Modbus master → MQTT publish)
        │
        ▼
   MQTT Broker
        ├── Home Assistant (optional)
        └── ESP32-Touch-LCD-3.5  ← THIS PROJECT
```

---

## 2. Hardware

| Item | Value |
|------|--------|
| Board | Waveshare **ESP32-Touch-LCD-3.5** |
| MCU | ESP32 (board-specific; use Waveshare docs for pins) |
| Display | **ST7796**, 320×480 |
| Touch | **FT6336** (capacitive) |
| Orientation | Portrait 320×480 (or landscape if you rotate in LVGL) |

**Recommended stack:** Arduino **or** ESP-IDF + **LVGL 8/9** + MQTT client.  
**Not recommended as primary path:** ESPHome (limited touch UI for this use case).

---

## 3. MQTT contract (critical)

| Setting | Value |
|---------|--------|
| Base topic | `iriv/ivt` |
| Subscribe | `iriv/ivt/#` |
| QoS (publisher) | typically 1 |
| Retain | often true on IRIV jobs |
| Payload | JSON, same style as ADL200 / HA: `{"value": <number>, ...}` |

**Parse:** use `value` field (HA: `value_json.value`). Do not assume bare numeric payloads unless you verify on the broker.

**Source of truth (copy into new repo `reference/`):**

1. `iriv_deye_mqtt.yaml` — HA sensor → `state_topic` map  
2. `iriv-ioc-config.json` — IRIV `baseTopic` + `topicSuffix` + scale already applied by gateway  

Full topic list: [mqtt-topics.md](mqtt-topics.md).

---

## 4. UI grouping (suggested screens)

Mirror MQTT hierarchy — one tab / page per group:

| Screen | Topics prefix | Key widgets |
|--------|---------------|-------------|
| Overview | `status`, `pv1/power`, `pv2/power`, `load/power`, `battery/soc` | Status text, PV total, load, SOC |
| Battery | `iriv/ivt/battery/#` | V, I, P, SOC, temp, charge/discharge today |
| PV | `pv1/#`, `pv2/#`, `pv/energy_today` | V/I/P per string + today kWh |
| Grid | `iriv/ivt/grid/#` | V, Hz, I, CT power, buy/sell today |
| Inverter / Load | `inverter/#`, `load/#` | Temp, P, Hz, load P + energy |

**Derived on device (optional):**

- PV total power = `pv1/power` + `pv2/power`  
- Status text from `status` int: `0` Standby, `1` Self-Test, `2` Normal, `3` Alarm, `4` Fault  

---

## 5. Engineering notes (values already scaled)

IRIV applies **scale/offset before publish**. LCD should display `value` as-is (engineering units).

| Metric examples | Unit | Notes |
|-----------------|------|--------|
| Powers | W | Signed (charge/discharge / export/import direction) |
| Currents | A | Signed |
| Voltages | V | |
| SOC | % | |
| Temps | °C | IRIV already applied Deye `×0.1 − 100` |
| Energy today | kWh | `total_increasing` style counters |
| Frequency | Hz | |

**Battery charge/discharge today (field-verified on SG06):**

- Charge today ← Modbus reg **70** → topic `battery/charge_today`  
- Discharge today ← Modbus reg **71** → topic `battery/discharge_today`  
(PDF V118 labels were swapped vs real inverter.)

---

## 6. Explicit non-goals

- Do **not** talk RS485 / Modbus to Deye from this ESP32.  
- Do **not** share the inverter RS485 bus with IRIV as a second master.  
- Do **not** require JK BMS CAN/Bluetooth for the first LCD version (battery data comes via Deye → IRIV → MQTT).  
- Emulator repo (`Inverter-BMS-RS485-Emulator`) is for bench testing IRIV/ESPHome only — not part of this firmware binary.

---

## 7. Sibling / related projects

| Repo / artifact | Relation |
|-----------------|----------|
| `Inverter-BMS-RS485-Emulator` | Modbus emulators, IRIV config, HA YAML, ESPHome NodeMCU |
| IRIV IOC MQTT Gateway | Publisher of `iriv/ivt/*` |
| IRIV Pi Control | Optional broker + long-term storage host |
| `sg06-nodemcu` ESPHome | Alternate Modbus master (avoid same RS485 bus as IRIV) |

---

## 8. Implementation checklist (firmware)

1. WiFi + MQTT reconnect with clear “offline” UI state.  
2. `subscribe("iriv/ivt/#")`.  
3. Map topic suffix → LVGL labels / gauges (see mqtt-topics.md).  
4. Config: broker host/port/user/pass in NVS or WiFi portal (avoid hard-coding production secrets).  
5. Optional OTA.  
6. Stale data: if no message for topic > N seconds, show “—” or grey out.

---

## 9. Agent instructions (Cursor)

When working in `deye-mqtt-dashboard-lcd-35`:

1. Read this handoff + `mqtt-topics.md` first.  
2. Treat `reference/iriv_deye_mqtt.yaml` as the topic list for UI bindings.  
3. Prefer LVGL + MQTT client; do not default to ESPHome unless the user asks.  
4. Keep MQTT topic strings identical to IRIV (`iriv/ivt/...`); do not invent new topic names without updating IRIV + HA.
