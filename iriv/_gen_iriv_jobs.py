"""Generate Deye SG06 Modbus poll jobs for IRIV IOC MQTT Gateway config.

Firmware note: IOC firmware **before V1.2.6** reboots and wipes the job list
when a 27th poll job is enabled. **V1.2.6** fixes that. Import
``iriv-ioc-config.json`` (27 jobs, full PV2) on V1.2.6+.
``iriv-ioc-config-26.json`` drops PV2 Current and is only for older firmware.

MQTT auth in both files: user ``admin``, password ``12345678``.

Periods:
  LIVE_MS  1000  — Voltage / Current / Power only
  TEMP_MS 10000  — temps, status, SOC, frequency
  ENERGY_MS 30000 — *_today energy counters

Run: python iriv/_gen_iriv_jobs.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / "iriv-ioc-config.json"
cfg = json.loads(path.read_text(encoding="utf-8"))

# Field-verified: dataType 3 = s16. dataType 1 produced bogus (~scale) values.
S16 = 3

LIVE_MS = 1000  # V / I / P
TEMP_MS = 10000  # temps, status, SOC, Hz
ENERGY_MS = 30000  # *_today


def job(
    name: str,
    addr: int,
    *,
    count: int = 1,
    scale: float = 1.0,
    offset: float = 0.0,
    unit: str = "",
    decimals: int = 2,
    topic: str = "",
    period_ms: int = 5000,
) -> dict:
    return {
        "enabled": True,
        "name": name,
        "slaveId": 1,
        "fc": 3,
        "address": int(addr),
        "count": int(count),
        "dataType": S16,
        "byteOrder": 0,
        "scale": float(scale),
        "offset": float(offset),
        "unit": unit,
        "decimals": int(decimals),
        "periodMs": int(period_ms),
        "priority": 1,
        "topicSuffix": topic,
        "payload": 1,
        "qos": 1,
        "retain": True,
        "publishMode": 1,
        "deadband": 0,
        "minPublishIntervalMs": 0,
    }


def empty() -> dict:
    return {
        "enabled": False,
        "name": "",
        "slaveId": 0,
        "fc": 0,
        "address": 0,
        "count": 0,
        "dataType": 0,
        "byteOrder": 0,
        "scale": 0.0,
        "offset": 0.0,
        "unit": "",
        "decimals": 0,
        "periodMs": 0,
        "priority": 0,
        "topicSuffix": "",
        "payload": 0,
        "qos": 0,
        "retain": False,
        "publishMode": 0,
        "deadband": 0,
        "minPublishIntervalMs": 0,
    }


# Full set is 27 enabled jobs (needs IOC firmware >= V1.2.6).
# The rollback file drops PV2 Current so older firmware stays at 26 jobs.
jobs = [
    job("Operating Status", 59, scale=1, unit="", decimals=0, topic="status", period_ms=TEMP_MS),
    # Battery energy / temp / SOC (not LIVE)
    job("Battery Charge Today", 70, scale=0.1, unit="kWh", decimals=1, topic="battery/charge_today", period_ms=ENERGY_MS),
    job("Battery Discharge Today", 71, scale=0.1, unit="kWh", decimals=1, topic="battery/discharge_today", period_ms=ENERGY_MS),
    job("Battery Temperature", 182, scale=0.1, offset=-100.0, unit="C", decimals=1, topic="battery/temperature", period_ms=TEMP_MS),
    job("Battery SOC", 184, scale=1, unit="%", decimals=0, topic="battery/soc", period_ms=TEMP_MS),
    # Battery V / I / P @ 1s
    job("Battery Voltage", 183, scale=0.01, unit="V", decimals=2, topic="battery/voltage", period_ms=LIVE_MS),
    job("Battery Power", 190, scale=1, unit="W", decimals=0, topic="battery/power", period_ms=LIVE_MS),
    job("Battery Current", 191, scale=0.01, unit="A", decimals=2, topic="battery/current", period_ms=LIVE_MS),
    job("PV1 Voltage", 109, scale=0.1, unit="V", decimals=1, topic="pv1/voltage", period_ms=LIVE_MS),
    job("PV1 Current", 110, scale=0.1, unit="A", decimals=2, topic="pv1/current", period_ms=LIVE_MS),
    job("PV1 Power", 186, scale=1, unit="W", decimals=0, topic="pv1/power", period_ms=LIVE_MS),
    job("PV2 Voltage", 111, scale=0.1, unit="V", decimals=1, topic="pv2/voltage", period_ms=LIVE_MS),
    job("PV2 Current", 112, scale=0.1, unit="A", decimals=2, topic="pv2/current", period_ms=LIVE_MS),
    job("PV2 Power", 187, scale=1, unit="W", decimals=0, topic="pv2/power", period_ms=LIVE_MS),
    job("PV Energy Today", 108, scale=0.1, unit="kWh", decimals=1, topic="pv/energy_today", period_ms=ENERGY_MS),
    # Grid Hz slow; V / I / P @ 1s
    job("Grid Frequency", 79, scale=0.01, unit="Hz", decimals=2, topic="grid/frequency", period_ms=TEMP_MS),
    job("Grid Voltage", 150, scale=0.1, unit="V", decimals=1, topic="grid/voltage", period_ms=LIVE_MS),
    job("Grid Current", 160, scale=0.01, unit="A", decimals=2, topic="grid/current", period_ms=LIVE_MS),
    job("Grid Power CT", 172, scale=1, unit="W", decimals=0, topic="grid/power_ct", period_ms=LIVE_MS),
    job("Grid Buy Today", 76, scale=0.1, unit="kWh", decimals=1, topic="grid/buy_today", period_ms=ENERGY_MS),
    job("Grid Sell Today", 77, scale=0.1, unit="kWh", decimals=1, topic="grid/sell_today", period_ms=ENERGY_MS),
    # Inverter / Load
    job("Inverter Temperature", 91, scale=0.1, offset=-100.0, unit="C", decimals=1, topic="inverter/temperature", period_ms=TEMP_MS),
    job("Inverter Active Power", 175, scale=1, unit="W", decimals=0, topic="inverter/power", period_ms=LIVE_MS),
    job("Inverter Frequency", 193, scale=0.01, unit="Hz", decimals=2, topic="inverter/frequency", period_ms=TEMP_MS),
    job("Load Power", 178, scale=1, unit="W", decimals=0, topic="load/power", period_ms=LIVE_MS),
    job("Load Current", 179, scale=0.01, unit="A", decimals=2, topic="load/current", period_ms=LIVE_MS),
    job("Load Energy Today", 84, scale=0.1, unit="kWh", decimals=1, topic="load/energy_today", period_ms=ENERGY_MS),
]

SAFE_CAP = 26
# Drop PV2 Current first — voltage and power stay. Inverter Frequency stays.
DROP_FOR_SAFE = {"pv2/current"}


def write_config(dest: Path, enabled_jobs: list[dict]) -> None:
    assert len(enabled_jobs) <= 32, f"IRIV template has 32 poll slots (got {len(enabled_jobs)})"
    slots = list(enabled_jobs)
    while len(slots) < 32:
        slots.append(empty())

    out = copy.deepcopy(cfg)
    out["rtu"]["pollJobs"] = slots
    out["rtu"]["link"]["baud"] = 9600
    out["rtu"]["link"]["responseTimeoutMs"] = 800
    out["mqtt"]["enabled"] = True
    out["mqtt"]["host"] = out.get("mqtt", {}).get("host") or "iriv-pi-control"
    out["mqtt"]["baseTopic"] = "iriv/ivt"
    out["mqtt"]["clientId"] = "iriv-ioc-ivt"
    out["mqtt"]["useAuth"] = True
    out["mqtt"]["user"] = "admin"
    out["mqtt"]["passEnc"] = "12345678"
    # Many 1 s publishes — leave headroom vs default 20
    out["mqtt"]["globalRateMax"] = 60
    out["mqtt"]["globalBurst"] = 120

    # ASCII-only JSON, LF endings — matches typical IRIV export style
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")

    print(f"Wrote {dest.name}: {len(enabled_jobs)} enabled jobs / 32 slots")
    print(f"  LIVE(V/I/P)={LIVE_MS}ms  TEMP/SOC/Hz={TEMP_MS}ms  ENERGY={ENERGY_MS}ms")
    for j in enabled_jobs:
        print(
            f"  {j['periodMs']/1000:4.0f}s  {j['name']:28} "
            f"addr={j['address']:3} -> iriv/ivt/{j['topicSuffix']}"
        )


safe_jobs = [j for j in jobs if j["topicSuffix"] not in DROP_FOR_SAFE]
assert any(j["topicSuffix"] == "inverter/frequency" for j in safe_jobs)
assert len(safe_jobs) == SAFE_CAP, f"rollback file must be {SAFE_CAP} jobs (got {len(safe_jobs)})"

write_config(path, jobs)
print()
write_config(HERE / "iriv-ioc-config-26.json", safe_jobs)
