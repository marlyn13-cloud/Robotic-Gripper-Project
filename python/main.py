"""
Robot Gripper — Hand Gesture Control
=====================================
Controls a 3D-printed gripper via Arduino Mega2560 using
hand gesture recognition (MediaPipe + OpenCV).

Usage:
    python main.py

Requirements:
    pip install pyserial customtkinter mediapipe opencv-contrib-python pillow
"""

from serial_controller import SerialController
from hand_tracker import HandTracker
from gui import GripperGUI


def main():
    serial = SerialController(baud_rate=9600)
    tracker = HandTracker(smoothing_window=5)
    app = GripperGUI(serial, tracker)
    app.start()


if __name__ == "__main__":
    main()
