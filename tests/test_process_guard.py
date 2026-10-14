import os
import pytest
from unittest.mock import patch
from database.repositories.guard_repository import GuardRepository
from database.models import ProcessCacheItem
from core.policy_engine import PolicyEngine, PolicyDecision
import restrictions.process_guard as guard

class FakeProcess:
    def __init__(self, pid: int, name: str, exe: str, parent_name: str = "explorer.exe"):
        self.pid = pid
        self._name = name
        self._exe = exe
        self._parent_name = parent_name
        self.killed = False

    @property
    def info(self):
        return {'pid': self.pid, 'name': self._name, 'exe': self._exe}

    def name(self):
        return self._name

    def exe(self):
        return self._exe

    def parent(self):
        if self._parent_name:
            return FakeProcess(9999, self._parent_name, f"c:\\windows\\{self._parent_name}", parent_name=None)
        return None

    def kill(self):
        self.killed = True

@pytest.fixture(autouse=True)
def clean_guard_state():
    guard.clear_ram_cache()
    yield
    guard.clear_ram_cache()

@pytest.fixture
def temp_repo(tmp_path):
    db_file = str(tmp_path / "test_guard_integration.db")
    repo = GuardRepository(db_path=db_file)
    repo.create_tables()
    return repo

@pytest.fixture
def engine(temp_repo):
    return PolicyEngine(api_key=None, repo=temp_repo)

def test_scan_and_kill_blocks_game_and_logs(temp_repo, engine, tmp_path):
    """Oyun klasöründeki sahte süreç engellenmeli, öldürülmeli ve DB'ye BLOCK olarak kaydedilmeli."""
    fake_exe = str(tmp_path / "steamapps" / "common" / "my_game" / "game.exe")
    os.makedirs(os.path.dirname(fake_exe), exist_ok=True)
    with open(fake_exe, "wb") as f:
        f.write(b"fake_game_content_xyz")

    proc = FakeProcess(pid=1001, name="game.exe", exe=fake_exe)

    guard.scan_and_kill(
        session_id=1,
        repo_override=temp_repo,
        engine_override=engine,
        process_iter_fn=lambda: [proc]
    )

    # 1. Süreç öldürülmüş olmalı
    assert proc.killed is True

    # 2. DB Cache BLOCK olarak kaydedilmiş olmalı
    cached = temp_repo.get_cached_item(fake_exe.lower())
    assert cached is not None
    assert cached["status"] == "BLOCK"

    # 3. Hash BLOCK olarak işaretlenmiş olmalı
    file_hash = guard.get_file_hash(fake_exe)
    assert temp_repo.check_if_hash_is_blocked(file_hash) is True

    # 4. İhlal tablosuna yazılmış olmalı
    with temp_repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, process_name, process_path, severity FROM violations WHERE session_id = 1")
        row = cursor.fetchone()
    assert row is not None
    assert row[0] == 1
    assert row[1] == "game.exe"
    assert row[2] == fake_exe.lower()
    assert row[3] == "HIGH"

def test_scan_and_kill_detects_copied_file_by_hash(temp_repo, engine, tmp_path):
    """
    3. Koşul: Engellenen bir dosya farklı bir yola kopyalandığında 
    aynı hash ile tanınmalı ve öldürülmeli.
    """
    game_exe = str(tmp_path / "steamapps" / "common" / "game" / "original.exe")
    copied_exe = str(tmp_path / "innocent_folder" / "study_helper.exe")
    os.makedirs(os.path.dirname(game_exe), exist_ok=True)
    os.makedirs(os.path.dirname(copied_exe), exist_ok=True)

    # İki dosya da birebir aynı içeriğe (dolayısıyla aynı hash'e) sahip
    binary_data = b"super_secret_game_code_hash_test"
    with open(game_exe, "wb") as f:
        f.write(binary_data)
    with open(copied_exe, "wb") as f:
        f.write(binary_data)

    proc1 = FakeProcess(pid=2001, name="original.exe", exe=game_exe)

    # İlk tarama: original.exe oyun klasöründe yakalanır ve BLOCK yapılır
    guard.scan_and_kill(
        session_id=5,
        repo_override=temp_repo,
        engine_override=engine,
        process_iter_fn=lambda: [proc1]
    )
    assert proc1.killed is True

    # RAM cache'i temizleyip yeni bir süreci simüle ediyoruz
    guard.clear_ram_cache()

    # İkinci tarama: study_helper.exe innocent_folder içinde, oyun klasöründe DEĞİL!
    # Ancak hash'i daha önce engellenmiş olan original.exe ile aynı.
    proc2 = FakeProcess(pid=2002, name="study_helper.exe", exe=copied_exe)
    guard.scan_and_kill(
        session_id=5,
        repo_override=temp_repo,
        engine_override=engine,
        process_iter_fn=lambda: [proc2]
    )

    # Kopya dosya hash eşleşmesi sayesinde yakalanmalı ve öldürülmeli
    assert proc2.killed is True

    # Kopya dosyanın da ihlali loglanmış olmalı
    with temp_repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT process_name, process_path FROM violations WHERE process_name = 'study_helper.exe'")
        row = cursor.fetchone()
    assert row is not None
    assert row[0] == "study_helper.exe"
    assert row[1] == copied_exe.lower()

def test_db_cache_recognizes_legacy_blocked_record(temp_repo, engine, tmp_path):
    """
    2. Koşul: Eski DB'de 'BLOCKED' olarak kayıtlı olan bir süreç 
    yeni Process Guard tarafından da tanınmalı ve öldürülmeli.
    """
    legacy_exe = str(tmp_path / "legacy_app" / "retro.exe")
    os.makedirs(os.path.dirname(legacy_exe), exist_ok=True)
    with open(legacy_exe, "wb") as f:
        f.write(b"retro_game_data")

    legacy_hash = guard.get_file_hash(legacy_exe)

    # Eski sürümün doğrudan yazdığı BLOCKED kaydı
    with temp_repo.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO process_cache (process_name, file_hash, status)
            VALUES (?, ?, ?)
        ''', (legacy_exe.lower(), legacy_hash, "BLOCKED"))
        conn.commit()

    proc = FakeProcess(pid=3001, name="retro.exe", exe=legacy_exe)

    guard.scan_and_kill(
        session_id=10,
        repo_override=temp_repo,
        engine_override=engine,
        process_iter_fn=lambda: [proc]
    )

    assert proc.killed is True

def test_ram_cache_blocks_without_calling_engine(temp_repo, engine, tmp_path):
    """RAM cache'te BLOCK olan süreç doğrudan öldürülmeli ve motor tekrar çağrılmamalı."""
    fake_exe = str(tmp_path / "cached_game.exe")
    with open(fake_exe, "wb") as f:
        f.write(b"cached_game_bytes")

    sig = guard.get_fast_file_signature(fake_exe)
    guard._ram_cache[fake_exe.lower()] = {'sig': sig, 'status': PolicyDecision.BLOCK.value}

    proc = FakeProcess(pid=4001, name="cached_game.exe", exe=fake_exe)

    with patch.object(engine, 'evaluate') as mock_eval:
        guard.scan_and_kill(
            session_id=20,
            repo_override=temp_repo,
            engine_override=engine,
            process_iter_fn=lambda: [proc]
        )
        assert proc.killed is True
        mock_eval.assert_not_called()

def test_session_lifecycle_clears_ram_cache():
    """Oturum durdurulduğunda RAM cache sıfırlanmalı."""
    guard._ram_cache["c:\\some\\path.exe"] = {'sig': "123_456", 'status': "ALLOW"}
    assert len(guard._ram_cache) == 1

    guard.on_session_stopped({})
    assert len(guard._ram_cache) == 0
    assert guard._active_session_id is None
