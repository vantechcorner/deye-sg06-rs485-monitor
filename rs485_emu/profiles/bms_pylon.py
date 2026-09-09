"""Pylontech-style BMS Modbus holding-register profile (bench only).

Register map adapted from Pylontech RS485 Modbus RTU Protocol v1.0
(CAN 0x351–0x35E mapped to holding registers).

Note: A real JK-PB1A16S10P paired with Deye typically uses CAN protocol
"001 – Deye Low Voltage Hybrid Inverter", not this Pylon Modbus map. Use this
profile to exercise Modbus masters (IRIV / ESPHome), not as a drop-in JK CAN
replacement.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from rs485_emu.core.registers import RegisterBank, RegisterMeta

REGISTER_META: dict[int, RegisterMeta] = {
    0x0100: RegisterMeta(0x0100, "ChargeVoltage", scale=0.1, unit="V"),
    0x0101: RegisterMeta(0x0101, "ChargeCurrentLimit", scale=0.1, unit="A", signed=True),
    0x0102: RegisterMeta(
        0x0102, "DischargeCurrentLimit", scale=0.1, unit="A", signed=True
    ),
    0x0110: RegisterMeta(0x0110, "SOC", scale=1.0, unit="%"),
    0x0111: RegisterMeta(0x0111, "SOH", scale=1.0, unit="%"),
    0x0120: RegisterMeta(0x0120, "PackVoltage", scale=0.01, unit="V", signed=True),
    0x0121: RegisterMeta(0x0121, "PackCurrent", scale=0.1, unit="A", signed=True),
    0x0122: RegisterMeta(0x0122, "AvgTemp", scale=0.1, unit="°C", signed=True),
    0x0130: RegisterMeta(0x0130, "ProtectionFlags"),
    0x0131: RegisterMeta(0x0131, "AlarmFlags"),
    0x0132: RegisterMeta(0x0132, "ModuleCount"),
}


@dataclass
class BmsSimState:
    scenario: str = "day"
    soc: float = 80.0
    soh: float = 98.0
    current_a: float = 5.0  # + charge, - discharge
    temp_c: float = 28.0
    rng: random.Random = field(default_factory=random.Random)


class PylonBmsSimulator:
    def __init__(
        self,
        bank: RegisterBank,
        *,
        scenario: str = "day",
        seed: int | None = None,
    ):
        self.bank = bank
        self.state = BmsSimState(scenario=scenario)
        if seed is not None:
            self.state.rng.seed(seed)
        self._seed_static()

    def _seed_static(self) -> None:
        b = self.bank
        b.apply_meta(REGISTER_META[0x0100], 53.2)  # charge voltage limit
        b.apply_meta(REGISTER_META[0x0101], 50.0)
        b.apply_meta(REGISTER_META[0x0102], 50.0)
        b.write_u16(0x0111, int(self.state.soh))
        b.write_u16(0x0132, 1)
        b.write_u16(0x0130, 0)
        b.write_u16(0x0131, 0)

    def tick(self, dt: float) -> None:
        st = self.state
        if st.scenario == "night":
            target_i = -st.rng.uniform(2.0, 8.0)
        elif st.scenario == "cloud":
            target_i = st.rng.uniform(-15.0, 20.0)
        elif st.scenario == "fault":
            target_i = 0.0
        else:
            # Day: mild charge bias
            target_i = st.rng.uniform(-5.0, 25.0)

        st.current_a += (target_i - st.current_a) * min(1.0, dt * 0.5)
        volt = 48.0 + st.soc * 0.08
        # 100 Ah nominal
        st.soc += (st.current_a * dt / 3600.0) / 100.0 * 100.0
        st.soc = max(5.0, min(100.0, st.soc))
        st.temp_c += (28.0 + abs(st.current_a) * 0.08 - st.temp_c) * 0.05
        st.temp_c += st.rng.uniform(-0.05, 0.05)

        protect = 0
        alarm = 0
        ccl = 50.0
        dcl = 50.0
        if st.scenario == "fault":
            protect = 0x0001  # example: cell UV / protect bit
            alarm = 0x0002
            ccl = 0.0
            dcl = 0.0
            st.current_a = 0.0
        elif st.soc >= 95:
            ccl = 5.0
        elif st.soc <= 15:
            dcl = 5.0
            alarm |= 0x0001  # low SOC alarm

        b = self.bank
        b.apply_meta(REGISTER_META[0x0100], 53.2)
        b.apply_meta(REGISTER_META[0x0101], ccl)
        b.apply_meta(REGISTER_META[0x0102], dcl)
        b.write_u16(0x0110, int(round(st.soc)))
        b.write_u16(0x0111, int(round(st.soh)))
        b.apply_meta(REGISTER_META[0x0120], volt)
        b.apply_meta(REGISTER_META[0x0121], st.current_a)
        b.apply_meta(REGISTER_META[0x0122], st.temp_c)
        b.write_u16(0x0130, protect)
        b.write_u16(0x0131, alarm)
        b.write_u16(0x0132, 1)


def create_bank() -> RegisterBank:
    # Cover 0x0100–0x0132 with headroom.
    return RegisterBank(size=0x0200, base_address=0)
