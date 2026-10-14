import pytest
from core.policy_engine import PolicyEngine, PolicyDecision
from database.repositories.guard_repository import GuardRepository
from database.models import ProcessCacheItem

@pytest.fixture
def temp_repo(tmp_path):
    db_file = str(tmp_path / "test_policy.db")
    repo = GuardRepository(db_path=db_file)
    repo.create_tables()
    return repo

@pytest.fixture
def engine(temp_repo):
    return PolicyEngine(api_key=None, repo=temp_repo)

def test_hash_match_blocks_immediately(engine, temp_repo):
    """1. Kural: Hash daha önce engellendiyse anında BLOCK dönmeli."""
    temp_repo.set_cached_status(ProcessCacheItem(
        process_name="c:\\games\\blocked.exe",
        file_hash="hash_12345",
        status="BLOCK"
    ))

    result = engine.evaluate({
        "process_name": "blocked.exe",
        "exe_path": "c:\\games\\blocked.exe",
        "file_hash": "hash_12345"
    })

    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "HASH_MATCH"
    assert result.severity == "HIGH"

def test_hash_match_detects_copied_file(engine, temp_repo):
    """3. Koşul: Engellenen bir dosya farklı bir yola kopyalandığında aynı hash ile tanınmalı."""
    temp_repo.set_cached_status(ProcessCacheItem(
        process_name="c:\\games\\game.exe",
        file_hash="hash_stolen_binary",
        status="BLOCK"
    ))

    # Dosya adı ve yolu tamamen alakasız/masum bir yere kopyalanmış
    result = engine.evaluate({
        "process_name": "calc.exe",
        "exe_path": "d:\\my_work\\calc.exe",
        "file_hash": "hash_stolen_binary",
        "company_name": "Unknown"
    })

    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "HASH_MATCH"

def test_system_and_dev_whitelist(engine):
    """2. Kural: Sistem ve geliştirici süreçleri serbest olmalı."""
    dev_procs = ["python.exe", "git.exe", "code.exe", "cmd.exe", "powershell.exe", "dwm.exe", "wallpaper64.exe"]
    for proc in dev_procs:
        result = engine.evaluate({
            "process_name": proc,
            "exe_path": f"c:\\tools\\{proc}",
            "file_hash": "hash_safe"
        })
        assert result.decision == PolicyDecision.ALLOW
        assert result.reason == "WHITELIST_PROCESS"

def test_launcher_whitelist(engine):
    """2. Kural: Oyun istemcileri oyunun kendisi değildir, serbest bırakılmalı."""
    launchers = ["steam.exe", "epicgameslauncher.exe", "uplay.exe"]
    for launcher in launchers:
        result = engine.evaluate({
            "process_name": launcher,
            "exe_path": f"c:\\program files\\{launcher}",
            "file_hash": "hash_launcher"
        })
        assert result.decision == PolicyDecision.ALLOW
        assert result.reason == "WHITELIST_PROCESS"

def test_safe_paths(engine):
    """3. Kural: Windows veya standart güvenli yollardaki süreçler serbest olmalı."""
    result = engine.evaluate({
        "process_name": "some_tool.exe",
        "exe_path": "c:\\windows\\system32\\some_tool.exe",
        "file_hash": "hash_windows_tool"
    })
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason == "SAFE_PATH"

def test_game_zone_takes_precedence_over_trusted_companies(engine):
    """
    Öncelik Kuralı: Güvenilir üretici (örn: Microsoft) olsa bile, 
    oyun klasöründe bulunan oyunlar engellenmeli (GAME_ZONE_MATCH).
    """
    # Microsoft imzalı bir oyun xboxgames veya steamapps altında çalışıyor
    result = engine.evaluate({
        "process_name": "forza.exe",
        "exe_path": "c:\\program files\\xboxgames\\forzahorizon5\\forza.exe",
        "file_hash": "hash_forza_game",
        "company_name": "Microsoft Corporation"
    })
    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "GAME_ZONE_MATCH"

    # Steamapps altındaki Halo oyunu
    result_halo = engine.evaluate({
        "process_name": "halo.exe",
        "exe_path": "d:\\steam\\steamapps\\common\\halo\\halo.exe",
        "file_hash": "hash_halo_game",
        "company_name": "Microsoft"
    })
    assert result_halo.decision == PolicyDecision.BLOCK
    assert result_halo.reason == "GAME_ZONE_MATCH"

def test_trusted_company_allowed_outside_game_zones(engine):
    """Oyun klasörleri dışında çalışan güvenilir üretici yazılımları (Spotify, Discord, Logitech) serbest olmalı."""
    result = engine.evaluate({
        "process_name": "lghub.exe",
        "exe_path": "c:\\program files\\lghub\\lghub.exe",
        "file_hash": "hash_logitech",
        "company_name": "Logitech Inc."
    })
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason == "TRUSTED_COMPANY_HEURISTIC"

def test_wallpaper_engine_allowed_in_steamapps(engine):
    """Wallpaper Engine steamapps/common altında olsa bile dokunulmaz olmalı."""
    # wallpaper32.exe adı üzerinden
    result1 = engine.evaluate({
        "process_name": "wallpaper32.exe",
        "exe_path": "d:\\steam\\steamapps\\common\\wallpaper_engine\\wallpaper32.exe",
        "file_hash": "hash_wp32",
        "company_name": "Kristjan Skutta"
    })
    assert result1.decision == PolicyDecision.ALLOW
    assert result1.reason == "WHITELIST_PROCESS"

    # Kristjan Skutta şirket adı üzerinden
    result2 = engine.evaluate({
        "process_name": "ui32.exe",
        "exe_path": "d:\\steam\\steamapps\\common\\wallpaper_engine\\bin\\ui32.exe",
        "file_hash": "hash_wp_ui",
        "company_name": "Kristjan Skutta"
    })
    assert result2.decision == PolicyDecision.ALLOW
    assert result2.reason == "WHITELIST_PROCESS"

def test_roblox_detected(engine):
    """Roblox tespit edildiğinde ROBLOX_DETECTED sebebiyle engellenmeli."""
    result = engine.evaluate({
        "process_name": "robloxplayerbeta.exe",
        "exe_path": "c:\\users\\user\\appdata\\local\\roblox\\versions\\version-123\\robloxplayerbeta.exe",
        "file_hash": "hash_roblox",
        "company_name": "Roblox Corporation"
    })
    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "ROBLOX_DETECTED"

def test_default_allow(engine):
    """Hiçbir kurala takılmayan sıradan güvenli uygulamalar DEFAULT_ALLOW ile serbest bırakılmalı."""
    result = engine.evaluate({
        "process_name": "my_study_timer.exe",
        "exe_path": "c:\\tools\\my_study_timer.exe",
        "file_hash": "hash_timer_123",
        "company_name": "StudyDev"
    })
    assert result.decision == PolicyDecision.ALLOW
    assert result.reason == "DEFAULT_ALLOW"
