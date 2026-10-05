#!/usr/bin/env python3
"""Remap a unique Feetech 1-6 chain to 7-12. Refuses if IDs collide or 7-12 already exist.

Two 1-6 sets on one UART cannot be told apart. Unplug the set you want to KEEP
as 1-6, leave only the other set plugged, then run this so that set becomes 7-12.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "robot_bridge"))
from feetech_bus import FeetechBus

OLD = [1, 2, 3, 4, 5, 6]
NEW = [7, 8, 9, 10, 11, 12]


def check(bus: FeetechBus) -> tuple[list[int], dict[int, int]]:
    found = bus.ping_ids(range(1, 16))
    counts = {sid: bus.ping_packet_count(sid) for sid in found}
    return found, counts


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True)
    p.add_argument("--apply", action="store_true", help="actually write EEPROM IDs")
    p.add_argument(
        "--only-this-chain",
        action="store_true",
        help="confirm the other 1-6 set is unplugged",
    )
    args = p.parse_args()
    bus = FeetechBus(args.port)
    bus.open()
    try:
        found, counts = check(bus)
        print("port", args.port)
        print("ids", found)
        print("ping_counts", counts)
        collide = [sid for sid, n in counts.items() if n > 1]
        if collide:
            print("COLLISION on", collide, "— unplug one chain; do not write IDs")
            return 2
        extra = [sid for sid in found if sid in NEW]
        if extra:
            print("7-12 already present", extra, "— refuse remap")
            return 3
        present_old = [sid for sid in OLD if sid in found]
        if not present_old:
            print("no 1-6 servos found")
            return 4
        plan = list(zip(reversed(present_old), reversed([NEW[OLD.index(s)] for s in present_old])))
        print("plan (high id first)", plan)
        if not args.apply:
            print("dry-run only. Plug one chain, then: --apply --only-this-chain")
            return 0
        if not args.only_this_chain:
            print("refusing --apply without --only-this-chain")
            return 5
        for old, new in plan:
            print(f"  {old} -> {new} ...", end=" ", flush=True)
            ok = bus.set_id(old, new)
            print("ok" if ok else "FAIL")
            if not ok:
                return 6
        found2, counts2 = check(bus)
        print("after ids", found2, "counts", counts2)
        return 0
    finally:
        bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
