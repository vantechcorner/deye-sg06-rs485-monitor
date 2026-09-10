"""Deye SG05/SG06 hybrid inverter Modbus holding-register profile.

Map aligned with Deye SG05 Modbus Protocol V118 and esphome/deye-sg06-nodemcu.yaml.
Emulates the inverter **datalogger RS485** slave (not the BMS CAN port).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from rs485_emu.core.registers import RegisterBank, RegisterMeta

# Addresses used by esphome/deye-sg06-nodemcu.yaml + PDF V118 essentials / pack1.
REGISTER_META: dict[int, RegisterMeta] = {
    0: RegisterMeta(0, "DeviceType", unit=""),
    59: RegisterMeta(59, "OperatingStatus"),
    70: RegisterMeta(70, "BattChargeToday", scale=0.1, unit="kWh"),
    71: RegisterMeta(71, "BattDischargeToday", scale=0.1, unit="kWh"),
    76: RegisterMeta(76, "GridBuyToday", scale=0.1, unit="kWh"),
    77: RegisterMeta(77, "GridSellToday", scale=0.1, unit="kWh"),
    79: RegisterMeta(79, "GridFreq", scale=0.01, unit="Hz"),
    84: RegisterMeta(84, "DayLoadEnergy", scale=0.1, unit="kWh"),
    # YAML: (x - 1000) / 10  => engineering = raw*0.1 + (-100) with raw = eng*10+1000
    90: RegisterMeta(90, "DcTemp", scale=0.1, offset=-100.0, unit="°C", signed=True),
    91: RegisterMeta(91, "InvTemp", scale=0.1, offset=-100.0, unit="°C", signed=True),
    96: RegisterMeta(96, "PvTotalGenLow"),
    97: RegisterMeta(97, "PvTotalGenHigh"),
    108: RegisterMeta(108, "PvToday", scale=0.1, unit="kWh"),
    109: RegisterMeta(109, "Pv1Volt", scale=0.1, unit="V"),
    110: RegisterMeta(110, "Pv1Curr", scale=0.1, unit="A", signed=True),
    111: RegisterMeta(111, "Pv2Volt", scale=0.1, unit="V"),
    112: RegisterMeta(112, "Pv2Curr", scale=0.1, unit="A", signed=True),
    150: RegisterMeta(150, "GridVolt", scale=0.1, unit="V"),
    154: RegisterMeta(154, "InvVolt", scale=0.1, unit="V"),
    160: RegisterMeta(160, "GridCurr", scale=0.01, unit="A", signed=True),
    164: RegisterMeta(164, "InvCurr", scale=0.01, unit="A", signed=True),
    172: RegisterMeta(172, "GridCtPower", scale=1.0, unit="W", signed=True),
    175: RegisterMeta(175, "InvActivePower", scale=1.0, unit="W", signed=True),
    178: RegisterMeta(178, "LoadPower", scale=1.0, unit="W", signed=True),
    179: RegisterMeta(179, "LoadCurr", scale=0.01, unit="A", signed=True),
    # PDF: batt temp real = raw/10 with offset +1000 (1200 => 20°C)
    182: RegisterMeta(182, "BattTemp", scale=0.1, offset=-100.0, unit="°C", signed=True),
    183: RegisterMeta(183, "BattVolt", scale=0.01, unit="V"),
    184: RegisterMeta(184, "BattSoc", scale=1.0, unit="%"),
    186: RegisterMeta(186, "Pv1Power", scale=1.0, unit="W", signed=True),
    187: RegisterMeta(187, "Pv2Power", scale=1.0, unit="W", signed=True),
    190: RegisterMeta(190, "BattPower", scale=1.0, unit="W", signed=True),
    191: RegisterMeta(191, "BattCurr", scale=0.01, unit="A", signed=True),
    193: RegisterMeta(193, "InvFreq", scale=0.01, unit="Hz"),
    325: RegisterMeta(325, "LithiumBattType"),
    # PACK1 (PDF V118)
    600: RegisterMeta(600, "Pack1Volt", scale=0.01, unit="V"),
    601: RegisterMeta(601, "Pack1Curr", scale=0.1, unit="A", signed=True),
    602: RegisterMeta(602, "Pack1Temp", scale=0.1, offset=-100.0, unit="°C"),
    603: RegisterMeta(603, "Pack1Soc", scale=0.1, unit="%"),
    604: RegisterMeta(604, "Pack1RemainAh", scale=0.1, unit="Ah"),
    605: RegisterMeta(605, "Pack1TotalAh", scale=0.1, unit="Ah"),
    606: RegisterMeta(606, "Pack1ChargeVolt", scale=0.01, unit="V"),
    607: RegisterMeta(607, "Pack1ChargeCurr", scale=0.1, unit="A"),
    608: RegisterMeta(608, "Pack1DischargeCurr", scale=0.1, unit="A"),
    609: RegisterMeta(609, "Pack1MaxCellV", scale=0.01, unit="V"),
    610: RegisterMeta(610, "Pack1MinCellV", scale=0.01, unit="V"),
    611: RegisterMeta(611, "Pack1Cycles"),
    612: RegisterMeta(612, "Pack1Warning"),
    613: RegisterMeta(613, "Pack1Fault"),
}

DEVICE_TYPE_SINGLE_PHASE_HYBRID = 0x0300
LITHIUM_TYPE_PYLON = 0x0000  # PYLON / 派能 (PDF reg 325)


@dataclass
class InverterSimState:
    scenario: str = "day"
    soc: float = 75.0
    load_w: float = 1200.0
    pv_today_kwh: float = 2.0
    batt_charge_today_kwh: float = 0.5
    batt_discharge_today_kwh: float = 0.3
    grid_buy_today_kwh: float = 0.2
    grid_sell_today_kwh: float = 0.4
    load_today_kwh: float = 1.5
    pv_total_kwh: float = 1234.5
    hour_offset: float = 0.0  # advances with ticks for accelerated day cycle
    rng: random.Random = field(default_factory=random.Random)

    def sun_factor(self) -> float:
        # Map accelerated hour into 0..24 for a smooth PV envelope.
        hour = (6.0 + self.hour_offset) % 24.0
        if self.scenario == "night":
            return 0.0
        # Peak around solar noon (hour 12).
        x = (hour - 12.0) / 5.5
        base = math.exp(-0.5 * x * x)
        if hour < 6.0 or hour > 18.5:
            base = 0.0
        if self.scenario == "cloud":
            base *= 0.35 + 0.45 * self.rng.random()
        return max(0.0, min(1.0, base))


class DeyeInverterSimulator:
    """Physics-lite day-cycle simulator writing Deye holding registers."""

    def __init__(
        self,
        bank: RegisterBank,
        *,
        scenario: str = "day",
        seed: int | None = None,
    ):
        self.bank = bank
        self.state = InverterSimState(scenario=scenario)
        if seed is not None:
            self.state.rng.seed(seed)
        # Start near solar noon so PV is non-zero before the first ESP poll.
        if scenario == "day":
            self.state.hour_offset = 6.0
        elif scenario == "cloud":
            self.state.hour_offset = 6.0
        elif scenario == "night":
            self.state.hour_offset = 14.0  # -> hour 20
        self._seed_static()
        # Populate all dynamic registers immediately (avoid PV=0 until first tick).
        self.tick(0.0)

    def _seed_static(self) -> None:
        b = self.bank
        b.write_u16(0, DEVICE_TYPE_SINGLE_PHASE_HYBRID)
        b.write_u16(325, LITHIUM_TYPE_PYLON)
        status = 4 if self.state.scenario == "fault" else 2
        b.write_u16(59, status)
        # Temperatures (offset+1000 encoding via RegisterMeta)
        b.apply_meta(REGISTER_META[90], 35.0)
        b.apply_meta(REGISTER_META[91], 42.0)
        b.apply_meta(REGISTER_META[79], 50.0)
        b.apply_meta(REGISTER_META[193], 50.0)
        b.apply_meta(REGISTER_META[150], 220.0)
        b.apply_meta(REGISTER_META[154], 220.0)

    def tick(self, dt: float) -> None:
        st = self.state
        # ~60x realtime so a day curve is visible within minutes.
        if dt > 0:
            st.hour_offset += dt * (60.0 / 3600.0) * 60.0

        sun = st.sun_factor()
        pv_total = 3200.0 * sun
        noise = st.rng.uniform(-40.0, 40.0) if sun > 0.05 else 0.0
        pv_total = max(0.0, pv_total + noise)
        pv1 = pv_total * 0.55
        pv2 = pv_total * 0.45

        # Load wanders slowly.
        st.load_w += st.rng.uniform(-30.0, 30.0)
        st.load_w = max(400.0, min(2500.0, st.load_w))
        if st.scenario == "night":
            st.load_w = max(300.0, min(900.0, st.load_w))

        # Power balance: surplus -> charge / export; deficit -> discharge / import.
        residual = pv_total - st.load_w
        if residual > 80:
            batt_w = min(residual * 0.6, 2000.0)  # charge (+)
            grid_w = residual - batt_w  # export (+ sell convention may vary)
        elif residual < -80:
            need = -residual
            batt_w = -min(need * 0.7, 2000.0)  # discharge (-)
            grid_w = residual - batt_w  # remaining from/to grid
        else:
            batt_w = 0.0
            grid_w = residual

        if st.scenario == "fault":
            pv1 = pv2 = pv_total = 0.0
            batt_w = 0.0
            grid_w = -st.load_w

        batt_v = 48.0 + st.soc * 0.08  # ~48–56 V
        batt_i = (batt_w / batt_v) if batt_v else 0.0
        # SOC drift: +charge / -discharge, ~100 Ah pack.
        capacity_wh = 100.0 * batt_v
        st.soc += (batt_w * dt / 3600.0) / capacity_wh * 100.0
        st.soc = max(10.0, min(98.0, st.soc))

        # Energy accumulators (kWh).
        hours = dt / 3600.0
        st.pv_today_kwh += pv_total * hours / 1000.0
        st.load_today_kwh += st.load_w * hours / 1000.0
        st.pv_total_kwh += pv_total * hours / 1000.0
        if batt_w > 0:
            st.batt_charge_today_kwh += batt_w * hours / 1000.0
        elif batt_w < 0:
            st.batt_discharge_today_kwh += (-batt_w) * hours / 1000.0
        if grid_w > 0:
            st.grid_sell_today_kwh += grid_w * hours / 1000.0
        elif grid_w < 0:
            st.grid_buy_today_kwh += (-grid_w) * hours / 1000.0

        inv_w = st.load_w  # approximate inverter AC output feeding load
        grid_v = 220.0 + st.rng.uniform(-1.5, 1.5)
        grid_f = 50.0 + st.rng.uniform(-0.03, 0.03)
        inv_temp = 35.0 + (abs(inv_w) / 6000.0) * 25.0 + st.rng.uniform(-0.3, 0.3)
        dc_temp = inv_temp - 5.0
        batt_temp = 28.0 + abs(batt_i) * 0.05

        pv1_v = 360.0 if sun > 0.02 else 0.0
        pv2_v = 340.0 if sun > 0.02 else 0.0
        pv1_i = (pv1 / pv1_v) if pv1_v else 0.0
        pv2_i = (pv2 / pv2_v) if pv2_v else 0.0
        grid_i = (grid_w / grid_v) if grid_v else 0.0
        inv_i = (inv_w / grid_v) if grid_v else 0.0

        status = 4 if st.scenario == "fault" else 2
        b = self.bank
        b.write_u16(59, status)
        b.apply_meta(REGISTER_META[90], dc_temp)
        b.apply_meta(REGISTER_META[91], inv_temp)
        b.apply_meta(REGISTER_META[79], grid_f)
        b.apply_meta(REGISTER_META[193], grid_f)
        b.apply_meta(REGISTER_META[150], grid_v)
        b.apply_meta(REGISTER_META[154], grid_v)
        b.apply_meta(REGISTER_META[160], grid_i)
        b.apply_meta(REGISTER_META[164], inv_i)
        b.apply_meta(REGISTER_META[172], int(round(grid_w)))
        b.apply_meta(REGISTER_META[175], int(round(inv_w)))
        b.apply_meta(REGISTER_META[178], int(round(st.load_w)))
        load_i = (st.load_w / grid_v) if grid_v > 1.0 else 0.0
        b.apply_meta(REGISTER_META[179], load_i)
        b.apply_meta(REGISTER_META[182], batt_temp)
        b.apply_meta(REGISTER_META[183], batt_v)
        b.apply_meta(REGISTER_META[184], st.soc)
        b.apply_meta(REGISTER_META[109], pv1_v)
        b.apply_meta(REGISTER_META[110], pv1_i)
        b.apply_meta(REGISTER_META[111], pv2_v)
        b.apply_meta(REGISTER_META[112], pv2_i)
        b.apply_meta(REGISTER_META[186], int(round(pv1)))
        b.apply_meta(REGISTER_META[187], int(round(pv2)))
        b.apply_meta(REGISTER_META[190], int(round(batt_w)))
        b.apply_meta(REGISTER_META[191], batt_i)
        b.apply_meta(REGISTER_META[70], st.batt_charge_today_kwh)
        b.apply_meta(REGISTER_META[71], st.batt_discharge_today_kwh)
        b.apply_meta(REGISTER_META[76], st.grid_buy_today_kwh)
        b.apply_meta(REGISTER_META[77], st.grid_sell_today_kwh)
        b.apply_meta(REGISTER_META[84], st.load_today_kwh)
        b.apply_meta(REGISTER_META[108], st.pv_today_kwh)
        b.write_u32_le(96, int(round(st.pv_total_kwh / 0.1)))

        # PACK1 mirrors battery pack view (PDF 600+)
        cell_v = batt_v / 16.0
        b.apply_meta(REGISTER_META[600], batt_v)
        b.apply_meta(REGISTER_META[601], batt_i)
        b.apply_meta(REGISTER_META[602], batt_temp)
        # PDF pack SOC unit is 0.1% → raw = soc% * 10
        b.apply_meta(REGISTER_META[603], st.soc)
        b.apply_meta(REGISTER_META[604], 100.0 * st.soc / 100.0)
        b.apply_meta(REGISTER_META[605], 100.0)
        b.apply_meta(REGISTER_META[606], 56.0)
        b.apply_meta(REGISTER_META[607], 50.0)
        b.apply_meta(REGISTER_META[608], 50.0)
        b.apply_meta(REGISTER_META[609], cell_v + 0.01)
        b.apply_meta(REGISTER_META[610], cell_v - 0.01)
        b.write_u16(611, 120)
        b.write_u16(612, 0)
        b.write_u16(613, 0x0001 if st.scenario == "fault" else 0)


def create_bank() -> RegisterBank:
    return RegisterBank(size=640, base_address=0)
