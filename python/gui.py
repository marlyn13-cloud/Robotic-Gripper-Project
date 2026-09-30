"""
Gripper GUI.

How others ship OpenCV + Tk on macOS (see any “webcam + tkinter” tutorial, e.g. PyImageSearch /
StackOverflow): **VideoCapture.read() on the Tk main thread** inside a **root.after()** loop.
Background threads reading the camera often break or stall on macOS AVFoundation.

Live image widget: **tkinter.Label + ImageTk.PhotoImage** as a direct child of the CTk window
(CustomTkinter #2675 — CTkImage in a CTkLabel is unreliable for live video on some Mac/Tk builds).
https://github.com/TomSchimansky/CustomTkinter/issues/2675

If the window still paints nothing, install a Python build with a **non–Apple-stub Tk**
(e.g. python.org installer or `brew install python-tk@3.12`); Apple’s CLT Tk is deprecated and
often misbehaves with mixed Tk/CustomTkinter.
"""

from __future__ import annotations

import sys
import tkinter as tk

import customtkinter as ctk

# Avoid CTk scheduling check_dpi_scaling / update after-scripts that can TclError
# when mixed with classic Tk widgets or on close (Apple stub Tk + CustomTkinter).
try:
    ctk.deactivate_automatic_dpi_awareness()
except AttributeError:
    pass

import cv2
import numpy as np
from PIL import Image, ImageTk


class GripperGUI:
    def __init__(self, serial_controller, hand_tracker):
        self.serial = serial_controller
        self.tracker = hand_tracker
        self.cap = None
        self.running = False
        self.gesture_enabled = True

        self._cam_photo: ImageTk.PhotoImage | None = None
        self._last_bgr_for_resize: np.ndarray | None = None
        self._camera_label_size = (640, 480)
        self._tick_after_id: str | None = None

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Robot Gripper — Hand Gesture Control")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1, minsize=300)
        self.root.grid_rowconfigure(0, weight=1)

        # Build CTk side first, then native Tk video (avoids rare stacking glitches).
        self.right = ctk.CTkFrame(self.root, width=300)
        self.right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right = self.right

        conn_label = ctk.CTkLabel(right, text="Connection", font=("Arial", 18, "bold"))
        conn_label.pack(pady=(15, 5))

        self.port_var = ctk.StringVar(value="Auto-detect")
        self.port_menu = ctk.CTkOptionMenu(right, variable=self.port_var, values=["Auto-detect"], width=220)
        self.port_menu.pack(pady=5)

        self.refresh_btn = ctk.CTkButton(right, text="Refresh Ports", command=self._refresh_ports, width=220)
        self.refresh_btn.pack(pady=5)

        self.connect_btn = ctk.CTkButton(right, text="Connect", command=self._toggle_connection, width=220,
                                         fg_color="green", hover_color="darkgreen")
        self.connect_btn.pack(pady=5)

        self.conn_status = ctk.CTkLabel(right, text="Disconnected", text_color="red", font=("Arial", 13))
        self.conn_status.pack(pady=(0, 10))

        sep1 = ctk.CTkFrame(right, height=2, fg_color="gray50")
        sep1.pack(fill="x", padx=15, pady=5)

        servo_label = ctk.CTkLabel(right, text="Servo Control", font=("Arial", 18, "bold"))
        servo_label.pack(pady=(10, 5))

        self.angle_display = ctk.CTkLabel(right, text="Angle: 90°", font=("Arial", 28, "bold"))
        self.angle_display.pack(pady=5)

        self.angle_slider = ctk.CTkSlider(right, from_=0, to=180, number_of_steps=180,
                                          command=self._on_slider_change, width=220)
        self.angle_slider.set(90)
        self.angle_slider.pack(pady=5)

        slider_labels = ctk.CTkFrame(right, fg_color="transparent")
        slider_labels.pack(fill="x", padx=40)
        ctk.CTkLabel(slider_labels, text="0", font=("Arial", 11)).pack(side="left")
        ctk.CTkLabel(slider_labels, text="180", font=("Arial", 11)).pack(side="right")

        sep2 = ctk.CTkFrame(right, height=2, fg_color="gray50")
        sep2.pack(fill="x", padx=15, pady=10)

        self.gesture_switch = ctk.CTkSwitch(right, text="Hand Gesture Control",
                                            command=self._toggle_gesture, width=220)
        self.gesture_switch.select()
        self.gesture_switch.pack(pady=5)

        self.hand_status = ctk.CTkLabel(right, text="No hand detected", font=("Arial", 13), text_color="gray")
        self.hand_status.pack(pady=5)

        self.openness_bar = ctk.CTkProgressBar(right, width=220)
        self.openness_bar.set(0)
        self.openness_bar.pack(pady=5)

        openness_labels = ctk.CTkFrame(right, fg_color="transparent")
        openness_labels.pack(fill="x", padx=40)
        ctk.CTkLabel(openness_labels, text="Closed", font=("Arial", 11)).pack(side="left")
        ctk.CTkLabel(openness_labels, text="Open", font=("Arial", 11)).pack(side="right")

        sep3 = ctk.CTkFrame(right, height=2, fg_color="gray50")
        sep3.pack(fill="x", padx=15, pady=10)

        range_label = ctk.CTkLabel(right, text="Angle Range", font=("Arial", 14, "bold"))
        range_label.pack(pady=(5, 2))

        open_frame = ctk.CTkFrame(right, fg_color="transparent")
        open_frame.pack(fill="x", padx=30, pady=2)
        ctk.CTkLabel(open_frame, text="Open:", width=50).pack(side="left")
        self.open_angle_entry = ctk.CTkEntry(open_frame, width=60)
        self.open_angle_entry.insert(0, "10")
        self.open_angle_entry.pack(side="right")

        close_frame = ctk.CTkFrame(right, fg_color="transparent")
        close_frame.pack(fill="x", padx=30, pady=2)
        ctk.CTkLabel(close_frame, text="Close:", width=50).pack(side="left")
        self.close_angle_entry = ctk.CTkEntry(close_frame, width=60)
        self.close_angle_entry.insert(0, "170")
        self.close_angle_entry.pack(side="right")

        # --- Left: native Tk video (direct child of CTk root — issue #2675 style) ---
        self._left_tk = tk.Frame(self.root, bg="#1a1a1a")
        self._left_tk.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self._left_tk.grid_rowconfigure(0, weight=1)
        self._left_tk.grid_columnconfigure(0, weight=1)

        self._tk_video_label = tk.Label(
            self._left_tk,
            text="Starting camera…",
            fg="#cccccc",
            bg="#1a1a1a",
            font=("Helvetica", 16),
        )
        self._tk_video_label.grid(row=0, column=0, sticky="nsew")
        self._tk_video_label.bind("<Configure>", self._on_camera_label_configure)

        self.status_bar = ctk.CTkLabel(self.root, text="Ready", font=("Arial", 12), anchor="w")
        self.status_bar.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")

    def _on_camera_label_configure(self, event):
        try:
            if event.width > 10 and event.height > 10:
                self._camera_label_size = (event.width, event.height)
                if self._last_bgr_for_resize is not None and self.running:
                    self._set_bgr_frame(self._last_bgr_for_resize)
        except tk.TclError:
            pass

    def _set_bgr_frame(self, frame: np.ndarray) -> None:
        self._last_bgr_for_resize = frame

        tw, th = self._target_size_for_frame(frame)
        resized = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)

        if resized.shape[2] == 4:
            rgba = cv2.cvtColor(resized, cv2.COLOR_BGRA2RGBA)
            frame_pil = Image.fromarray(rgba, mode="RGBA")
        else:
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(rgb, mode="RGB")

        try:
            self._cam_photo = ImageTk.PhotoImage(frame_pil)
            self._tk_video_label.configure(image=self._cam_photo, text="")
            self._tk_video_label.image = self._cam_photo
        except tk.TclError:
            pass

    def _target_size_for_frame(self, frame: np.ndarray) -> tuple[int, int]:
        frame_h, frame_w = frame.shape[:2]
        target_w, target_h = self._camera_label_size
        target_w = max(1, target_w)
        target_h = max(1, target_h)

        if frame_w / frame_h > target_w / target_h:
            target_h = max(1, int(frame_h * target_w / frame_w))
        else:
            target_w = max(1, int(frame_w * target_h / frame_h))

        return target_w, target_h

    def _schedule_tick(self, ms: int) -> None:
        if not self.running:
            return
        try:
            if not bool(self.root.winfo_exists()):
                return
        except tk.TclError:
            return
        self._tick_after_id = self.root.after(ms, self._tick)

    def _tick(self) -> None:
        if not self.running:
            return
        try:
            if not bool(self.root.winfo_exists()):
                return
        except tk.TclError:
            return

        try:
            # Main thread only — required for reliable macOS camera + Tk.
            ret, frame = self.cap.read()
            if not ret:
                self._schedule_tick(30)
                return

            if frame.ndim == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            frame = cv2.flip(frame, 1)
            frame, openness = self.tracker.process_frame(frame)

            if openness is not None:
                self.hand_status.configure(text="Hand detected", text_color="green")
                self.openness_bar.set(openness)

                if self.gesture_enabled:
                    open_a, close_a = self._get_angle_range()
                    angle = self.tracker.openness_to_angle(openness, open_a, close_a)
                    if angle is not None:
                        # TODO (from Arduino repo idea): skip serial write when angle hasn't
                        # changed since last frame — their "prev_finger_count" pattern.
                        # Could store self._prev_angle and compare here to avoid redundant
                        # serial traffic (currently rate-limited at 50ms in SerialController,
                        # but dedup would reduce it further).
                        self.angle_display.configure(text=f"Angle: {angle}°")
                        self.angle_slider.set(angle)
                        self.serial.send_angle(angle)
            else:
                self.hand_status.configure(text="No hand detected", text_color="gray")

            self.root.update_idletasks()
            self._set_bgr_frame(frame)
        except tk.TclError:
            return
        except Exception:
            # Do not kill the loop on transient errors
            pass

        self._schedule_tick(16)

    def _refresh_ports(self):
        ports = self.serial.list_ports()
        port_names = ["Auto-detect"] + [f"{dev} — {desc}" for dev, desc in ports]
        self.port_menu.configure(values=port_names)
        self.status_bar.configure(text=f"Found {len(ports)} port(s)")

    def _toggle_connection(self):
        if self.serial.connected:
            self.serial.disconnect()
            self.connect_btn.configure(text="Connect", fg_color="green", hover_color="darkgreen")
            self.conn_status.configure(text="Disconnected", text_color="red")
            self.status_bar.configure(text="Disconnected")
        else:
            try:
                selected = self.port_var.get()
                port = None if selected == "Auto-detect" else selected.split(" — ")[0]
                connected_port = self.serial.connect(port)
                self.connect_btn.configure(text="Disconnect", fg_color="red", hover_color="darkred")
                self.conn_status.configure(text=f"Connected: {connected_port}", text_color="green")
                self.status_bar.configure(text=f"Connected to {connected_port}")
            except ConnectionError as e:
                self.conn_status.configure(text="Connection failed", text_color="red")
                self.status_bar.configure(text=str(e))

    def _toggle_gesture(self):
        self.gesture_enabled = self.gesture_switch.get() == 1

    def _on_slider_change(self, value):
        angle = int(value)
        self.angle_display.configure(text=f"Angle: {angle}°")
        if not self.gesture_enabled:
            self.serial.send_angle(angle)

    def _get_angle_range(self):
        try:
            open_a = int(self.open_angle_entry.get())
            close_a = int(self.close_angle_entry.get())
            return max(0, min(180, open_a)), max(0, min(180, close_a))
        except ValueError:
            return 10, 170

    def start(self):
        """Open camera and start the main GUI loop."""
        if sys.platform == "darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
            self.cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        else:
            self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.status_bar.configure(text="ERROR: Cannot open camera")
            self.root.mainloop()
            return

        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # NOTE (cam settings comparison — Arduino repo):
        # Their repo uses bare cv2.VideoCapture(0) with no backend, no buffer
        # tuning, no resolution/fps props. Our setup is already more robust:
        #   - CAP_AVFOUNDATION on macOS (avoids V4L / GStreamer probe)
        #   - BUFFERSIZE=1 to minimize latency
        #   - BGRA→BGR guard in _tick()
        # Possible additions if needed:
        #   self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        #   self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        #   self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.running = True
        self.status_bar.configure(text="Camera active — show your hand to control gripper")
        self._refresh_ports()
        self.root.update_idletasks()
        # Do not call root.update() — it fights CustomTkinter's own after("update", …) on macOS.
        self._schedule_tick(1)
        self.root.mainloop()

    def _on_close(self):
        """Clean shutdown."""
        self.running = False
        if self._tick_after_id is not None:
            try:
                self.root.after_cancel(self._tick_after_id)
            except tk.TclError:
                pass
            self._tick_after_id = None
        if self.cap:
            self.cap.release()
        self.tracker.release()
        self.serial.disconnect()
        self._cam_photo = None
        self._last_bgr_for_resize = None
        try:
            self.root.destroy()
        except tk.TclError:
            pass
