"""
Process Guard for YKS Sentinel.
Scans and terminates blocked applications during active study sessions.
"""
import os
import json
import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
import psutil

from database.models import Violation
from database.repositories import ViolationRepository
from core.event_bus import event_bus
from config.settings import settings

logger = logging.getLogger(__name__)


class ProcessGuard:
    def __init__(self, violation_repo: ViolationRepository, policies_path: Optional[Path] = None):
        self.violation_repo = violation_repo
        self.policies_path = policies_path or settings.policies_path
        self._running = False
        self._active_session_id: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Policy rules & allowlists
        self.blocked_apps: List[dict] = []
        self.allowlist: Set[str] = set()
        self._hash_cache: Dict[str, str] = {}  # {path: sha256}
        self.current_pid = os.getpid()

        self.reload_policies()

    def reload_policies(self):
        """Loads or reloads policies from policies.json."""
        with self._lock:
            try:
                if self.policies_path.exists():
                    with open(self.policies_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.blocked_apps = [
                            app for app in data.get("blocked_apps", []) if app.get("enabled", True)
                        ]
                        self.allowlist = {name.lower() for name in data.get("allowlist", [])}
                        logger.info(f"Loaded {len(self.blocked_apps)} active policies from {self.policies_path}")
            except Exception as e:
                logger.error(f"Failed to load policies from {self.policies_path}: {e}")

    def set_active_session(self, session_id: Optional[int]):
        """Sets the currently active study session ID for violation tagging."""
        self._active_session_id = session_id

    def start(self):
        """Starts background scanning thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        logger.info("ProcessGuard started.")

    def stop(self):
        """Stops background scanning."""
        self._running = False
        logger.info("ProcessGuard stopped.")

    def _get_file_sha256(self, filepath: str) -> Optional[str]:
        """Calculates and caches SHA-256 hash of an executable."""
        if filepath in self._hash_cache:
            return self._hash_cache[filepath]
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            digest = h.hexdigest().lower()
            self._hash_cache[filepath] = digest
            return digest
        except Exception:
            return None

    def scan_once(self) -> List[Violation]:
        """Performs a single scan iteration across all running processes."""
        violations_found = []
        with self._lock:
            active_rules = list(self.blocked_apps)

        if not active_rules:
            return violations_found

        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                pid = proc.info['pid']
                if pid == self.current_pid or pid <= 4:  # Ignore self and system idle/kernel
                    continue

                name = (proc.info['name'] or "").lower()
                exe_path = proc.info['exe'] or ""

                if name in self.allowlist:
                    continue

                # Match against blocked apps
                for rule in active_rules:
                    rule_name = rule.get("name", "").lower()
                    if name != rule_name:
                        continue

                    # 1. Path check if specified in rule
                    rule_paths = [p.lower() for p in rule.get("paths", [])]
                    if rule_paths and exe_path.lower() not in rule_paths:
                        continue

                    # 2. SHA256 check if specified in rule
                    rule_hashes = [h.lower() for h in rule.get("sha256", [])]
                    if rule_hashes and exe_path:
                        file_hash = self._get_file_sha256(exe_path)
                        if file_hash not in rule_hashes:
                            continue

                    # Match confirmed! Terminate process
                    action = rule.get("action", "kill")
                    reason = rule.get("reason", f"Yasaklı uygulama algılandı: {proc.info['name']}")
                    
                    try:
                        proc.kill()
                        logger.warning(f"ProcessGuard killed: {name} (PID: {pid}) | Reason: {reason}")
                    except Exception as kill_err:
                        logger.error(f"Failed to kill process {pid}: {kill_err}")

                    violation = Violation(
                        study_session_id=self._active_session_id,
                        rule_name=rule.get("name", name),
                        process_name=proc.info['name'],
                        executable_path=exe_path,
                        process_hash=self._hash_cache.get(exe_path, ""),
                        severity="HIGH",
                        action_taken=action,
                        reason=reason,
                        detected_at=None
                    )
                    saved_violation = self.violation_repo.record_violation(violation)
                    violations_found.append(saved_violation)
                    event_bus.publish("VIOLATION_DETECTED", saved_violation)
                    break  # Matched one rule for this process, proceed to next process

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logger.error(f"Unexpected error inspecting process: {e}")

        return violations_found

    def _scan_loop(self):
        interval = settings.process_guard.scan_interval_seconds
        while self._running:
            self.scan_once()
            time.sleep(interval)