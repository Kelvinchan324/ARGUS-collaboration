"""Left/right linear actuators (lifts). Separate bus from arm servos."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import threading
import time

import yaml

from feetech_bus import FeetechBus

DEFAULT_PORTS = Path(__file__).resolve().parent.parent / "config" / "ports.yaml"
NUDGE_MAX = 400
LIFT_SPEED = 120
ACCEL = 30
SIDE_ORDER = ("left", "right")


@dataclass
class LiftState:
    side: str
    ready: bool = False
    mock: bool = True
    port: str = ""
    error: str | None = None
    ids: list[int] = field(default_factory=list)
    positions: dict[int, int] = field(default_factory=dict)
    last_command: str = ""


class LinearActuatorDriver:
    """Independent left/right lifts on one Feetech bus (not arm shoulder_lift)."""

    def __init__(self, mock: bool = False, config_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self.bus: FeetechBus | None = None
        self._states: dict[str, LiftState] = {}
        self._side_cfg: dict[str, dict[str, Any]] = {}
        self.port = ""
        path = config_path or DEFAULT_PORTS
        cfg = {}
        if path.exists():
            with path.open(encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        lifts = cfg.get("lifts") or {}
        self.port = str(lifts.get("port") or "")
        enabled = bool(lifts.get("enabled", True))
        for side in SIDE_ORDER:
            sc = lifts.get(side) or {}
            ids = [int(x) for x in (sc.get("ids") or [])]
            signs = [int(x) for x in (sc.get("signs") or [1] * len(ids))]
            while len(signs) < len(ids):
                signs.append(1)
            self._side_cfg[side] = {"ids": ids, "signs": signs[: len(ids)]}
            st = LiftState(side=side, port=self.port, ids=list(ids))
            self._states[side] = st
            if mock or not enabled:
                st.error = "forced mock" if mock else "disabled in config/ports.yaml"
                continue
            if not self.port or not Path(self.port).exists():
                st.error = f"port missing: {self.port or '(unset)'}"
                continue
            if not ids:
                st.error = "no servo ids in config"
                continue

        if mock or not enabled or not self.port or not Path(self.port).exists():
            return

        bus = FeetechBus(self.port)
        try:
            bus.open()
            found = bus.ping_ids(range(1, 21))
        except Exception as exc:
            for st in self._states.values():
                st.error = str(exc)
            try:
                bus.close()
            except Exception:
                pass
            return

        self.bus = bus
        for side, st in self._states.items():
            want = self._side_cfg[side]["ids"]
            missing = [i for i in want if i not in found]
            if missing:
                st.error = f"missing ids {missing}; bus has {found}"
                st.ready = False
                st.mock = True
            else:
                st.ids = list(want)
                st.ready = True
                st.mock = False
                st.error = None

    def side_names(self) -> list[str]:
        return [s for s in SIDE_ORDER if s in self._states]

    def snapshot(self) -> dict:
        with self._lock:
            if self.bus is not None:
                all_ids = []
                for st in self._states.values():
                    if st.ready and not st.mock:
                        all_ids.extend(st.ids)
                try:
                    pos = self.bus.read_positions(sorted(set(all_ids))) if all_ids else {}
                except Exception as exc:
                    pos = {}
                    for st in self._states.values():
                        if st.ready:
                            st.error = str(exc)
                for st in self._states.values():
                    st.positions = {i: pos[i] for i in st.ids if i in pos}
            out = {side: st.__dict__.copy() for side, st in self._states.items()}
            out["mock"] = all(s.mock for s in self._states.values()) if self._states else True
            out["sides"] = self.side_names()
            out["port"] = self.port
            return out

    def _write_goal(self, sid: int, pos: int) -> bool:
        assert self.bus is not None
        ok = True
        ok = self.bus.set_accel(sid, ACCEL) and ok
        ok = self.bus.set_speed(sid, LIFT_SPEED) and ok
        ok = self.bus.set_goal(sid, pos) and ok
        ok = self.bus.set_torque(sid, True) and ok
        if not ok:
            time.sleep(0.02)
            ok = self.bus.set_goal(sid, pos) and self.bus.set_torque(sid, True)
        return ok

    def nudge(self, side: str, delta: int) -> dict:
        """Move one lift up/down. delta>0 = up (config signs flip per motor)."""
        if side not in self._states:
            raise ValueError(f"unknown lift side {side!r}")
        st = self._states[side]
        if st.mock or not st.ready or self.bus is None:
            raise ValueError(f"{side} lift not wired")
        delta = max(-NUDGE_MAX, min(NUDGE_MAX, int(delta)))
        signs = self._side_cfg[side]["signs"]
        with self._lock:
            pos = self.bus.read_positions(st.ids)
            goals: dict[int, int] = {}
            ok = True
            for sid, sign in zip(st.ids, signs):
                cur = int(pos.get(sid, 0))
                goal = max(0, min(4095, cur + int(sign) * delta))
                goals[sid] = goal
                ok = self._write_goal(sid, goal) and ok
            st.positions = dict(goals)
            st.last_command = f"nudge d={delta} goals={goals}"
            st.error = None if ok else "write failed"
            if not ok:
                raise RuntimeError(f"{side} lift nudge write failed")
            return {"side": side, "delta": delta, "goals": goals}

    def estop(self) -> None:
        if self.bus is None:
            return
        for st in self._states.values():
            for sid in st.ids:
                try:
                    self.bus.set_torque(sid, False)
                except Exception:
                    pass
            if not st.mock:
                st.last_command = "estop"
