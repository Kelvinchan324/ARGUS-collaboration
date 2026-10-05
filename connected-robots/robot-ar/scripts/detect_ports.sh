#!/usr/bin/env bash
echo "=== USB ==="
lsusb || true
echo
echo "=== tty ==="
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "no ttyUSB/ttyACM"
echo
echo "=== by-id ==="
ls -l /dev/serial/by-id 2>/dev/null || echo "no /dev/serial/by-id"
echo
echo "Plug chassis USB-serial first. SO-ARM Feetech adapters usually appear as ttyACM*."
