"""
Audit Logger and Anti-Bypass Monitor for YKS Sentinel.
Handles system heartbeats, clean exit recording, and monotonic clock-skew detection.
"""
import time
import logging
import threading
from datetime import datetime
from database.repositories import SystemEventRepository
from core.event_bus import event_bus
from config.settings import settings

logger = logging.getLogger(__name__)


class AuditMonitor:
    def __init__(self, event_repo: SystemEventRepository):
        self.event_repo = event_repo
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_wall_time = time.time()
        self._last_monotonic = time.monotonic()
        self._heartbeat_counter = 0

    def start(self):
        """Starts background heartbeat and clock monitor thread."""
        if self._running:
            return
        self._running = True
        self._last_wall_time = time.time()
        self._last_monotonic = time.monotonic()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("AuditMonitor started.")

    def stop(self, is_clean: bool = True):
        """Stops background monitor and logs CLEAN_EXIT if requested."""
        self._running = False
        if is_clean:
            self.event_repo.record_event("CLEAN_EXIT", "Application closed normally by user/system.")
            logger.info("Recorded CLEAN_EXIT event.")

    def _monitor_loop(self):
        check_interval = 1.0  # Check every second
        heartbeat_interval = settings.process_guard.heartbeat_interval_seconds
        skew_threshold = settings.process_guard.clock_skew_threshold_seconds

        while self._running:
            time.sleep(check_interval)
            
            # 1. Clock skew / Tampering check
            curr_wall = time.time()
            curr_mono = time.monotonic()

            wall_diff = curr_wall - self._last_wall_time
            mono_diff = curr_mono - self._last_monotonic
            skew = abs(wall_diff - mono_diff)

            if skew > skew_threshold:
                details = f"Clock change detected: wall skew={skew:.2f}s (wall={wall_diff:.2f}s, mono={mono_diff:.2f}s)"
                logger.warning(details)
                self.event_repo.record_event("CLOCK_CHANGED", details)
                event_bus.publish("CLOCK_CHANGED", {"skew": skew, "details": details})

            self._last_wall_time = curr_wall
            self._last_monotonic = curr_mono

            # 2. Periodic Heartbeat
            self._heartbeat_counter += 1
            if self._heartbeat_counter >= heartbeat_interval:
                self._heartbeat_counter = 0
                self.event_repo.record_event("HEARTBEAT", f"Sentinel alive at {datetime.now().isoformat()}")
