import serial
import serial.tools.list_ports
import threading
import time


class SerialController:
    def __init__(self, baud_rate=9600):
        self.baud_rate = baud_rate
        self.connection = None
        self.connected = False
        self.port_name = None
        self._lock = threading.Lock()
        self._last_send_time = 0
        self._min_interval = 0.05  # 50ms between commands

    def auto_detect_port(self):
        """Find the Arduino Mega serial port automatically."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            desc = (port.description + " " + port.manufacturer).lower() if port.manufacturer else port.description.lower()
            if any(keyword in desc for keyword in ["arduino", "mega", "usb", "usbmodem", "usbserial", "ch340", "cp210"]):
                return port.device
        # Fallback: return first /dev/cu.usbmodem or COM port
        for port in ports:
            if "usbmodem" in port.device or "usbserial" in port.device or "COM" in port.device:
                return port.device
        return None

    def list_ports(self):
        """Return list of available serial ports."""
        return [(p.device, p.description) for p in serial.tools.list_ports.comports()]

    def connect(self, port=None):
        """Connect to Arduino. Auto-detects port if not specified."""
        if self.connected:
            self.disconnect()

        if port is None:
            port = self.auto_detect_port()
        if port is None:
            raise ConnectionError("No Arduino found. Check USB cable.")

        try:
            self.connection = serial.Serial(port, self.baud_rate, timeout=1)
            time.sleep(2)  # Arduino resets on serial connect
            self.port_name = port
            self.connected = True
            # Read the READY message
            if self.connection.in_waiting:
                self.connection.readline()
            return port
        except serial.SerialException as e:
            self.connected = False
            raise ConnectionError(f"Could not connect to {port}: {e}")

    def disconnect(self):
        """Close the serial connection."""
        with self._lock:
            if self.connection and self.connection.is_open:
                self.connection.close()
            self.connected = False
            self.port_name = None

    def send_angle(self, angle):
        """Send a servo angle (0-180) to Arduino. Rate-limited to 50ms."""
        if not self.connected:
            return False

        angle = max(0, min(180, int(angle)))

        # TODO (from Arduino repo idea): add self._prev_angle and skip write
        # when angle == self._prev_angle, like their prev_finger_count pattern.
        # Currently we already rate-limit at 50ms, but dedup would also avoid
        # sending identical values when the hand is steady.

        now = time.time()
        if now - self._last_send_time < self._min_interval:
            return True  # Skip, too fast

        with self._lock:
            try:
                self.connection.write(f"{angle}\n".encode())
                self._last_send_time = now
                return True
            except serial.SerialException:
                self.connected = False
                return False

    def read_response(self):
        """Read a response line from Arduino (non-blocking)."""
        if not self.connected:
            return None
        with self._lock:
            try:
                if self.connection.in_waiting:
                    return self.connection.readline().decode().strip()
            except serial.SerialException:
                self.connected = False
        return None
