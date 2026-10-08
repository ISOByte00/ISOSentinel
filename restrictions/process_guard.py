import psutil
import hashlib
import os
import pefile
import requests
import urllib3
from database.repositories.guard_repository import GuardRepository
from database.models import Violation, ProcessCacheItem
from config.settings import RAWG_API_KEY

# GPT Eleştirisi 1 Çözümü: Artık isim değiştirmek (Spoofing) işe yaramayacak
# Çünkü sistem sadece exe ismine değil, şirkete veya yola bakarak karar verecek.

TRUSTED_COMPANIES = [
    "microsoft", "nvidia", "amd", "intel", "voidtools", 
    "logitech", "realtek", "tailscale", "google", "mozilla",
    "asus", "gigabyte", "msi", "corsair", "razer", "brave",
    "docker inc", "discord inc", "discord", "spotify",
    "kristjan skutta", # wallpaper engine yapımcısı
    "team ts3", "overwolf", "obs project", "git for windows",
    "python software foundation"
]

SAFE_PATHS = [
    "c:\\windows", "system32", "program files\\google\\chrome", 
    "program files (x86)\\google\\chrome", "brave-browser", 
    "microsoft\\edge", "microsoft vs code", "docker", "wsl", "git"
]

# GPT Eleştirisi 2 Çözümü: Game Zones daraltıldı ve akıllandı.
GAME_ZONES = [
    "steamapps\\common", "riot games", "epic games", "xboxgames", 
    "origin games", "ea games", "ubisoft",
    "roblox", ".minecraft", "curseforge", "ftb", 
    "technic", "tlauncher", "osu!"
]

# RAWG API'de yanlış eşleşmeyi önleyecek isimler ve jenerikler
NON_GAME_WORDS = ["launcher", "setup", "service", "helper", "installer", "client", "updater", "overlay", "renderer", "crashhandler", "system", "host", "daemon"]

repo = GuardRepository()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_active_session_id = None

# Performans Optimizasyonu için RAM (Memory) Cache Sözlüğü
# Aynı dosya için tekrar tekrar disk IO yapılmasını ve hash hesaplanmasını engeller.
_ram_cache = {}

def get_fast_file_signature(file_path):
    """Dosyanın boyutu ve değiştirilme tarihi ile hızlı bir imza oluşturur."""
    try:
        stat = os.stat(file_path)
        return f"{stat.st_size}_{stat.st_mtime}"
    except Exception:
        return ""

def get_file_hash(file_path):
    if not os.path.exists(file_path): return ""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception: return ""

def get_forensic_data(file_path):
    data = {
        "original_filename": "", "product_name": "", 
        "company_name": "", "file_description": "", "file_size": 0
    }
    try:
        data["file_size"] = os.path.getsize(file_path)
        pe = pefile.PE(file_path, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
        
        if hasattr(pe, 'FileInfo'):
            for fileinfo in pe.FileInfo:
                for info in fileinfo:
                    if hasattr(info, 'StringTable'):
                        for st in info.StringTable:
                            for entry in st.entries.items():
                                key = entry[0].decode('utf-8', 'ignore')
                                val = entry[1].decode('utf-8', 'ignore')
                                if key == 'OriginalFilename': data["original_filename"] = val
                                elif key == 'ProductName': data["product_name"] = val
                                elif key == 'CompanyName': data["company_name"] = val
                                elif key == 'FileDescription': data["file_description"] = val
    except Exception: pass
    return data

def check_if_game_via_api(process_name):
    if not RAWG_API_KEY: return False
    clean_name = process_name.replace(".exe", "").strip()
    
    # API'nin aptallaşmasını engelle
    if any(word in clean_name for word in NON_GAME_WORDS): return False

    url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&search={clean_name}&page_size=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=2, verify=False)
        if response.status_code == 200:
            data = response.json()
            if data.get("count", 0) > 0:
                top_game = data["results"][0]
                top_name = top_game["name"].lower()
                
                if clean_name == top_name or (len(clean_name) > 3 and clean_name in top_name and not any(w in top_name for w in NON_GAME_WORDS)):
                    print(f"  └── [API TESPİT] '{clean_name}' OYUN olarak doğrulandı! RAWG: '{top_game['name']}'")
                    return True
    except Exception: pass
    return False

def scan_and_kill(session_id):
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            exe_path = proc.info.get('exe')
            if not exe_path: continue
                
            exe_path = exe_path.lower()
            process_name = proc.info['name'].lower()

            # GPT 4 Çözümü: PERFORMANS OPTİMİZASYONU
            # Dosya değişmediyse ağır işlemlere (hash, pefile, api) girmeden ram_cache'ten dön.
            fast_sig = get_fast_file_signature(exe_path)
            if exe_path in _ram_cache and _ram_cache[exe_path]['sig'] == fast_sig:
                if _ram_cache[exe_path]['status'] == 'ALLOWED':
                    continue
                elif _ram_cache[exe_path]['status'] == 'BLOCKED':
                    # Spam'i azaltmak için sadece kill diyoruz, print basmıyoruz
                    proc.kill() 
                    continue

            # Dosya ilk defa görülüyor veya değişmiş!
            file_hash = get_file_hash(exe_path)
            
            # --- ZIRH 1: MUTLAK HASH KONTROLÜ (Spoofing Koruması) ---
            if repo.check_if_hash_is_blocked(file_hash):
                proc.kill()
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': 'BLOCKED'}
                print(f"[IHLAL - HASH TESPİTİ] ({process_name}) Yakalandı!")
                continue

            # Veritabanı Cache Kontrolü (Hash Doğrulamalı)
            db_cache = repo.get_cached_item(exe_path)
            if db_cache and db_cache["file_hash"] == file_hash:
                status = db_cache["status"]
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}
                if status == 'BLOCKED': proc.kill()
                continue

            # --- ARTIK BU YEPYENİ BİR DOSYA, ANALİZ BAŞLIYOR ---
            
            forensics = get_forensic_data(exe_path)
            company = forensics.get("company_name", "").lower()
            is_temp_file = exe_path.endswith('.tmp') or exe_path.endswith('.temp')

            # ZIRH 2: PE HEURISTIC ONAYI (En güvenilir karar)
            if not is_temp_file and any(trusted in company for trusted in TRUSTED_COMPANIES):
                status = 'ALLOWED'
                repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status=status))
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}
                print(f"[OTOMATİK İZİN - PE HEURISTIC] {process_name} ({company}) güvenilir üretici olarak onaylandı.")
                continue

            # ZIRH 3: KESİN MASUMLAR (Safe Paths)
            if any(safe_path in exe_path for safe_path in SAFE_PATHS):
                status = 'ALLOWED'
                repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status=status))
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}
                continue

            # ZIRH 4: KESİN SUÇLULAR (Game Zones)
            if any(zone in exe_path for zone in GAME_ZONES):
                # Roblox özel kontrolü
                if "roblox" in company or "roblox" in exe_path:
                    status = 'BLOCKED'
                    proc.kill()
                    repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status=status))
                    _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}
                    repo.log_violation(Violation(id=None, session_id=session_id, process_name=process_name, process_path=exe_path, file_hash=file_hash, severity="HIGH"))
                    print(f"[IHLAL - GAME ZONE] {process_name} (Roblox) yakalandı!")
                    continue

                # Eğer şirket güvenilir değilse ve Game Zone içindeyse, VUR!
                # (Wallpaper engine vb. güvenilir olduğu için Zırh 2'den geçip buraya inmeyecek)
                status = 'BLOCKED'
                proc.kill()
                repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status=status))
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}
                repo.log_violation(Violation(id=None, session_id=session_id, process_name=process_name, process_path=exe_path, file_hash=file_hash, severity="HIGH"))
                print(f"[IHLAL - GAME ZONE] {process_name} yakalandı ve genetiği çıkarıldı!")
                continue

            # ZIRH 5: GRİ ALAN - API SORGUSU
            print(f"[API SORGUSU] '{process_name}' inceleniyor...")
            if check_if_game_via_api(process_name):
                status = 'BLOCKED'
                proc.kill()
                repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status=status))
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}
                repo.log_violation(Violation(id=None, session_id=session_id, process_name=process_name, process_path=exe_path, file_hash=file_hash, severity="HIGH"))
                print(f"[IHLAL - API TESPİTİ] {process_name} yakalandı ve genetiği çıkarıldı!")
            else:
                status = 'ALLOWED'
                repo.set_cached_status(ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status=status))
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def on_session_started(data):
    global _active_session_id
    _active_session_id = data.get("session_id")
    print(f"[Process Guard] Korumalar Aktif! (Session ID: {_active_session_id})")

def on_session_stopped(data):
    global _active_session_id
    _active_session_id = None
    # Oturum bittiğinde RAM Cache'i temizle ki sonraki oturumda veritabanıyla temiz bir başlangıç yapılsın.
    _ram_cache.clear()
    print("[Process Guard] Korumalar Devre Dışı Bırakıldı ve RAM Cache Temizlendi.")

def on_guard_tick(data):
    if _active_session_id:
        scan_and_kill(_active_session_id)