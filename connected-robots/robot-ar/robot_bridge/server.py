#!/usr/bin/env python3
"""Phase-1 robot bridge + language task runner."""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from arms import DualArmDriver
from chassis_serial import ChassisDriver
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
        "task": runner.snapshot(),
        "camera": cameras.status(),
        "vla": vla.capabilities(),
        "capabilities": capabilities(),
        "inventory": inventory(),
    }


@app.get("/capabilities")
def capabilities():
    st = driver.snapshot()
    return {
        "chassis": {"wired": st.connected and not st.mock, "mode": "serial" if st.connected and not st.mock else "mock"},
        "arms": {"wired": False, "mode": "mock"},
        "camera": cameras.status(),
        "vla_act": vla.capabilities(),
    }


@app.get("/inventory")
def inventory():
    st = driver.snapshot()
    chassis_on = bool(st.connected and not st.mock)
    arm_on = False
    cam_on = bool(cameras.status().get("devices"))
    return [
        {"part": "Compute", "model": "NVIDIA Jetson Thor", "role": "Onboard computer", "status": "connected"},
        {"part": "Chassis MCU", "model": "STM32 USB-UART 115200", "role": "Wheelbase controller", "status": "connected" if chassis_on else "disconnected"},
        {"part": "Drive motors", "model": "4× steer-drive", "role": "Locomotion", "status": "connected" if chassis_on else "disconnected"},
        {"part": "Left arm", "model": "SO-ARM100/101 · STS3215 ×6", "role": "Left manipulator", "status": "connected" if arm_on else "disconnected"},
        {"part": "Right arm", "model": "SO-ARM100/101 · STS3215 ×6", "role": "Right manipulator", "status": "connected" if arm_on else "disconnected"},
        {"part": "Left gripper", "model": "Robonine parallel · STS3215", "role": "Left grasp", "status": "connected" if arm_on else "disconnected"},
        {"part": "Right gripper", "model": "Robonine parallel · STS3215", "role": "Right grasp", "status": "connected" if arm_on else "disconnected"},
        {"part": "Camera", "model": "USB / RealSense", "role": "Perception", "status": "connected" if cam_on else "disconnected"},
        {"part": "VLA", "model": "vla_act slot", "role": "Contact policy", "status": "connected" if vla.capabilities()["wired"] else "disconnected"},
    ]


@app.get("/camera/latest")
def camera_latest():
    return cameras.latest()


@app.get("/camera/snapshot.svg")
def camera_snapshot():
    st = cameras.latest()
    if st.get("devices") and st.get("frame") is None:
        label = "device present · capture not wired"
    else:
        label = "camera disconnected"
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


@app.post("/arm/{side}")
def arm(side: str, body: ArmCommand):
    if side not in {"left", "right", "both"}:
        raise HTTPException(400, "side must be left, right, or both")
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


@app.post("/gripper/{side}")
def gripper(side: str, body: GripperCommand):
    if side not in {"left", "right", "both"}:
        raise HTTPException(400, "side must be left, right, or both")
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
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--serial", default=os.environ.get("CHASSIS_PORT", "auto"))
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--timeout-ms", type=int, default=500)
    return p.parse_args()


def main() -> None:
    global driver, arms, runner, cameras, vla
    args = parse_args()
    port, missing = pick_chassis_port(None if args.serial == "auto" else args.serial)
    mock = args.mock
    if missing and not mock:
        print(f"[robot_bridge] {port} not present yet; waiting for USB (not mock)")
    driver = ChassisDriver(port=port, baud=args.baud, timeout_ms=args.timeout_ms, mock=mock)
    driver.start()
    arms = DualArmDriver(mock=True)
    runner = TaskRunner(driver, arms)
    cameras = CameraHub()
    vla = VLARuntime(cameras, arms, driver)
    mode = "MOCK (no chassis USB)" if mock else f"SERIAL {port}"
    print(f"[robot_bridge] {mode}  http://{args.host}:{args.port}/")
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
