# Robotic-Gripper-Project

**Course:** CSIT431/CSIT531 — Introduction to Robotics

---

## Overview

Build a **Python GUI** (CustomTkinter) that controls a **3D-printed gripper** via an **Arduino Mega2560** over USB serial. A webcam feed uses **MediaPipe** to detect hand gestures, which open/close the gripper's **9g servo** in real time. The gripper must pick up **20 objects** of different shapes in a timed competition.

---

### Task
Use hand gesture recognition to control the gripper to **grasp objects from one box** and **deliver them to another box 30 cm away**.

### Rules
1. **20 objects** with different shapes, each labeled with a score
2. Distance between boxes: **30 cm**
3. **3 trials per object** — first-try success loses remaining trials for that object
4. Gripper must be controlled by **hand gesture recognition only**
5. **10 seconds per trial** — stop and start next trial if time runs out
6. Object falls INTO target box from gripper during delivery = **no points**
7. Object falls OUTSIDE target box = **get points but -1 deduction**
8. Gripper loses control = **-2 points per loss (max -8 deducted)**
9. Judges record scores on a performance sheet

---

## Part 1: 3D Design

### Selected Design
- **RobotGeek 9G Servo Gripper** — [Thingiverse thing:2083312](https://www.thingiverse.com/thing:2083312)
- Modify using **Tinkercad**, **Fusion 360**, or **Python (trimesh)**

### Design Requirements
| Parameter | Value |
|---|---|
| Hole size | 2.8 mm |
| Screw length compatibility | 18–24 mm |
| Servo attachment screws | No changes needed (keep as-is) |

### Bill of Materials (33 parts to print)

| # | Part | Qty | Notes |
|---|---|---|---|
| 1 | `BottomPlate.stl` | 1 | Base frame plate |
| 2 | `TopPlate.stl` | 1 | Top frame plate |
| 3 | `BackPlate.stl` | 1 | Rear structural support |
| 4 | `BackPlateSpacer.stl` | 1 | Rear spacer |
| 5 | `Gear.stl` | 1 | Central gear (servo-driven, hidden between plates) |
| 6 | `LeftFinger.stl` | **2** | Left gripper arms (stacked, has integrated gear teeth) |
| 7 | `RightFinger.stl` | **2** | Right gripper arms (stacked, has integrated gear teeth) |
| 8 | `FingerTip.stl` | **2** | Grip contact tips |
| 9 | `FingerTip-Plate.stl` | **4** | Tip mounting plates |
| 10 | `9GSpacer.stl` | 1 | Servo mount spacer |
| 11 | `9GSpacer-3mm.stl` | 1 | 3mm servo spacer variant |
| 12 | `3mmSpacer.stl` | **8** | General spacers (between plates) |
| 13 | `15mmStandoff.stl` | **8** | Standoffs (plate separation) |
| — | `Fitec-9g.stl` | — | Reference only — do NOT print |
| — | `GripperASM.stl` | — | Assembly reference — do NOT print |

### Hole Modifications (done via Python/trimesh)
- 7 parts modified: BottomPlate, TopPlate, LeftFinger, RightFinger, FingerTip-Plate, 3mmSpacer, 15mmStandoff
- All ~3.0 mm screw holes → **2.8 mm**
- Servo mount holes (2.0 mm) left unchanged

---

## Part 2: Hardware Setup

### System Diagram
```
  ┌──────────┐    USB     ┌──────────────┐   3 wires   ┌──────────┐
  │ COMPUTER │ ─────────> │   ARDUINO    │ ──────────> │ GRIPPER  │
  │ (Python  │   Serial   │  MEGA 2560   │  Red=5V     │ (9g Servo│
  │  GUI)    │            │              │  Brown=GND  │  inside) │
  └──────────┘            └──────────────┘  Yellow=A2  └──────────┘
       │
     Webcam
   (MediaPipe)
```

### Board
- **Arduino Mega2560** (provided by instructor)

### Servo Wiring
| Wire Color | Connect To |
|---|---|
| Red | 5V |
| Dark/Brown | Ground |
| Yellow/Signal | Pin **A2** (default in provided Arduino code) |

### Arduino Code
- Provided via Canvas — **no changes needed**
- Upload using Arduino IDE
- Install **Servo library**: [arduino.cc/libraries/servo](https://www.arduino.cc/reference/en/libraries/servo/)
- Serial port:
  - **Windows:** `COMx`
  - **macOS:** `/dev/cu.usbmodemXXXX`
- Python code supports **auto port detection**

---

## Part 3: Python Development

### Environment
- **Python version:** 3.11 or 3.12 (64-bit) — compatible with MediaPipe (supports 3.9–3.12)
- **IDE:** VSCode with **Python Extension Pack** (optional but recommended)

### Dependencies (install via pip)
```
pip install pyserial customtkinter mediapipe opencv-contrib-python
```

| Package | Purpose |
|---|---|
| `pyserial` | Serial communication with Arduino Mega2560 |
| `customtkinter` | Modern Python GUI framework |
| `mediapipe` | Hand landmark / gesture detection |
| `opencv-contrib-python` | Camera input & image processing |

### Architecture
1. **GUI (CustomTkinter)** — Main window with camera feed, controls, and status
2. **Hand Tracking (MediaPipe + OpenCV)** — Detect hand landmarks from webcam
3. **Gesture Interpretation** — Map hand open/close to gripper open/close commands
4. **Serial Communication (pyserial)** — Send servo angle commands to Arduino over USB
5. **Auto Port Detection** — Automatically find the connected Arduino serial port

### Workflow
1. Connect Arduino Mega2560 via USB (servo already wired)
2. Run the Python GUI (`python xxx.py`)
3. Select Python 3.x interpreter in VSCode if needed
4. Serial port is auto-detected (or manually set in code)
5. Webcam opens → MediaPipe tracks hand → gestures control gripper

---

## Part 4: Test Objects (20 in competition)

Items in the project box — each labeled with a score. Must grasp from one box and deliver to another (30 cm apart).

| # | Object | Notes | Difficulty |
|---|---|---|---|
| 1 | 9g Servo motor (blue) | Small, rigid, rectangular | Easy |
| 2 | Yellow servo/motor component | Small, irregular shape | Easy |
| 3 | 3D printed robotic arm/hand | Gray, multi-part, medium size | Medium |
| 4 | Long screw/bolt | Thin, cylindrical | Hard |
| 5 | Plastic fork | Lightweight, flat handle | Medium |
| 6 | Green lid/cap | Round, flat | Medium |
| 7 | Red container/jar | Cylindrical, medium | Easy |
| 8 | Yellow wheel/gear piece | Round with spokes | Medium |
| 9 | 3D printed head | Gray, large, heaviest item | Hard |
| 10 | Orange craft knife | Thin, elongated | Medium |
| 11 | Blue donut/ring | Round, hollow center | Medium |
| 12 | Tube (glue or similar) | Cylindrical, small | Easy |
| 13 | Small connectors & wires | Various tiny parts | Hard |

*Competition will have 20 objects total — these are samples.*

---

## Resources

### Servo Control
- [Arduino Servo Library](https://www.arduino.cc/reference/en/libraries/servo/)
- [Servo Motor with Arduino](https://makersportal.com/blog/2020/3/14/arduino-servo-motor-control)
- [Python + Arduino Servo](https://github.com/jumejume1/python-arduino-basic/tree/main/servo-control)

### Arduino Reference
- [Arrays](https://www.arduino.cc/reference/en/language/variables/data-types/array/)
- [If Statement](https://www.arduino.cc/reference/en/language/structure/control-structure/if/)
- [For Loops](https://www.arduino.cc/reference/en/language/structure/control-structure/for/)
- [While Loops](https://www.arduino.cc/reference/en/language/structure/control-structure/while/)

### Other Gripper Designs for Reference
- [EEZYbotARM](https://www.thingiverse.com/thing:2195839)
- [Simple 9g Servo Gripper](https://www.thingiverse.com/thing:2302957)
- [Rack & Pinion Gripper](https://www.thingiverse.com/thing:2661755)
- [3-Finger Chess Robot Gripper](https://www.thingiverse.com/thing:1322867)
- [Parametric Robot Claw](https://www.thingiverse.com/thing:27468)
----------
Demo Video Link

https://drive.google.com/file/d/11LuLujdieBRYz85RrpzKWeHXCLVEo9Aj/view?usp=sharing
