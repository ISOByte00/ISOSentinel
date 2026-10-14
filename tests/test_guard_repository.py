import os
import sqlite3
import pytest
from database.repositories.guard_repository import GuardRepository
from database.models import Violation, ProcessCacheItem

@pytest.fixture
def temp_repo(tmp_path):
    db_file = str(tmp_path / "test_guardian.db")
    repo = GuardRepository(db_path=db_file)
    repo.create_tables()
    return repo

def test_empty_or_none_hash(temp_repo):
    assert temp_repo.check_if_hash_is_blocked(None) is False
    assert temp_repo.check_if_hash_is_blocked("") is False
    assert temp_repo.check_if_hash_is_blocked("non_existent_hash") is False

def test_new_version_block_status_found_in_hash_check(temp_repo):
    """1. Koşul: Yeni sürümün kaydettiği BLOCK kayıtları hash kontrolünde bulunmalı."""
    item = ProcessCacheItem(
        process_name="c:\\games\\evil_game.exe",
        file_hash="hash_evil_123",
        status="BLOCK",
        original_filename="evil.exe",
        product_name="Evil Game",
        company_name="Evil Inc",
        file_size=1024,
        parent_process="explorer.exe"
    )
    temp_repo.set_cached_status(item)

    # Hash kontrolünde BLOCK kaydı bulunmalı
    assert temp_repo.check_if_hash_is_blocked("hash_evil_123") is True

    # Cache kaydını get_cached_item ile okuduğumuzda da BLOCK olarak gelmeli
    cached = temp_repo.get_cached_item("c:\\games\\evil_game.exe")
    assert cached is not None
    assert cached["status"] == "BLOCK"
    assert cached["file_hash"] == "hash_evil_123"

def test_legacy_blocked_status_found_in_hash_check(temp_repo):
    """2. Koşul: Eski veritabanındaki BLOCKED kayıtları da güvenli biçimde desteklenmeli."""
    # Eski sürümün doğrudan yazdığı BLOCKED durumunu DB'ye ekleyelim (migrasyon öncesi simülasyonu)
    with temp_repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO process_cache (process_name, file_hash, status)
            VALUES (?, ?, ?)
        ''', ("c:\\old_games\\retro.exe", "hash_retro_999", "BLOCKED"))
        conn.commit()

    # Hash kontrolü BLOCKED durumunu tanımalı
    assert temp_repo.check_if_hash_is_blocked("hash_retro_999") is True

    # get_cached_item geriye dönük uyumlulukla normalize edilmiş BLOCK döndürmeli
    cached = temp_repo.get_cached_item("c:\\old_games\\retro.exe")
    assert cached is not None
    assert cached["status"] == "BLOCK"
    assert cached["file_hash"] == "hash_retro_999"

def test_legacy_status_migration(temp_repo):
    """2. Koşul devamı: migrate_cache_statuses() BLOCKED->BLOCK ve ALLOWED->ALLOW dönüşümünü yapmalı."""
    with temp_repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO process_cache (process_name, file_hash, status) VALUES ('p1', 'h1', 'BLOCKED')")
        cursor.execute("INSERT INTO process_cache (process_name, file_hash, status) VALUES ('p2', 'h2', 'ALLOWED')")
        cursor.execute("INSERT INTO process_cache (process_name, file_hash, status) VALUES ('p3', 'h3', 'BLOCK')")
        cursor.execute("INSERT INTO process_cache (process_name, file_hash, status) VALUES ('p4', 'h4', 'ALLOW')")
        conn.commit()

    temp_repo.migrate_cache_statuses()

    with temp_repo.get_connection() as conn:
        cursor = conn.cursor()
        rows = dict(cursor.execute("SELECT process_name, status FROM process_cache").fetchall())

    assert rows['p1'] == 'BLOCK'
    assert rows['p2'] == 'ALLOW'
    assert rows['p3'] == 'BLOCK'
    assert rows['p4'] == 'ALLOW'

def test_copied_file_recognized_by_same_hash(temp_repo):
    """3. Koşul: Engellenen bir dosya farklı bir yola kopyalandığında aynı hash ile tanınmalı."""
    original_path = "c:\\games\\rogue.exe"
    copied_path = "d:\\innocent_folder\\calculator.exe"
    same_hash = "sha256_identical_hash_abc"

    # İlk dosya yasaklanıyor
    temp_repo.set_cached_status(ProcessCacheItem(
        process_name=original_path,
        file_hash=same_hash,
        status="BLOCK"
    ))

    # Kopyalanan dosyanın yolu henüz cache'te yok
    assert temp_repo.get_cached_item(copied_path) is None

    # Ancak kopyalanan dosyanın hash'i sorgulandığında yasaklı olduğu anlaşılmalı
    assert temp_repo.check_if_hash_is_blocked(same_hash) is True

def test_log_violation(temp_repo):
    violation = Violation(
        id=None,
        session_id=42,
        process_name="game.exe",
        process_path="c:\\games\\game.exe",
        file_hash="hash_xyz",
        severity="HIGH"
    )
    temp_repo.log_violation(violation)

    with temp_repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, process_name, process_path, file_hash, severity FROM violations WHERE session_id = 42")
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == 42
    assert row[1] == "game.exe"
    assert row[2] == "c:\\games\\game.exe"
    assert row[3] == "hash_xyz"
    assert row[4] == "HIGH"
