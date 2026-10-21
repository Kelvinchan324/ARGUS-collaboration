"""Find the USB camera capture streams on this Raspberry Pi.

Each USB camera also exposes a metadata node.  The ``video-index0`` links
select capture streams, and their USB port paths stay stable when Linux
renumbers ``/dev/video*`` devices.
"""

from pathlib import Path


def find_usb_cameras():
    by_path = Path("/dev/v4l/by-path")
    devices = {}
    for link in sorted(by_path.glob("*usb*-video-index0")):
        if not link.is_symlink():
            continue
        target = link.resolve()
        if target.exists():
            # Some Raspberry Pi USB ports have two aliases for one device.
            devices.setdefault(target, link)
    return [str(link) for link in devices.values()]
