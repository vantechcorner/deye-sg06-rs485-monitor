# Domain keywords — `deye-mqtt-dashboard-lcd-35`

Use for search, Cursor rules, and agent context. English preferred in code/comments.

## Project

- deye-mqtt-dashboard-lcd-35
- MQTT dashboard
- realtime LCD viewer
- inverter telemetry display
- standalone firmware (not ESPHome-first)

## Hardware

- Waveshare ESP32-Touch-LCD-3.5
- ESP32
- ST7796
- FT6336
- 320x480
- capacitive touch
- LVGL

## Upstream / ecosystem

- Deye SG06
- Deye SG05
- hybrid inverter
- IRIV IOC MQTT Gateway
- IRIV Pi Control
- Cytron
- Mosquitto
- Home Assistant MQTT
- Modbus RTU (upstream only — not on this device)
- RS485 (upstream only)

## MQTT

- baseTopic: iriv/ivt
- subscribe: iriv/ivt/#
- payload JSON value
- value_json.value
- QoS 1
- retain
- topicSuffix
- broker

## Topic groups

- status
- battery voltage SOC power current temperature charge_today discharge_today
- pv1 voltage current power
- pv2 voltage current power
- pv energy_today
- grid frequency voltage current power_ct buy_today sell_today
- inverter temperature power frequency
- load power energy_today

## Metrics / units

- W (signed power)
- V
- A (signed current)
- Hz
- % SOC
- °C temperature
- kWh energy today
- operating status 0 Standby 1 Self-Test 2 Normal 3 Alarm 4 Fault

## Deye register context (for reference only)

- slave id 1
- FC03 holding
- 9600 8N1
- reg 59 operating status
- reg 70 battery charge today
- reg 71 battery discharge today
- reg 182 battery temp (raw×0.1−100; IRIV already scaled)
- reg 183 battery voltage
- reg 184 SOC
- reg 186/187 PV1/PV2 power
- reg 178 load power

## Explicit exclusions

- no RS485 master on LCD firmware
- no JK BMS CAN protocol 001 on this device
- no Pylon BMS emulator dependency
- no second Modbus master on inverter bus

## Related filenames

- iriv_deye_mqtt.yaml
- iriv-ioc-config.json
- Inverter-BMS-RS485-Emulator
- deye-sg06-ivt-emu.py
- sg06-nodemcu
