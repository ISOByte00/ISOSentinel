import psutil
import hashlib
import os
import pefile
import requests
import urllib3
from database.repositories.guard_repository import GuardRepository
from database.models import Violation, ProcessCacheItem
from config.settings import RAWG_API_KEY

# Dokunulmaz Sistem ve Geliştirici Süreçleri
SYSTEM_DEV_WHITELIST = [
    "python.exe", "pythonw.exe", "git.exe", "code.exe", 
    "cmd.exe", "powershell.exe", "conhost.exe", "taskhostw.exe",
    "svchost.exe", "explorer.exe", "sihost.exe", "ctfmon.exe",
    "system", "idle", "registry", "vctip.exe",
    "docker.exe", "dockerd.exe", "docker-desktop.exe", 
    "wsl.exe", "vmmem", "com.docker.backend.exe", "wslhost.exe"
]

# Oyun İstemcileri ve Mağazalar (RAWG'ın 'oyun' sanıp vurmasını engellemek için)
LAUNCHER_WHITELIST = [
    "steam.exe", "steamwebhelper.exe", "steamservice.exe",
    "epicgameslauncher.exe", "epicwebhelper.exe",
    "uplay.exe", "ubisoftconnect.exe", "galaxyclient.exe"
]

# Bilinen Güvenilir Üreticiler
TRUSTED_COMPANIES = [
    "microsoft", "nvidia", "amd", "intel", "voidtools", 
    "logitech", "realtek", "tailscale", "google", "mozilla",
    "asus", "gigabyte", "msi", "corsair", "razer", "brave",
    "docker inc"
]

SAFE_PATHS = [
    "c:\\windows", "system32", "program files\\google\\chrome", 
    "program files (x86)\\google\\chrome", "brave-browser", 
    "microsoft\\edge", "microsoft vs code"
]

# Kesin Oyun Klasörleri (Gerçek oyun exeleri buradadır)
GAME_ZONES = [
    "steamapps\\common", "riot games", "epic games", "xboxgames", 
    "origin games", "ea games", "ubisoft",
    "roblox", ".minecraft", "curseforge", "ftb", 
    "technic", "tlauncher", "osu!"
]

# RAWG API'de yanlış eşleşmeyi önleyecek jenerik/tehlikeli sözcükler
GENERIC_NON_GAME_WORDS = ["launcher", "setup", "service", "helper", "installer", "client", "updater"]

repo = GuardRepository()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_active_session_id = None

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

def build_cache_item(proc, exe_path, file_hash, status, forensics=None):
    item = ProcessCacheItem(process_name=exe_path, file_hash=file_hash, status=status)
    if not forensics: forensics = get_forensic_data(exe_path)
        
    item.original_filename = forensics.get("original_filename", "")
    item.product_name = forensics.get("product_name", "")
    item.company_name = forensics.get("company_name", "")
    item.file_size = forensics.get("file_size", 0)
    
    if status == 'BLOCKED':
        try:
            parent = proc.parent()
            item.parent_process = parent.name() if parent else "Bilinmiyor"
        except Exception:
            item.parent_process = "Bilinmiyor"
            
    return item

def check_if_game_via_api(process_name):
    if not RAWG_API_KEY: return False
        
    clean_name = process_name.replace(".exe", "").strip()
    
    # Jenerik isimleri API oyun sanmasın
    if any(word in clean_name for word in GENERIC_NON_GAME_WORDS):
        return False

    url = f"https://api.rawg.io/api/games?key={RAWG_API_KEY}&search={clean_name}&page_size=1"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=3, verify=False)
        if response.status_code == 200:
            data = response.json()
            if data.get("count", 0) > 0:
                top_game = data["results"][0]
                top_name = top_game["name"].lower()
                
                # Tam isim veya güçlü isim eşleşmesi
                if clean_name == top_name or (len(clean_name) > 3 and clean_name in top_name and not any(w in top_name for w in GENERIC_NON_GAME_WORDS)):
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

            # 0. SİSTEM, DEV SÜREÇLERİ VE OYUN LAUNCHER'LARI
            if process_name in SYSTEM_DEV_WHITELIST or process_name in LAUNCHER_WHITELIST:
                continue

            # 1. PATH CACHE KONTROLÜ
            cached_status = repo.get_cached_status(exe_path) 
            if cached_status == 'ALLOWED': continue
            if cached_status == 'BLOCKED':
                proc.kill()
                continue

            file_hash = get_file_hash(exe_path)
            
            # 2. HASH (PARMAK İZİ) KONTROLÜ
            if repo.check_if_hash_is_blocked(file_hash):
                proc.kill()
                repo.set_cached_status(build_cache_item(proc, exe_path, file_hash, 'BLOCKED'))
                print(f"[IHLAL - HASH TESPİTİ] İsim Değiştirme Yakalandı! ({process_name})")
                continue

            # 3. KESİN MASUMLAR
            if any(safe_path in exe_path for safe_path in SAFE_PATHS):
                repo.set_cached_status(build_cache_item(proc, exe_path, file_hash, 'ALLOWED'))
                continue

            # 4. KESİN SUÇLULAR (OYUN KLASÖRLERİ)
            if any(zone in exe_path for zone in GAME_ZONES):
                proc.kill()
                repo.set_cached_status(build_cache_item(proc, exe_path, file_hash, 'BLOCKED'))
                repo.log_violation(Violation(id=None, session_id=session_id, process_name=process_name, process_path=exe_path, file_hash=file_hash, severity="HIGH"))
                print(f"[IHLAL - GAME ZONE] {process_name} yakalandı ve genetiği çıkarıldı!")
                continue

            # 5. PE FORENSIC SÜZGEÇ (Giriş: .tmp dosyaları bu kontrolü bypass edemez)
            forensics = get_forensic_data(exe_path)
            company = forensics.get("company_name", "").lower()
            
            is_temp_file = exe_path.endswith('.tmp') or exe_path.endswith('.temp')
            
            if not is_temp_file and any(trusted in company for trusted in TRUSTED_COMPANIES):
                repo.set_cached_status(build_cache_item(proc, exe_path, file_hash, 'ALLOWED', forensics))
                print(f"[OTOMATİK İZİN - PE HEURISTIC] {process_name} ({company}) güvenilir üretici olarak onaylandı.")
                continue

            # Roblox Özel PE Kontrolü
            if "roblox" in company:
                proc.kill()
                repo.set_cached_status(build_cache_item(proc, exe_path, file_hash, 'BLOCKED', forensics))
                repo.log_violation(Violation(id=None, session_id=session_id, process_name=process_name, process_path=exe_path, file_hash=file_hash, severity="HIGH"))
                print(f"[IHLAL - PE HEURISTIC] {process_name} (Roblox) yakalandı!")
                continue

            # 6. GRİ ALAN - API SORGUSU
            print(f"[API SORGUSU] '{process_name}' inceleniyor...")
            if check_if_game_via_api(process_name):
                proc.kill()
                repo.set_cached_status(build_cache_item(proc, exe_path, file_hash, 'BLOCKED', forensics))
                repo.log_violation(Violation(id=None, session_id=session_id, process_name=process_name, process_path=exe_path, file_hash=file_hash, severity="HIGH"))
                print(f"[IHLAL - API TESPİTİ] {process_name} yakalandı ve genetiği çıkarıldı!")
            else:
                repo.set_cached_status(build_cache_item(proc, exe_path, file_hash, 'ALLOWED', forensics))

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def on_session_started(data):
    global _active_session_id
    _active_session_id = data.get("session_id")
    print(f"[Process Guard] Korumalar Aktif! (Session ID: {_active_session_id})")

def on_session_stopped(data):
    global _active_session_id
    _active_session_id = None
    print("[Process Guard] Korumalar Devre Dışı Bırakıldı.")

def on_guard_tick(data):
    if _active_session_id:
        scan_and_kill(_active_session_id)