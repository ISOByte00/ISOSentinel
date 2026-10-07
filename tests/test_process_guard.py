import json
from pathlib import Path
import pytest
from database.database import DatabaseManager
from database.repositories import ViolationRepository
from restrictions.process_guard import ProcessGuard


@pytest.fixture
def guard_env(tmp_path):
    db_path = tmp_path / "test_guard.db"
    policies_path = tmp_path / "policies.json"

    policies_data = {
        "version": "1.0",
        "blocked_apps": [
            {
                "name": "calc.exe",
                "paths": [],
                "sha256": [],
                "action": "kill",
                "enabled": True,
                "reason": "Test Block Rule"
            },
            {
                "name": "notepad.exe",
                "paths": [],
                "sha256": [],
                "action": "kill",
                "enabled": False,
                "reason": "Disabled Rule"
            }
        ],
        "allowlist": [
            "python.exe",
            "pytest.exe"
        ]
    }
    with open(policies_path, "w", encoding="utf-8") as f:
        json.dump(policies_data, f)

    mgr = DatabaseManager(db_path)
    mgr.initialize()
    v_repo = ViolationRepository(mgr)
    guard = ProcessGuard(v_repo, policies_path=policies_path)
    return guard, v_repo


def test_guard_policy_loading(guard_env):
    guard, v_repo = guard_env
    # Only enabled rule should be in active blocked_apps
    assert len(guard.blocked_apps) == 1
    assert guard.blocked_apps[0]["name"] == "calc.exe"
    assert "python.exe" in guard.allowlist
