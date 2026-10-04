"""STM32 four-wheel-steer chassis protocol (copied from chassis_node.cpp)."""

from __future__ import annotations

import math
import os
import struct
import threading
import time
from dataclasses import dataclass, field

FRAME_DN_LEN = 53
FRAME_UP_LEN = 125
HEADER_UP = b"\xaa\xaa\xf1"
DATA_COUNT = 30
DATA_OFFSET = 4


def checksum(data: bytes) -> int:
    return sum(data) & 0xFF


def f2b(value: float) -> bytes:
    return struct.pack(">f", float(value))


def b2f(raw: bytes) -> float:
    return struct.unpack(">f", raw)[0]


@dataclass
class ChassisState:
    connected: bool = False
    mock: bool = False
    motor_enabled: bool = True
    port: str = ""
    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0
    odom_x: float = 0.0
    odom_y: float = 0.0
    odom_th: float = 0.0
    voltage: float = 0.0
    wheel_angles_deg: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    wheel_speeds: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    gyro_dps: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rpy_deg: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    ok_frames: int = 0
    last_rx_age_s: float = 1e9
    last_cmd_age_s: float = 1e9


class ChassisDriver:
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baud: int = 115200,
        timeout_ms: int = 500,
        mock: bool = False,
        max_vx: float = 0.50,
        max_vy: float = 0.50,
        max_wz: float = 1.20,
    ) -> None:
        self.port_name = port
        self.baud = baud
        self.timeout_s = timeout_ms / 1000.0
        self.mock = mock
        self.max_vx = max_vx
        self.max_vy = max_vy
        self.max_wz = max_wz
        self._ser = None
        self._lock = threading.Lock()
        self._cmd = (0.0, 0.0, 0.0)
        self._last_cmd = 0.0
        self._motor = True
        self._reset = False
        self._stop = threading.Event()
        self._state = ChassisState(mock=mock, port=port)
        self._last_rx = 0.0
        self._rx_buf = bytearray()
        self._next_open = 0.0

    def start(self) -> None:
        if self.mock:
            self._state.connected = False
            self._state.mock = True
        threading.Thread(target=self._loop, name="chassis-io", daemon=True).start()

    def close(self) -> None:
        self._stop.set()
        self.set_cmd(0.0, 0.0, 0.0)
        self.enable_motor(False)
        time.sleep(0.1)
        self._close_serial()

    def set_cmd(self, vx: float, vy: float, wz: float) -> None:
        vx = max(-self.max_vx, min(self.max_vx, vx))
        vy = max(-self.max_vy, min(self.max_vy, vy))
        wz = max(-self.max_wz, min(self.max_wz, wz))
        with self._lock:
            self._cmd = (vx, vy, wz)
            self._last_cmd = time.monotonic()

    def stop(self) -> None:
        with self._lock:
            self._cmd = (0.0, 0.0, 0.0)
            self._last_cmd = time.monotonic()

    def enable_motor(self, enabled: bool) -> None:
        with self._lock:
            self._motor = bool(enabled)
            if not enabled:
                self._cmd = (0.0, 0.0, 0.0)

    def reset_odom(self) -> None:
        with self._lock:
            self._reset = True
            if self.mock:
                self._state.odom_x = 0.0
                self._state.odom_y = 0.0
                self._state.odom_th = 0.0

    def snapshot(self) -> ChassisState:
        with self._lock:
            now = time.monotonic()
            return ChassisState(
                connected=self._state.connected,
                mock=self.mock,
                motor_enabled=self._motor,
                port=self.port_name if not self.mock else "mock",
                vx=self._cmd[0],
                vy=self._cmd[1],
                wz=self._cmd[2],
                odom_x=self._state.odom_x,
                odom_y=self._state.odom_y,
                odom_th=self._state.odom_th,
                voltage=self._state.voltage,
                wheel_angles_deg=list(self._state.wheel_angles_deg),
                wheel_speeds=list(self._state.wheel_speeds),
                gyro_dps=list(self._state.gyro_dps),
                rpy_deg=list(self._state.rpy_deg),
                ok_frames=self._state.ok_frames,
                last_rx_age_s=(now - self._last_rx) if self._last_rx else 1e9,
                last_cmd_age_s=(now - self._last_cmd) if self._last_cmd else 1e9,
            )

    def _close_serial(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        self._state.connected = False
        self._rx_buf.clear()

    def _ensure_serial(self) -> bool:
        now = time.monotonic()
        if self._ser is not None:
            try:
                if self._ser.is_open:
                    if self._last_rx and (now - self._last_rx) > 2.5:
                        print(f"[chassis] stale RX on {self.port_name}; reopening")
                        self._close_serial()
                    else:
                        return True
            except Exception:
                self._close_serial()
        if now < self._next_open:
            return False
        self._next_open = now + 1.0
        if not os.path.exists(self.port_name):
            self._state.connected = False
            return False
        try:
            import serial

            self._close_serial()
            self._ser = serial.Serial(
                self.port_name,
                self.baud,
                timeout=0.05,
                dsrdtr=False,
                rtscts=False,
            )
            try:
                self._ser.dtr = False
                self._ser.rts = False
            except Exception:
                pass
            self._rx_buf.clear()
            self._last_rx = 0.0
            self._state.connected = False
            print(f"[chassis] opened {self.port_name}")
            return True
        except Exception as exc:
            self._close_serial()
            print(f"[chassis] waiting for {self.port_name}: {exc}")
            return False

    def _loop(self) -> None:
        period = 1.0 / 20.0
        while not self._stop.is_set():
            t0 = time.monotonic()
            self._tick()
            dt = time.monotonic() - t0
            time.sleep(max(0.0, period - dt))

    def _tick(self) -> None:
        with self._lock:
            now = time.monotonic()
            vx, vy, wz = self._cmd
            if self._last_cmd and (now - self._last_cmd) > self.timeout_s:
                vx = vy = wz = 0.0
                self._cmd = (0.0, 0.0, 0.0)
            motor = self._motor
            do_reset = self._reset
            self._reset = False
        if self.mock:
            self._mock_integrate(vx, vy, wz)
            return
        if not self._ensure_serial():
            return
        self._read_serial()
        self._send_mode1(vx, vy, wz, motor, do_reset)

    def _mock_integrate(self, vx: float, vy: float, wz: float) -> None:
        dt = 0.05
        with self._lock:
            th = self._state.odom_th
            self._state.odom_x += (vx * math.cos(th) - vy * math.sin(th)) * dt
            self._state.odom_y += (vx * math.sin(th) + vy * math.cos(th)) * dt
            self._state.odom_th += wz * dt
            self._state.voltage = 24.0
            self._last_rx = time.monotonic()
            self._state.ok_frames += 1

    def _send_mode1(self, vx: float, vy: float, wz: float, motor: bool, reset: bool) -> None:
        buf = bytearray(FRAME_DN_LEN)
        buf[0] = 0xAA
        buf[1] = 0xAA
        off = 4
        buf[off : off + 4] = f2b(1.0 if motor else 0.0)
        off += 4
        buf[off : off + 4] = f2b(1.0)
        off += 4
        buf[off : off + 4] = f2b(vx)
        off += 4
        buf[off : off + 4] = f2b(vy)
        off += 4
        buf[off : off + 4] = f2b(wz)
        buf[44:48] = f2b(0.0 if reset else 1.0)
        buf[52] = checksum(bytes(buf[:52]))
        try:
            self._ser.write(buf)
        except Exception as exc:
            print(f"[chassis] write failed: {exc}")
            self._close_serial()

    def _read_serial(self) -> None:
        try:
            waiting = self._ser.in_waiting
            if waiting:
                self._rx_buf.extend(self._ser.read(waiting))
        except Exception as exc:
            print(f"[chassis] read failed: {exc}")
            self._close_serial()
            return
        if len(self._rx_buf) > 4096:
            self._rx_buf = self._rx_buf[-256:]
        while True:
            idx = self._rx_buf.find(HEADER_UP)
            if idx < 0:
                if len(self._rx_buf) > 2:
                    self._rx_buf = self._rx_buf[-2:]
                return
            if idx:
                del self._rx_buf[:idx]
            if len(self._rx_buf) < FRAME_UP_LEN:
                return
            frame = bytes(self._rx_buf[:FRAME_UP_LEN])
            del self._rx_buf[:FRAME_UP_LEN]
            if checksum(frame[:-1]) != frame[-1]:
                continue
            self._parse(frame)

    def _parse(self, frame: bytes) -> None:
        vals = [
            b2f(frame[DATA_OFFSET + i * 4 : DATA_OFFSET + (i + 1) * 4])
            for i in range(DATA_COUNT)
        ]
        with self._lock:
            self._state.wheel_angles_deg = [vals[1], vals[2], vals[3], vals[4]]
            self._state.wheel_speeds = [vals[5], vals[6], vals[7], vals[8]]
            self._state.gyro_dps = [vals[9], vals[10], vals[11]]
            self._state.rpy_deg = [vals[15], vals[16], vals[17]]
            self._state.voltage = vals[18] / 100.0
            self._state.odom_x = vals[19]
            self._state.odom_y = vals[20]
            self._state.odom_th = vals[21]
            self._state.ok_frames += 1
            self._state.connected = True
            self._last_rx = time.monotonic()
