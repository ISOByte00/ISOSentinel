from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class StudySession:
    id: Optional[int]
    subject: str
    topic: str
    planned_duration: int
    actual_duration: int = 0
    status: str = 'PLANNED'
    created_at: Optional[datetime] = None

@dataclass
class Violation:
    id: Optional[int]
    session_id: int
    process_name: str
    process_path: str
    file_hash: str
    severity: str = 'HIGH'
    timestamp: Optional[datetime] = None

@dataclass
class QuestionBatch:
    id: Optional[int]
    session_id: int
    subject: str
    topic: str
    correct_count: int = 0
    wrong_count: int = 0
    empty_count: int = 0
    timestamp: Optional[datetime] = None

@dataclass
class ProcessCacheItem:
    process_name: str
    file_hash: str
    status: str
    # YENİ: Adli Bilişim (Forensics) Verileri
    original_filename: str = ""
    product_name: str = ""
    company_name: str = ""
    file_size: int = 0
    parent_process: str = ""