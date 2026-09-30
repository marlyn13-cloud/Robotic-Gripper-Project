"""
Quick servo test — sweeps between full open and full close.
No camera, no MediaPipe, just serial.

Usage:
    python test_servo.py
"""

import serial
import serial.tools.list_ports
import time
import sys


def find_arduino():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        desc = (port.description or "").lower()
        mfr = (port.manufacturer or "").lower()
        combined = desc + " " + mfr
        if any(k in combined for k in ["arduino", "mega", "usbmodem", "usbserial", "ch340", "cp210"]):
            return port.device
    for port in ports:
        if "usbmodem" in port.device or "usbserial" in port.device or "COM" in port.device:
            return port.device
    return None


def main():
    port = find_arduino()
    if not port:
        print("No Arduino found. Available ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device} — {p.description}")
        sys.exit(1)

    print(f"Connecting to {port} ...")
    ser = serial.Serial(port, 9600, timeout=1)
    time.sleep(2)  # Arduino resets on connect

    if ser.in_waiting:
        print(f"Arduino says: {ser.readline().decode().strip()}")

    OPEN_ANGLE = 10
    CLOSE_ANGLE = 170
    STEP = 5
    DELAY = 0.03  # seconds between steps

    print(f"\nSweeping servo: {OPEN_ANGLE}° (open) <-> {CLOSE_ANGLE}° (close)")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Open → Close
            print("Closing ...", end="", flush=True)
            for angle in range(OPEN_ANGLE, CLOSE_ANGLE + 1, STEP):
                ser.write(f"{angle}\n".encode())
                time.sleep(DELAY)
            print(f" {CLOSE_ANGLE}°")
            time.sleep(0.5)

            # Close → Open
            print("Opening ...", end="", flush=True)
            for angle in range(CLOSE_ANGLE, OPEN_ANGLE - 1, -STEP):
                ser.write(f"{angle}\n".encode())
                time.sleep(DELAY)
            print(f" {OPEN_ANGLE}°")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\nStopped. Setting servo to 90° (middle).")
        ser.write(b"90\n")
        time.sleep(0.3)

    ser.close()
    print("Done.")


if __name__ == "__main__":
    main()
