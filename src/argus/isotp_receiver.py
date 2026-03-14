import can
import sys
import time
import queue
import threading

from typing import Optional, Callable


class IsoTpReceiver:
    """
    Minimal ISO-TP receiver (11-bit IDs) using python-can only.

    Data frames (SF/FF/CF) arrive on data_id.
    Flow-Control (CTS) is sent on fc_id.

    This mirrors many MCU demos that use two 11-bit IDs:
      data_id = 0x702  (peer sends SF/FF/CF here)
      fc_id   = 0x701  (we reply FC(CTS) here)

    fc_dispatch_id / fc_dispatch_queue: when set, frames arriving on
    fc_dispatch_id are forwarded into fc_dispatch_queue instead of being
    discarded. A paired IsoTpSender sharing the same bus reads FC frames from
    that queue, so both objects can coexist on a single can.Bus without racing
    on bus.recv().
    """

    # PCI types
    PCI_SF = 0x0
    PCI_FF = 0x1
    PCI_CF = 0x2
    PCI_FC = 0x3

    # FC statuses
    FC_CTS = 0x0
    FC_WT = 0x1
    FC_OVFL = 0x2

    def __init__(
        self,
        bus,
        rx_id: int = 0x702,
        fc_id: int = 0x701,
        on_message: Optional[Callable[[bytes], None]] = None,
        cf_timeout_s: float = 0.5,
        send_stmin_ms: int = 0,
        fc_dispatch_id: Optional[int] = None,
        fc_dispatch_queue: Optional[queue.Queue] = None,
    ):
        self.bus = bus
        self.data_id = rx_id
        self.fc_id = fc_id
        self.on_message = on_message or (
            lambda payload: print(f"[RX] {payload.hex()}  |  {repr(payload)}")
        )
        self.cf_timeout_s = cf_timeout_s
        self.send_stmin_ms = max(
            0, min(127, int(send_stmin_ms))
        )  # 0..127 ms per ISO-TP

        self._fc_dispatch_id = fc_dispatch_id
        self._fc_dispatch_queue = fc_dispatch_queue

        # Reassembly state
        self._lock = threading.Lock()
        self._active = False
        self._expect_len = 0
        self._buf = bytearray()
        self._next_sn = 1
        self._last_cf_time = 0.0

        # Thread
        self._running = False
        self._t: Optional[threading.Thread] = None

    def _send_fc_cts(self):
        # bytes: [ PCI=0x30 | BS=0 | STmin=self.send_stmin_ms ]
        data = bytes([(self.PCI_FC << 4) | self.FC_CTS, 0x00, self.send_stmin_ms])
        msg = can.Message(arbitration_id=self.fc_id, is_extended_id=False, data=data)
        try:
            self.bus.send(msg)
        except can.CanError as e:
            print(f"[WARN] FC(CTS) send failed: {e}", file=sys.stderr)

    def _handle_sf(self, frame: can.Message):
        sfl = frame.data[0] & 0x0F
        if sfl == 0 or sfl > 7 or sfl > frame.dlc - 1:
            return
        payload = bytes(frame.data[1 : 1 + sfl])
        self.on_message(payload)

    def _handle_ff(self, frame: can.Message):
        if frame.dlc < 8:
            return
        total_len = ((frame.data[0] & 0x0F) << 8) | frame.data[1]
        if total_len <= 0:
            return

        with self._lock:
            self._active = True
            self._expect_len = total_len
            self._buf.clear()
            self._buf.extend(frame.data[2:8])  # 6 bytes in FF
            self._next_sn = 1
            self._last_cf_time = time.monotonic()

        self._send_fc_cts()

    def _handle_cf(self, frame: can.Message):
        if frame.dlc < 2:
            return
        sn = frame.data[0] & 0x0F

        deliver_payload = None
        with self._lock:
            if not self._active:
                return

            now = time.monotonic()
            if (now - self._last_cf_time) > self.cf_timeout_s:
                self._active = False
                self._buf.clear()
                return

            if sn != self._next_sn:
                self._active = False
                self._buf.clear()
                return

            remain = self._expect_len - len(self._buf)
            take = min(remain, frame.dlc - 1)
            if take > 0:
                self._buf.extend(frame.data[1 : 1 + take])

            self._next_sn = (self._next_sn + 1) & 0x0F
            self._last_cf_time = now

            if len(self._buf) >= self._expect_len:
                deliver_payload = bytes(self._buf[: self._expect_len])
                self._active = False
                self._buf.clear()

        if deliver_payload is not None:
            self.on_message(deliver_payload)

    def _loop(self):
        while self._running:
            try:
                frame = self.bus.recv(timeout=0.1)
            except Exception as e:
                print(f"[ERR] CAN recv error: {e}", file=sys.stderr)
                continue
            if frame is None or frame.dlc == 0:
                continue

            if frame.arbitration_id == self.data_id:
                pci = frame.data[0] >> 4
                if pci == self.PCI_SF:
                    self._handle_sf(frame)
                elif pci == self.PCI_FF:
                    self._handle_ff(frame)
                elif pci == self.PCI_CF:
                    self._handle_cf(frame)
            elif (
                self._fc_dispatch_id is not None
                and frame.arbitration_id == self._fc_dispatch_id
                and self._fc_dispatch_queue is not None
            ):
                # Forward FC frames to the paired sender instead of discarding them.
                self._fc_dispatch_queue.put(frame)

            with self._lock:
                if self._active and (time.monotonic() - self._last_cf_time) > self.cf_timeout_s:
                    self._active = False
                    self._buf.clear()

    def start(self):
        if self._running:
            return
        self._running = True
        self._t = threading.Thread(target=self._loop, name="isotp-rx", daemon=True)
        self._t.start()

    def stop(self):
        self._running = False
        t = self._t
        if t and t.is_alive():
            t.join(timeout=1.0)
