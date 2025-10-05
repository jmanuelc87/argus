import time
import queue
import logging
import threading

import tkinter as tk
from tkinter import ttk

from argus.serial import Driver

log = logging.getLogger(__file__)


MIN_PULSE = 100
MAX_PULSE = 3900
DEFAULT_PULSE = (MIN_PULSE + MAX_PULSE) // 2  # 2000


class ServoControllerFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.parent = parent
        self.scales = []
        self.send_on_change = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")

        self._debounce_after_id = None
        self._debounce_idx = None
        self._debounce_value = None

        self._serial_lock = self.parent._serial_lock

        # Create three servo rows
        for i in range(3):
            row = self._make_servo_row(self, i + 1)
            row.grid(row=i, column=0, sticky="ew", pady=(0, 10))
            self.columnconfigure(0, weight=1)

        # Button row
        btn_row = ttk.Frame(self)
        btn_row.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        btn_row.columnconfigure((0, 1, 2, 3), weight=1)

        ttk.Button(btn_row, text="Center All", command=self.center_all).grid(
            row=0, column=0, padx=4
        )
        ttk.Button(
            btn_row, text="Min All", command=lambda: self.set_all(MIN_PULSE)
        ).grid(row=0, column=1, padx=4)
        ttk.Button(
            btn_row, text="Max All", command=lambda: self.set_all(MAX_PULSE)
        ).grid(row=0, column=2, padx=4)
        ttk.Button(btn_row, text="Print Values", command=self.print_values).grid(
            row=0, column=3, padx=4
        )

        # Optional: send on change toggle
        ttk.Checkbutton(
            self, text="Trigger callback on change", variable=self.send_on_change
        ).grid(row=4, column=0, sticky="w")

        # Status line
        status = ttk.Label(self, textvariable=self.status_var, anchor="w")
        status.grid(row=5, column=0, sticky="ew", pady=(8, 0))

    def _make_servo_row(self, parent, idx: int):
        frame = ttk.LabelFrame(parent, text=f"Servo {idx}")

        value_var = tk.IntVar(value=DEFAULT_PULSE)
        value_lbl = ttk.Label(frame, textvariable=value_var, width=5, anchor="e")

        scale = ttk.Scale(
            frame,
            from_=MIN_PULSE,
            to=MAX_PULSE,
            orient="horizontal",
            command=lambda _val, v=value_var, i=idx: self._on_scale_change(v, i, _val),
        )
        scale.set(DEFAULT_PULSE)

        min_lbl = ttk.Label(frame, text=str(MIN_PULSE))
        max_lbl = ttk.Label(frame, text=str(MAX_PULSE))

        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Pulse:").grid(
            row=0, column=0, padx=(8, 6), pady=8, sticky="w"
        )
        scale.grid(row=0, column=1, padx=6, pady=8, sticky="ew")
        value_lbl.grid(row=0, column=2, padx=(6, 8))
        min_lbl.grid(row=1, column=1, sticky="w", padx=6)
        max_lbl.grid(row=1, column=1, sticky="e", padx=6)

        self.scales.append((scale, value_var))
        return frame

    def _on_scale_change(self, value_var: tk.IntVar, idx: int, raw_value: str):
        ivalue = int(float(raw_value))
        value_var.set(ivalue)
        self.status_var.set(f"Servo {idx}: {ivalue}")

        if self.send_on_change.get():
            # debounce: cancel previous scheduled callback
            if self._debounce_after_id is not None:
                self.after_cancel(self._debounce_after_id)

            # store latest values
            self._debounce_idx = idx
            self._debounce_value = ivalue

            # schedule new callback after 450ms
            self._debounce_after_id = self.after(450, self._debounced_callback)

    def _debounced_callback(self):
        """Actually trigger the on_servo_change after debounce period."""
        if self._debounce_idx is not None and self._debounce_value is not None:
            self.on_servo_change(self._debounce_idx, self._debounce_value)
        self._debounce_after_id = None

    def center_all(self):
        self.set_all(DEFAULT_PULSE)

    def set_all(self, value: int):
        for i, (scale, value_var) in enumerate(self.scales, start=1):
            scale.set(value)
            value_var.set(value)
            if self.send_on_change.get():
                self.on_servo_change(i, value)
        self.status_var.set(f"All servos set to {value}")

    def print_values(self):
        values = [int(float(scale.get())) for scale, _ in self.scales]
        print(f"Servo pulses: {values}")
        self.status_var.set(f"Printed values to console: {values}")

    def on_servo_change(self, servo_index: int, pulse: int):
        """
        Hook for your serial code.
        Called 300ms after last slider move (debounced) or immediately by buttons.
        """
        # Acquire the same shared lock used by MotorControllerFrame
        lock = getattr(self, "_serial_lock", None)
        if lock is not None:
            try:
                with lock:
                    self._send_servo_command(servo_index, pulse)
            except Exception as e:
                # Keep UI responsive even if serial fails
                self.status_var.set(f"Servo {servo_index} send failed: {e}")
        else:
            # Fallback (shouldn't happen): send without lock
            self._send_servo_command(servo_index, pulse)

    def _send_servo_command(self, servo_index: int, pulse: int):
        if self.parent._driver:
            self.parent._driver.move_serial_servo(servo_index, pulse, 500)


class MotorControllerFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.parent = parent
        self.status = tk.StringVar(value="Motor Controller Ready")

        self.motors = {}  # list of IntVar for Motor 1..4

        self.poll_interval_ms = 750  # overall cadence per full cycle
        self._poll_q = queue.Queue()  # data from worker -> UI
        self._stop_ev = threading.Event()  # stop signal for worker thread
        self._poll_thread = None

        lf = ttk.LabelFrame(self, text="Motor Controls")
        lf.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.columnconfigure(0, weight=1)

        for i in range(4):
            self._make_motor_row(lf, i + 1, row=i)

        ttk.Label(self, textvariable=self.status, anchor="w").grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )

        # Start background worker and UI queue draining
        self._poll_thread = threading.Thread(target=self._poll_worker, daemon=True)
        self._poll_thread.start()
        self.after(50, self._drain_poll_queue)

        # Ensure clean stop when this frame is destroyed
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _make_motor_row(self, parent, idx: int, row: int):
        ttk.Label(parent, text=f"Motor {idx}:").grid(
            row=row, column=0, padx=6, pady=6, sticky="w"
        )

        rpm_var = tk.DoubleVar(value=0.0)
        ttk.Label(parent, textvariable=rpm_var, width=8, anchor="e").grid(
            row=row, column=1, padx=6
        )
        ttk.Label(parent, text="RPM").grid(row=row, column=2, padx=4)

        # Control buttons
        btns = ttk.Frame(parent)
        btns.grid(row=row, column=3, padx=6)
        ttk.Button(btns, text="Stop", command=lambda i=idx: self._set_speed(i, 0)).pack(
            side="left", padx=2
        )
        ttk.Button(
            btns, text="Fwd", command=lambda i=idx: self._set_speed(i, 700)
        ).pack(side="left", padx=2)
        ttk.Button(
            btns, text="Rev", command=lambda i=idx: self._set_speed(i, -700)
        ).pack(side="left", padx=2)
        ttk.Button(
            btns, text="Accel", command=lambda i=idx: self._adjust_speed(i, +100)
        ).pack(side="left", padx=2)
        ttk.Button(
            btns, text="Decel", command=lambda i=idx: self._adjust_speed(i, -100)
        ).pack(side="left", padx=2)

        self.motors[idx] = [0, rpm_var]

    def _set_speed(self, motor_idx: int, value: int):
        value = max(-2000, min(2000, int(value)))
        self.motors[motor_idx][0] = value

        self.status.set(f"Motor {motor_idx} set to {value} RPM")
        try:
            with self.parent._serial_lock:
                if self.parent._driver:
                    self.parent._driver.set_motor_speed(motor_idx, value)  # type: ignore
        except Exception as e:
            self.status.set(f"Set speed failed (M{motor_idx}): {e}")

    def _adjust_speed(self, motor_idx: int, delta: int):
        cur, _ = self.motors[motor_idx]
        self._set_speed(motor_idx, cur + int(delta))

    def _poll_worker(self):
        """
        Poll each motor in round-robin order.
        Do ALL blocking serial I/O here; UI updates happen via queue -> after().
        """
        # per-motor stagger so a full cycle ~ poll_interval_ms
        while not self._stop_ev.is_set():
            rpm = None
            try:
                with self.parent._serial_lock:
                    rpms = self._safe_read_rpm()
            except Exception:
                rpms = [None, None, None, None]

            for i, rpm in enumerate(rpms):
                # enqueue result for UI thread
                self._poll_q.put((i + 1, rpm))

            time.sleep(self.poll_interval_ms / 1000.0)

    def _safe_read_rpm(self):
        """
        Replace with your real serial read.
        Must be fast-ish or have an internal timeout.
        Return int (RPM) or None if not available.
        """
        # Example placeholder: echo last known value so UI is stable without hardware.
        self.parent._driver.get_encoder_values()  # type: ignore
        last = self.parent._driver.get_latest_rpm()  # type: ignore
        return last

    def _drain_poll_queue(self):
        try:
            while True:
                idx, rpm = self._poll_q.get_nowait()
                if rpm is not None and 1 <= idx <= len(self.motors.items()):
                    # rpm = float(max(-205, min(205, rpm)))
                    self.motors[idx][1].set(f"{rpm:0.2f}")
        except queue.Empty:
            pass
        # re-arm if widget still exists
        if self.winfo_exists() and not self._stop_ev.is_set():
            self.after(50, self._drain_poll_queue)

    def _on_destroy(self, _event=None):
        # Signal worker to stop; thread is daemon so app exit is not blocked
        self._stop_ev.set()


class SettingsFrame(ttk.Frame):
    """Settings panel for configuring serial connection."""

    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent, padding=16)
        self.status_var = status_var
        self.parent = parent

        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Serial Settings", font=("", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        ttk.Label(self, text="Port:").grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.serial_port_var = tk.StringVar(
            value="/dev/tty.usbserial-2130"
        )  # adjust default for your system
        self.serial_entry = ttk.Entry(self, textvariable=self.serial_port_var)
        self.serial_entry.grid(row=1, column=1, sticky="ew", pady=4)

        btns = ttk.Frame(self)
        btns.grid(row=1, column=2, padx=(8, 0))
        ttk.Button(btns, text="Connect", command=self._on_connect).pack(
            side="left", padx=2
        )
        ttk.Button(btns, text="Disconnect", command=self._on_disconnect).pack(
            side="left", padx=2
        )

    def _on_connect(self):
        port = self.serial_port_var.get().strip()
        if not port:
            self.status_var.set("Please enter a serial port before connecting.")
            return
        self.parent._driver = Driver(port, report=True)
        self.status_var.set(f"Connected to {port} (UI only).")

    def _on_disconnect(self):
        if self.parent._driver:
            self.parent._driver.close()
            self.parent._driver = None
        self.status_var.set("Disconnected.")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transbot Control Panel")
        self.geometry("1020x380")
        self.resizable(False, False)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Layout: left sidebar, right content
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # Sidebar
        sidebar = ttk.Frame(root, width=180, padding=12)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        ttk.Label(sidebar, text="Controllers", font=("", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        self.view_var = tk.StringVar(value="settings")

        ttk.Radiobutton(
            sidebar,
            text="Settings",
            value="settings",
            variable=self.view_var,
            command=self._switch_view,
        ).pack(anchor="w", pady=4)
        ttk.Radiobutton(
            sidebar,
            text="Servo Controller",
            value="servo",
            variable=self.view_var,
            command=self._switch_view,
        ).pack(anchor="w", pady=4)
        ttk.Radiobutton(
            sidebar,
            text="Motor Controller",
            value="motor",
            variable=self.view_var,
            command=self._switch_view,
        ).pack(anchor="w", pady=4)

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", pady=12)
        self.status_var = tk.StringVar(value="Select a controller from the left.")
        ttk.Label(
            sidebar,
            textvariable=self.status_var,
            wraplength=150,
            anchor="w",
            justify="left",
        ).pack(fill="x")

        # Content area (stacked frames)
        self.content = ttk.Frame(root, padding=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

        # create shared props
        setattr(self.content, "_serial_lock", threading.Lock())
        setattr(self.content, "_driver", None)

        # Existing views
        self.settings_view = SettingsFrame(self.content, self.status_var)
        self.servo_view = ServoControllerFrame(self.content)
        self.motor_view = MotorControllerFrame(self.content)

        # Stack all views; raise the selected one
        for f in (self.settings_view, self.servo_view, self.motor_view):
            f.grid(row=0, column=0, sticky="nsew")

        self._switch_view()  # show default

    def _switch_view(self):
        view = self.view_var.get()
        if view == "servo":
            self.servo_view.tkraise()
            self.status_var.set("Servo Controller active.")
        elif view == "motor":
            self.motor_view.tkraise()
            self.status_var.set("Motor Controller active.")
        else:
            self.settings_view.tkraise()
            self.status_var.set("Open Settings to configure serial port.")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
