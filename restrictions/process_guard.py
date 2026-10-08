import psutil
from database.repositories.guard_repository import GuardRepository
from database.models import Violation, ProcessCacheItem
from config.settings import GLOBAL_WHITELIST

import hashlib
import os

def get_file_hash(file_path):
    """Bir dosyanın SHA-256 özet değerini (parmak izini) hesaplar."""
    if not os.path.exists(file_path):
        return ""
    
    sha256_hash = hashlib.sha256()
    try:
        # Dosyayı parça parça oku ki büyük dosyalarda RAM patlamasın
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        # İzin hatası (PermissionError) vb. olursa boş dön
        return ""

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

            # 0. Aşama: Dokunulmazlar Listesi
            if process_name in GLOBAL_WHITELIST:
                continue

            # 1. Aşama: Gelişmiş Cache Kontrolü (Sadece isme değil, YOL'a bak)
            # Artık sahte bir isim bile olsa, farklı yoldan çalışıyorsa cache'e yakalanmaz.
            cached_status = repo.get_cached_status(exe_path) 
            
            if cached_status == 'ALLOWED':
                continue
            if cached_status == 'BLOCKED':
                proc.kill()
                # Dosya yolunu bildiğimiz için hemen hash'ini de çıkarıp logluyoruz
                file_hash = get_file_hash(exe_path)
                repo.log_violation(Violation(
                    id=None, session_id=session_id, process_name=process_name, 
                    process_path=exe_path, file_hash=file_hash, severity="HIGH"
                ))
                print(f"[IHLAL - CACHE] {process_name} yakalandı ve sonlandırıldı!")
                continue

            # 2. Aşama: Güvenli Klasörler (Sistem Dosyaları)
            if any(safe_path in exe_path for safe_path in SAFE_PATHS):
                # Hash hesaplamak sisteme yük bindirebilir diye güvenlilerde atlıyoruz
                repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash="", status='ALLOWED'))
                continue

            # 3. Aşama: Tehlikeli Klasörler ve Kaba Analiz
            if any(danger_zone in exe_path for danger_zone in DANGER_ZONES):
                proc.kill()
                
                # Sadece tehlikeli dosyalarda maliyetli Hash işlemini yapıyoruz!
                file_hash = get_file_hash(exe_path)
                
                # Yeni cache'i ismiyle değil, YOLUYLA kaydediyoruz.
                repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status='BLOCKED'))
                
                repo.log_violation(Violation(
                    id=None, session_id=session_id, process_name=process_name, 
                    process_path=exe_path, file_hash=file_hash, severity="HIGH"
                ))
                print(f"[IHLAL - YENİ TESPİT] {process_name} yakalandı ve sonlandırıldı!")
                continue

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        
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