import psutil
from database.repositories.guard_repository import GuardRepository
from database.models import Violation, ProcessCacheItem
from config.settings import GLOBAL_WHITELIST

SAFE_PATHS = [
    "c:\\windows", "c:\\program files\\windows", "c:\\program files (x86)\\windows", "system32"
]
DANGER_ZONES = [
    "steamapps", "riot games", "epic games", "xboxgames", "origin games", "ea games", "ubisoft"
]

repo = GuardRepository()

def scan_and_kill(session_id):
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            exe_path = proc.info.get('exe')
            if not exe_path:
                continue
                
            exe_path = exe_path.lower()
            process_name = proc.info['name'].lower()

            # 0. Aşama: Dokunulmazlar Listesi (Wallpaper Engine vb.)
            if process_name in GLOBAL_WHITELIST:
                continue

            # 1. Aşama: Cache Kontrolü
            cached_status = repo.get_cached_status(process_name)
            if cached_status == 'ALLOWED':
                continue
            if cached_status == 'BLOCKED':
                proc.kill()
                repo.log_violation(Violation(
                    id=None, session_id=session_id, process_name=process_name, 
                    process_path=exe_path, file_hash="", severity="HIGH"
                ))
                print(f"[IHLAL] {process_name} yakalandı ve sonlandırıldı!")
                continue

            # 2. Aşama: Güvenli Klasörler
            if any(safe_path in exe_path for safe_path in SAFE_PATHS):
                repo.set_cached_status(ProcessCacheItem(process_name=process_name, file_hash="", status='ALLOWED'))
                continue

            # 3. Aşama: Tehlikeli Klasörler
            if any(danger_zone in exe_path for danger_zone in DANGER_ZONES):
                repo.set_cached_status(ProcessCacheItem(process_name=process_name, file_hash="", status='BLOCKED'))
                proc.kill()
                repo.log_violation(Violation(
                    id=None, session_id=session_id, process_name=process_name, 
                    process_path=exe_path, file_hash="", severity="HIGH"
                ))
                print(f"[IHLAL] {process_name} yakalandı ve sonlandırıldı!")
                continue

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

            # --- EVENT BUS LİSTENER'LARI ---
_active_session_id = None

def on_session_started(data):
    """EventBus: Oturum başladığında tetiklenir."""
    global _active_session_id
    _active_session_id = data.get("session_id")
    print(f"[Process Guard] Korumalar Aktif! (Session ID: {_active_session_id})")

def on_session_stopped(data):
    """EventBus: Oturum bittiğinde tetiklenir."""
    global _active_session_id
    print(f"[Process Guard] Korumalar Devre Dışı Bırakıldı.")
    _active_session_id = None

def on_guard_tick(data):
    """EventBus: Arayüzden gelen 2 saniyelik tarama tetiklemesi."""
    if _active_session_id:
        scan_and_kill(_active_session_id)