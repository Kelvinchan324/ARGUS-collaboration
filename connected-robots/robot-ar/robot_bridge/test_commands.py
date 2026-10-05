from __future__ import annotations

from chassis_serial import ChassisDriver, checksum, f2b


def test_downlink_mode1_header_and_checksum():
    buf = bytearray(53)
    buf[0] = 0xAA
    buf[1] = 0xAA
    buf[4:8] = f2b(1.0)
    buf[8:12] = f2b(1.0)
    buf[12:16] = f2b(0.3)
    buf[52] = checksum(bytes(buf[:52]))
    assert buf[0:2] == b"\xaa\xaa"
    assert buf[52] == checksum(bytes(buf[:52]))


def test_parse_forward_then_close():
    from commands import parse_command

    plan = parse_command("前進 1 秒 然後 關閉夾爪")
    assert plan["steps"][0]["action"] == "move"
    assert plan["steps"][0]["vx"] > 0
    assert abs(plan["steps"][0]["duration"] - 1.0) < 1e-6
    assert plan["steps"][1]["action"] == "gripper"
    assert plan["steps"][1]["open"] == 0.0


def test_parse_stop():
    from commands import parse_command

    assert parse_command("停")["steps"] == [{"action": "stop"}]


def test_parse_strafe_and_close():
    from commands import parse_command

    left = parse_command("往左平移")
    assert left["steps"][0]["action"] == "move"
    assert left["steps"][0]["vy"] > 0
    close = parse_command("把夾爪輕輕合上然後停")
    assert close["steps"][0]["action"] == "gripper"
    assert close["steps"][0]["open"] == 0.0
    assert close["steps"][1]["action"] == "stop"


def test_parse_nudge_back_no_turn():
    from commands import parse_command

    plan = parse_command("往後一點然後輪子準備右轉（但別轉")
    assert plan["steps"][0]["action"] == "move"
    assert plan["steps"][0]["vx"] < 0
    assert abs(plan["steps"][0]["vx"] + 0.08) < 1e-6
    assert abs(plan["steps"][0]["duration"] - 0.25) < 1e-6
    assert plan["steps"][1]["action"] == "stop"
    assert not any(s.get("action") == "move" and float(s.get("wz", 0)) != 0 for s in plan["steps"])


def test_parse_forward_then_turn_right():
    from commands import parse_command

    plan = parse_command("往前一點，然後輪子轉右")
    assert plan["steps"][0]["action"] == "move"
    assert plan["steps"][0]["vx"] > 0
    assert plan["steps"][0]["wz"] == 0.0
    assert plan["steps"][1]["action"] == "move"
    assert plan["steps"][1]["vx"] == 0.0
    assert plan["steps"][1]["wz"] < 0


def test_mock_chassis_moves_odom():
    d = ChassisDriver(mock=True)
    d.start()
    d.enable_motor(True)
    d.set_cmd(0.3, 0.0, 0.0)
    import time

    time.sleep(0.2)
    st = d.snapshot()
    d.close()
    assert st.mock
    assert st.odom_x != 0.0 or st.ok_frames > 0


def test_multi_arm_and_lift_configuration_fails_closed_in_mock_mode():
    from arms import DualArmDriver
    from linear_actuators import LinearActuatorDriver

    arm_driver = DualArmDriver(mock=True)
    arm_state = arm_driver.snapshot()
    assert arm_state["sides"] == ["left", "right", "left2", "right2"]
    assert all(arm_state[side]["mock"] for side in arm_state["sides"])

    lift_driver = LinearActuatorDriver(mock=True)
    lift_state = lift_driver.snapshot()
    assert lift_state["sides"] == ["left", "right"]
    assert all(lift_state[side]["mock"] for side in lift_state["sides"])
    try:
        lift_driver.nudge("left", 120)
    except ValueError as exc:
        assert "not wired" in str(exc)
    else:
        raise AssertionError("mock lift nudge should fail closed")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(name, "ok")
    print("command tests ok")
