#!/usr/bin/env python3
"""Pylontech-style BMS Modbus RTU slave emulator (USB-RS485).

Generic **Pylon / 派能 RS485 Modbus** holding-register slave for bringing up
dataloggers (IRIV, ESPHome, etc.). This does **not** emulate a JK-PB series BMS
talking to Deye over CAN (see README field notes).

Defaults: slave id 1, 9600 8N1. Use a separate COM port from the inverter emu.

Examples:
  python bms-pylon-emu.py --port COM36 --debug --scenario day
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rs485_emu.core.cli import add_common_args, setup_logging
from rs485_emu.core.server import run_serial_emulator
from rs485_emu.core.tracer import FrameTracer
from rs485_emu.profiles.bms_pylon import REGISTER_META, PylonBmsSimulator, create_bank


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Pylontech-style BMS Modbus RTU slave emulator (USB-RS485). "
            "Not a JK/Deye CAN BMS replacement."
        )
    )
    add_common_args(parser)
    args = parser.parse_args(argv)
    setup_logging(debug=args.debug, trace=args.trace)

    bank = create_bank()
    sim = PylonBmsSimulator(bank, scenario=args.scenario, seed=args.seed)
    tracer = FrameTracer(
        debug=args.debug,
        trace=args.trace,
        bank=bank,
        meta_by_addr=REGISTER_META,
        known_addresses=set(REGISTER_META),
    )

    asyncio.run(
        run_serial_emulator(
            title="Pylon-style BMS emulator (Modbus RTU)",
            bank=bank,
            slave_id=args.slave_id,
            port=args.port,
            baudrate=args.baudrate,
            tracer=tracer,
            tick=sim.tick,
            tick_interval=args.tick,
            extra_banner={
                "Scenario": args.scenario,
                "Registers": "0x0100-0x0132 (CVL/CCL/DCL, SOC/SOH, V/I/T, flags)",
                "Note": "Bench logger profile only; JK↔Deye uses CAN protocol 001",
            },
        )
    )


if __name__ == "__main__":
    main()
