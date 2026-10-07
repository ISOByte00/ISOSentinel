"""
Configuration settings for YKS Sentinel.
Handles loading and validation of app, restriction, and health guardrail configurations.
"""
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class PomodoroSettings(BaseModel):
    study_duration_minutes: int = Field(default=25, ge=1, le=120)
    short_break_minutes: int = Field(default=5, ge=1, le=60)
    long_break_minutes: int = Field(default=15, ge=1, le=60)
    pomodoros_until_long_break: int = Field(default=4, ge=1, le=10)


class HealthGuardrailSettings(BaseModel):
    max_daily_study_minutes: int = Field(default=420, ge=60, le=900)
    mandatory_break_minutes: int = Field(default=10, ge=0, le=60)
    sleep_start: str = Field(default="23:30")
    sleep_end: str = Field(default="07:00")


class ProcessGuardSettings(BaseModel):
    enabled: bool = True
    scan_interval_seconds: float = Field(default=1.5, ge=0.5, le=10.0)
    heartbeat_interval_seconds: int = Field(default=5, ge=1, le=60)
    clock_skew_threshold_seconds: int = Field(default=10, ge=2, le=300)


class AppSettings(BaseModel):
    app_name: str = "YKS Sentinel"
    version: str = "0.1.0"
    db_path: Path = Path(__file__).resolve().parent.parent / "guardian.db"
    policies_path: Path = Path(__file__).resolve().parent / "policies.json"
    subjects_path: Path = Path(__file__).resolve().parent / "subjects.json"
    
    pomodoro: PomodoroSettings = Field(default_factory=PomodoroSettings)
    health: HealthGuardrailSettings = Field(default_factory=HealthGuardrailSettings)
    process_guard: ProcessGuardSettings = Field(default_factory=ProcessGuardSettings)


# Singleton instance
settings = AppSettings()