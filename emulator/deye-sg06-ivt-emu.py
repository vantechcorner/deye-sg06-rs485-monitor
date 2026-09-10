#!/usr/bin/env python3
"""Deye SG05/SG06 hybrid inverter Modbus RTU slave emulator (USB-RS485).

Acts as a Modbus RTU **slave** (default id 1, 9600 8N1) with a physics-lite
day-cycle simulation. Intended masters: ESPHome, IRIV IOC MQTT Gateway, or any
Modbus RTU logger.

Register map follows Deye SG05 Modbus Protocol V118 (holding registers) and
matches esphome/deye-sg06-nodemcu.yaml.

Examples:
  python emulator/deye-sg06-ivt-emu.py --port COM35 --debug --scenario day
  python emulator/deye-sg06-ivt-emu.py --port COM35 --trace --scenario fault
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from repo root or emulator/ without install.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rs485_emu.core.cli import add_common_args, setup_logging
from rs485_emu.core.server import run_serial_emulator
from rs485_emu.core.tracer import FrameTracer
from rs485_emu.profiles.deye_sg_inverter import (
    REGISTER_META,
    DeyeInverterSimulator,
    create_bank,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Deye SG05/SG06 hybrid inverter Modbus RTU slave emulator "
            "(USB-RS485)"
        )
    )
    add_common_args(parser)
    args = parser.parse_args(argv)
    setup_logging(debug=args.debug, trace=args.trace)

    bank = create_bank()
    sim = DeyeInverterSimulator(bank, scenario=args.scenario, seed=args.seed)
    tracer = FrameTracer(
        debug=args.debug,
        trace=args.trace,
        bank=bank,
        meta_by_addr=REGISTER_META,
        known_addresses=set(REGISTER_META),
    )

    asyncio.run(
        run_serial_emulator(
            title="Deye SG06 / SG05 inverter emulator",
            bank=bank,
            slave_id=args.slave_id,
            port=args.port,
            baudrate=args.baudrate,
            tracer=tracer,
            tick=sim.tick,
            tick_interval=args.tick,
            extra_banner={"Scenario": args.scenario},
        )
    )


if __name__ == "__main__":
    main()
