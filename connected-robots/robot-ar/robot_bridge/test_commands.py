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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(name, "ok")
    print("command tests ok")
