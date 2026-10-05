"""Feetech STS ping/position/goal. Torque stays off until explicitly enabled."""

from __future__ import annotations

import threading
import time

PING = 0x01
READ = 0x02
WRITE = 0x03
ADDR_TORQUE = 40
ADDR_ACCEL = 41
ADDR_GOAL_POS = 42
ADDR_GOAL_SPEED = 46
ADDR_PRESENT_POS = 56
ADDR_ID = 5
ADDR_LOCK = 55


def _checksum(body: list[int]) -> int:
    return (~(sum(body) & 0xFF)) & 0xFF


def _open(port: str, baud: int = 1_000_000):
    import serial

    return serial.Serial(port, baudrate=baud, timeout=0.05, write_timeout=0.2)


def _write_read(ser, pkt: bytes, sid: int, expect: int, timeout: float = 0.05) -> bytes | None:
    ser.reset_input_buffer()
    ser.write(pkt)
    ser.flush()
    t0 = time.time()
    buf = bytearray()
    while time.time() - t0 < timeout:
        n = ser.in_waiting
        if n:
            buf.extend(ser.read(n))
            for i in range(max(0, len(buf) - expect + 1)):
                if buf[i] == 0xFF and buf[i + 1] == 0xFF and buf[i + 2] == sid and len(buf) >= i + expect:
                    return bytes(buf[i : i + expect])
        time.sleep(0.002)
    return None


class FeetechBus:
    def __init__(self, port: str, baud: int = 1_000_000) -> None:
        self.port = port
        self.baud = baud
        self.ser = None
        self._lock = threading.Lock()

    def open(self) -> None:
        with self._lock:
            if self.ser is None or not self.ser.is_open:
                self.ser = _open(self.port, self.baud)

    def close(self) -> None:
        with self._lock:
            if self.ser is not None:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None

    def _req(self, sid: int, body: list[int], expect: int) -> bytes | None:
        if self.ser is None:
            raise RuntimeError(f"bus closed: {self.port}")
        pkt = bytes([0xFF, 0xFF, *body, _checksum(body)])
        return _write_read(self.ser, pkt, sid, expect)

    def ping(self, sid: int) -> bool:
        with self._lock:
            return self._req(sid, [sid, 0x02, PING], 6) is not None

    def ping_ids(self, ids: range | list[int] | None = None) -> list[int]:
        ids = list(ids or range(1, 11))
        return [sid for sid in ids if self.ping(sid)]

    def read_position(self, sid: int) -> int | None:
        with self._lock:
            raw = self._req(sid, [sid, 0x04, READ, ADDR_PRESENT_POS, 2], 8)
        if not raw or len(raw) < 8:
            return None
        return raw[5] | (raw[6] << 8)

    def read_positions(self, ids: list[int]) -> dict[int, int]:
        out: dict[int, int] = {}
        for sid in ids:
            pos = self.read_position(sid)
            if pos is not None:
                out[sid] = pos
        return out

    def write(self, sid: int, addr: int, data: list[int]) -> bool:
        body = [sid, 3 + len(data), WRITE, addr, *data]
        with self._lock:
            return self._req(sid, body, 6) is not None

    def set_torque(self, sid: int, on: bool) -> bool:
        return self.write(sid, ADDR_TORQUE, [1 if on else 0])

    def set_accel(self, sid: int, accel: int) -> bool:
        return self.write(sid, ADDR_ACCEL, [max(0, min(254, int(accel)))])

    def set_speed(self, sid: int, speed: int) -> bool:
        speed = max(0, min(32767, int(speed)))
        return self.write(sid, ADDR_GOAL_SPEED, [speed & 0xFF, (speed >> 8) & 0xFF])

    def set_goal(self, sid: int, pos: int) -> bool:
        pos = max(0, min(4095, int(pos)))
        return self.write(sid, ADDR_GOAL_POS, [pos & 0xFF, (pos >> 8) & 0xFF])

    def ping_packet_count(self, sid: int, timeout: float = 0.08) -> int:
        """How many status packets follow one PING. >1 means ID collision."""
        body = [sid, 0x02, PING]
        pkt = bytes([0xFF, 0xFF, *body, _checksum(body)])
        with self._lock:
            if self.ser is None:
                raise RuntimeError(f"bus closed: {self.port}")
            self.ser.reset_input_buffer()
            self.ser.write(pkt)
            self.ser.flush()
            t0 = time.time()
            buf = bytearray()
            while time.time() - t0 < timeout:
                n = self.ser.in_waiting
                if n:
                    buf.extend(self.ser.read(n))
                time.sleep(0.002)
        hits = 0
        i = 0
        while i + 6 <= len(buf):
            if buf[i] == 0xFF and buf[i + 1] == 0xFF and buf[i + 2] == sid:
                hits += 1
                i += 6
            else:
                i += 1
        return hits

    def set_id(self, old: int, new: int) -> bool:
        """Unlock EEPROM, write ID, lock on the new ID. Torque off first."""
        old, new = int(old), int(new)
        if not (1 <= new <= 253):
            raise ValueError(f"bad new id {new}")
        self.set_torque(old, False)
        time.sleep(0.02)
        self.write(old, ADDR_LOCK, [0])
        time.sleep(0.02)
        self.write(old, ADDR_ID, [new])
        time.sleep(0.15)
        if not self.ping(new):
            return False
        self.write(new, ADDR_LOCK, [1])
        return True


def ping_ids(port: str, ids: range | list[int] | None = None) -> list[int]:
    bus = FeetechBus(port)
    bus.open()
    try:
        return bus.ping_ids(ids)
    finally:
        bus.close()


def read_positions(port: str, ids: list[int]) -> dict[int, int]:
    bus = FeetechBus(port)
    bus.open()
    try:
        return bus.read_positions(ids)
    finally:
        bus.close()
