#!/usr/bin/env python3
"""Phase-1 robot bridge + language task runner."""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from arms import DualArmDriver
from chassis_serial import ChassisDriver
from linear_actuators import LinearActuatorDriver
from perception import CameraHub
from tasks import TaskRunner
from vla import VLARuntime

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
AGENT = ROOT.parent / "agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))
from planner import plan as plan_command

driver: ChassisDriver | None = None
arms: DualArmDriver | None = None
lifts: LinearActuatorDriver | None = None
runner: TaskRunner | None = None
cameras: CameraHub | None = None
vla: VLARuntime | None = None

app = FastAPI(title="bimanual robot_bridge", version="0.3.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class CmdVel(BaseModel):
    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0


class MotorEnable(BaseModel):
    enabled: bool = True


class ArmCommand(BaseModel):
    joints: list[float] = Field(default_factory=list)
    gripper: float | None = None
    preset: str | None = None


class GripperCommand(BaseModel):
    open: float = 0.0


class NudgeBody(BaseModel):
    joint: int = Field(description="servo id 1-5")
    delta: int = 80


class LiftNudgeBody(BaseModel):
    delta: int = 120


class CommandBody(BaseModel):
    text: str
    plan_only: bool = False


class TaskBody(BaseModel):
    steps: list[dict]
    text: str = ""


class VLAActBody(BaseModel):
    instruction: str
    timeout_s: float = 4.0


def list_serial_ports() -> list[str]:
    ports = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    by_id = sorted(glob.glob("/dev/serial/by-id/*"))
    return by_id or ports


_ollama_cache: tuple[float, dict] = (0.0, {})


def ollama_status() -> dict:
    global _ollama_cache
    now = time.monotonic()
    ts, cached = _ollama_cache
    if cached and now - ts < 15:
        return cached
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    out = {"ollama": False, "host": host, "model": model, "models": []}
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=0.6) as resp:
            body = json.loads(resp.read().decode())
        names = [m.get("name") or m.get("model") for m in body.get("models") or []]
        out["models"] = [n for n in names if n]
        out["ollama"] = any(n == model or n.startswith(model.split(":")[0]) for n in out["models"])
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        out["ollama"] = False
    _ollama_cache = (now, out)
    return out


def pick_chassis_port(requested: str | None) -> tuple[str, bool]:
    if requested and requested != "auto":
        return requested, not os.path.exists(requested)
    ports = list_serial_ports()
    if ports:
        return ports[0], False
    return "/dev/ttyUSB0", True


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    st = driver.snapshot()
    cap = capabilities()
    return {
        "ok": True,
        "connected": st.connected,
        "mock": st.mock,
        "port": st.port,
        "vision_wired": cap["camera"]["wired"] and cap["vla_act"]["wired"],
    }


@app.get("/state")
def state():
    st = driver.snapshot()
    return {
        "chassis": st.__dict__,
        "serial_ports": list_serial_ports(),
        "arms": arms.snapshot(),
        "lifts": lifts.snapshot(),
        "task": runner.snapshot(),
        "camera": cameras.status(),
        "vla": vla.capabilities(),
        "capabilities": capabilities(),
        "inventory": inventory(),
    }


@app.get("/capabilities")
def capabilities():
    st = driver.snapshot()
    snap = arms.snapshot()
    arm_caps = {}
    any_wired = False
    for side in snap.get("sides") or ["left", "right"]:
        a = snap.get(side) or {}
        wired = (not a.get("mock")) and a.get("ready")
        any_wired = any_wired or bool(wired)
        arm_caps[side] = {
            "wired": bool(wired),
            "port": a.get("port"),
            "ids": list(a.get("ids") or []),
            "error": a.get("error"),
        }
    lift_snap = lifts.snapshot()
    lift_caps = {}
    any_lift = False
    for side in lift_snap.get("sides") or ["left", "right"]:
        L = lift_snap.get(side) or {}
        wired = (not L.get("mock")) and L.get("ready")
        any_lift = any_lift or bool(wired)
        lift_caps[side] = {
            "wired": bool(wired),
            "port": L.get("port") or lift_snap.get("port"),
            "ids": list(L.get("ids") or []),
            "error": L.get("error"),
        }
    return {
        "chassis": {"wired": st.connected and not st.mock, "mode": "serial" if st.connected and not st.mock else "mock"},
        "arms": {
            "wired": any_wired,
            "mode": "serial" if any_wired else "mock",
            "sides": list(arm_caps.keys()),
            **arm_caps,
        },
        "lifts": {
            "wired": any_lift,
            "mode": "serial" if any_lift else "mock",
            "sides": list(lift_caps.keys()),
            **lift_caps,
        },
        "camera": cameras.status(),
        "vla_act": vla.capabilities(),
        "planner": ollama_status(),
    }


@app.get("/inventory")
def inventory():
    st = driver.snapshot()
    snap = arms.snapshot()
    chassis_on = bool(st.connected and not st.mock)
    labels = {
        "left": ("Left arm", "Left gripper", "Left manipulator", "Left grasp"),
        "right": ("Right arm", "Right gripper", "Right manipulator", "Right grasp"),
        "left2": ("Left arm 2", "Left gripper 2", "Left manipulator 2", "Left grasp 2"),
        "right2": ("Right arm 2", "Right gripper 2", "Right manipulator 2", "Right grasp 2"),
    }
    rows = [
        {"part": "Compute", "model": "Mini PC · NucBox G2", "role": "Onboard computer", "status": "connected"},
        {"part": "Chassis MCU", "model": "STM32 USB-UART 115200", "role": "Wheelbase controller", "status": "connected" if chassis_on else "disconnected"},
        {"part": "Drive motors", "model": "4× steer-drive", "role": "Locomotion", "status": "connected" if chassis_on else "disconnected"},
    ]
    for side in snap.get("sides") or ["left", "right"]:
        a = snap.get(side) or {}
        on = (not a.get("mock")) and a.get("ready")
        grip_on = on and (6 in (a.get("ids") or []))
        arm_name, grip_name, arm_role, grip_role = labels.get(
            side, (f"Arm {side}", f"Gripper {side}", f"Manipulator {side}", f"Grasp {side}")
        )
        rows.append({"part": arm_name, "model": "SO-ARM100/101 · STS3215 ×6", "role": arm_role, "status": "connected" if on else "disconnected"})
        rows.append({"part": grip_name, "model": "Robonine parallel · STS3215", "role": grip_role, "status": "connected" if grip_on else "disconnected"})
    lift_snap = lifts.snapshot()
    lift_labels = {"left": "Left lift", "right": "Right lift"}
    for side in lift_snap.get("sides") or ["left", "right"]:
        L = lift_snap.get(side) or {}
        on = (not L.get("mock")) and L.get("ready")
        rows.append({
            "part": lift_labels.get(side, f"Lift {side}"),
            "model": "Linear actuator · STS3215 ×2",
            "role": f"{side} vertical lift",
            "status": "connected" if on else "disconnected",
        })
    cam_on = bool(cameras.status().get("devices"))
    rows.append({"part": "Camera", "model": "USB / RealSense", "role": "Perception", "status": "connected" if cam_on else "disconnected"})
    rows.append({"part": "VLA", "model": "vla_act slot", "role": "Contact policy", "status": "connected" if vla.capabilities()["wired"] else "disconnected"})
    return rows


@app.get("/camera/latest")
def camera_latest():
    return cameras.latest()


@app.get("/camera/snapshot.svg")
@app.get("/camera/frame.jpg")
def camera_snapshot():
    data = cameras.jpeg() if hasattr(cameras, "jpeg") else None
    if data:
        return Response(content=data, media_type="image/jpeg")
    st = cameras.latest()
    label = (st.get("reason") or "camera disconnected").replace("<", "")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360">'
        '<rect width="640" height="360" fill="#0c0c0c"/>'
        f'<text x="320" y="180" fill="#8a8a8a" text-anchor="middle" '
        f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="16">{label}</text>'
        "</svg>"
    )
    return Response(content=svg, media_type="image/svg+xml")


@app.post("/vla_act")
def vla_act(body: VLAActBody):
    result = vla.act(body.instruction, body.timeout_s)
    if not result["ok"]:
        return JSONResponse(status_code=503, content=result)
    return result


@app.post("/cmd_vel")
def cmd_vel(body: CmdVel):
    driver.set_cmd(body.vx, body.vy, body.wz)
    return {"ok": True, "vx": body.vx, "vy": body.vy, "wz": body.wz}


@app.post("/stop")
def stop():
    runner.cancel()
    driver.stop()
    driver.enable_motor(False)
    arms.estop()
    lifts.estop()
    return {"ok": True, "stopped": True}


@app.post("/motor")
def motor(body: MotorEnable):
    driver.enable_motor(body.enabled)
    if not body.enabled:
        driver.stop()
    return {"ok": True, "enabled": body.enabled}


@app.post("/reset_odom")
def reset_odom():
    driver.reset_odom()
    return {"ok": True}


def _valid_arm_side(side: str) -> bool:
    if side == "both":
        return True
    return side in arms.arm_names()


@app.post("/arm/{side}")
def arm(side: str, body: ArmCommand):
    if not _valid_arm_side(side):
        raise HTTPException(400, f"side must be one of {arms.arm_names()} or both")
    try:
        if body.preset:
            arms.set_preset(side, body.preset)
        elif body.joints:
            arms.set_joints(side, body.joints)
        if body.gripper is not None:
            arms.set_gripper(side, body.gripper)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "arms": arms.snapshot()}


@app.post("/arm/{side}/nudge")
def arm_nudge(side: str, body: NudgeBody):
    if not _valid_arm_side(side):
        raise HTTPException(400, f"side must be one of {arms.arm_names()} or both")
    try:
        info = arms.nudge(side, body.joint, body.delta)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"ok": True, "nudge": info, "arms": arms.snapshot()}


def _valid_lift_side(side: str) -> bool:
    return side in lifts.side_names()


@app.post("/lift/{side}/nudge")
def lift_nudge(side: str, body: LiftNudgeBody):
    if not _valid_lift_side(side):
        raise HTTPException(400, f"lift side must be one of {lifts.side_names()}")
    try:
        info = lifts.nudge(side, body.delta)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"ok": True, "nudge": info, "lifts": lifts.snapshot()}


@app.post("/gripper/{side}")
def gripper(side: str, body: GripperCommand):
    if not _valid_arm_side(side):
        raise HTTPException(400, f"side must be one of {arms.arm_names()} or both")
    try:
        arms.set_gripper(side, body.open)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "arms": arms.snapshot()}


@app.post("/command")
def command(body: CommandBody):
    try:
        planned = plan_command(body.text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if body.plan_only:
        return {"ok": True, "plan_only": True, **planned}
    try:
        result = runner.start(planned["text"], planned["steps"])
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True, "plan_only": False, "source": planned.get("source"), **result}


@app.post("/task")
def task(body: TaskBody):
    try:
        result = runner.start(body.text or "task", body.steps)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True, **result}


@app.get("/task")
def task_status():
    return runner.snapshot()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--serial", default=os.environ.get("CHASSIS_PORT", "auto"))
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--timeout-ms", type=int, default=500)
    return p.parse_args()


def main() -> None:
    global driver, arms, lifts, runner, cameras, vla
    args = parse_args()
    port, missing = pick_chassis_port(None if args.serial == "auto" else args.serial)
    mock = args.mock
    if missing and not mock:
        print(f"[robot_bridge] {port} not present yet; waiting for USB (not mock)")
    driver = ChassisDriver(port=port, baud=args.baud, timeout_ms=args.timeout_ms, mock=mock)
    driver.start()
    arms = DualArmDriver(mock=False)
    lifts = LinearActuatorDriver(mock=False)
    runner = TaskRunner(driver, arms)
    cameras = CameraHub()
    vla = VLARuntime(cameras, arms, driver)
    mode = "MOCK (no chassis USB)" if mock else f"SERIAL {port}"
    print(f"[robot_bridge] {mode}  http://0.0.0.0:{args.port}/")
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
