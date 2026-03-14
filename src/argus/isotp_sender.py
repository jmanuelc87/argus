import can
import time
import queue

from typing import Optional


class IsoTpSender:
    """
    Minimal ISO-TP sender (11-bit IDs) using python-can only.

    Frames:
      - DATA (SF/FF/CF) go to tx_id
      - Flow Control (FC) is expected to arrive on fc_id

    This matches a common embedded pattern (data on one ID, FC on another).
    If your peer uses standard ISO-TP (single ID pair per direction).

    When fc_queue is provided, Flow Control frames are read from that queue
    instead of calling bus.recv(). This is required when a concurrent
    IsoTpReceiver thread is the sole bus.recv() caller on the shared bus.
    """

    PCI_SF = 0x0
    PCI_FF = 0x1
    PCI_CF = 0x2
    PCI_FC = 0x3

    FC_CTS = 0x0
    FC_WT = 0x1
    FC_OVF = 0x2

    def __init__(
        self,
        bus,
        tx_id: int = 0x700,
        fc_id: int = 0x701,
        fc_queue: Optional[queue.Queue] = None,
    ):
        self.bus = bus
        self.tx_id = tx_id
        self.fc_id = fc_id
        self._fc_queue = fc_queue

    def _send_frame(self, arb_id: int, data: bytes) -> None:
        msg = can.Message(arbitration_id=arb_id, is_extended_id=False, data=data)
        self.bus.send(msg)

    def _wait_fc_cts(self, timeout_s: float) -> Optional[int]:
        """
        Wait for Flow Control CTS on fc_id.
        Returns STmin (0..127 ms) if CTS received, else None.
        Reads from fc_queue if set, otherwise falls back to bus.recv().
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            remaining = max(0.001, deadline - time.monotonic())
            if self._fc_queue is not None:
                try:
                    frame = self._fc_queue.get(timeout=min(0.01, remaining))
                except queue.Empty:
                    continue
            else:
                frame = self.bus.recv(timeout=0.01)
                if frame is None:
                    continue
            if frame.arbitration_id != self.fc_id or frame.dlc < 3:
                continue
            pci = frame.data[0] >> 4
            fs = frame.data[0] & 0x0F
            if pci != self.PCI_FC:
                continue
            if fs == self.FC_CTS:
                return frame.data[2]
            if fs == self.FC_WT:
                # Receiver asks us to wait; keep looping until timeout.
                continue
            if fs == self.FC_OVF:
                return None
        return None

    def send(self, payload: bytes, timeout_s: float = 0.5) -> bool:
        """
        Send an ISO-TP message. Returns True on success, False on failure/timeout.

        - payload length 0..4095 (12-bit length field).
        - For len <= 7, sends a Single Frame (no FC needed).
        - For len > 7, sends FF then waits for FC(CTS), then streams CFs.
        - Honors STmin (0..127 ms) if provided by receiver.
        """
        if not payload:
            return True

        length = len(payload)
        if length <= 7:
            # Single Frame: [PCI | len][data...]
            sf = bytes([(self.PCI_SF << 4) | (length & 0x0F)]) + payload
            self._send_frame(self.tx_id, sf)
            return True

        if length > 4095:
            raise ValueError(
                "Payload too large for 12-bit ISO-TP length (max 4095 bytes)."
            )

        # First Frame: [PCI|len_hi][len_lo][6 data bytes] — always exactly 8 bytes
        ff0 = (self.PCI_FF << 4) | ((length >> 8) & 0x0F)
        ff1 = length & 0xFF
        ff = bytes([ff0, ff1]) + payload[:6]
        self._send_frame(self.tx_id, ff)
        offset = 6

        # Wait for Flow Control (CTS) before sending Consecutive Frames
        stmin = self._wait_fc_cts(timeout_s)
        if stmin is None:
            return False

        # Interpret STmin (0..127 ms). Ignore microsecond encodings (0xF1..0xF9).
        delay_ms = stmin if 0 <= stmin <= 127 else 0

        # Send Consecutive Frames: [PCI|SN][up to 7 data]
        sn = 1
        while offset < length:
            chunk = payload[offset : offset + 7]
            cf0 = (self.PCI_CF << 4) | (sn & 0x0F)
            frame = bytes([cf0]) + chunk
            self._send_frame(self.tx_id, frame)
            offset += len(chunk)
            sn = (sn + 1) & 0x0F

            if delay_ms:
                time.sleep(delay_ms / 1000.0)

        return True
