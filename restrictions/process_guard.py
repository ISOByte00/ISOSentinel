import psutil
import hashlib
import os
import pefile
from database.repositories.guard_repository import GuardRepository
from database.models import Violation, ProcessCacheItem
from config.settings import RAWG_API_KEY
from core.policy_engine import PolicyEngine, PolicyDecision

repo = GuardRepository()
policy_engine = PolicyEngine(api_key=RAWG_API_KEY, repo=repo)

_active_session_id = None
_ram_cache = {}

def get_fast_file_signature(file_path):
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

def scan_and_kill(session_id):
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            exe_path = proc.info.get('exe')
            if not exe_path: continue
                
            exe_path = exe_path.lower()
            process_name = proc.info['name'].lower()

            # 1. RAM CACHE KONTROLÜ (Hızlı Geçiş)
            fast_sig = get_fast_file_signature(exe_path)
            if exe_path in _ram_cache and _ram_cache[exe_path]['sig'] == fast_sig:
                if _ram_cache[exe_path]['status'] == PolicyDecision.ALLOW.value:
                    continue
                elif _ram_cache[exe_path]['status'] == PolicyDecision.BLOCK.value:
                    proc.kill()
                    continue

            file_hash = get_file_hash(exe_path)

            # 2. VERİTABANI CACHE KONTROLÜ
            db_cache = repo.get_cached_item(exe_path)
            if db_cache and db_cache["file_hash"] == file_hash:
                status = db_cache["status"]
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status}
                if status == PolicyDecision.BLOCK.value:
                    proc.kill()
                continue

            # 3. METADATA TOPLAMA (Adli Bilişim)
            forensics = get_forensic_data(exe_path)
            process_info = {
                "process_name": process_name,
                "exe_path": exe_path,
                "file_hash": file_hash,
                "company_name": forensics.get("company_name", ""),
                "product_name": forensics.get("product_name", ""),
                "file_size": forensics.get("file_size", 0)
            }

            # 4. POLICY ENGINE'E DANIŞMA
            eval_result = policy_engine.evaluate(process_info)

            # 5. EYLEM UYGULAMA (AKSİYON)
            if eval_result.decision == PolicyDecision.BLOCK:
                proc.kill()
                status_str = PolicyDecision.BLOCK.value
                
                repo.set_cached_status(ProcessCacheItem(
                    process_name=exe_path, 
                    file_hash=file_hash, 
                    status=status_str,
                    original_filename=forensics.get("original_filename", ""),
                    product_name=forensics.get("product_name", ""),
                    company_name=forensics.get("company_name", ""),
                    file_size=forensics.get("file_size", 0)
                ))
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status_str}

                repo.log_violation(Violation(
                    id=None, 
                    session_id=session_id, 
                    process_name=process_name, 
                    process_path=exe_path, 
                    file_hash=file_hash, 
                    severity=eval_result.severity
                ))
                print(f"[IHLAL - {eval_result.reason}] {process_name} engellendi!")

            elif eval_result.decision == PolicyDecision.ALLOW:
                status_str = PolicyDecision.ALLOW.value
                repo.set_cached_status(ProcessCacheItem(
                    process_name=exe_path, 
                    file_hash=file_hash, 
                    status=status_str
                ))
                _ram_cache[exe_path] = {'sig': fast_sig, 'status': status_str}

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def on_session_started(data):
    global _active_session_id
    _active_session_id = data.get("session_id")
    print(f"[Process Guard] Korumalar Aktif! (Session ID: {_active_session_id})")

def on_session_stopped(data):
    global _active_session_id
    _active_session_id = None
    _ram_cache.clear()
    print("[Process Guard] Korumalar Devre Dışı Bırakıldı ve RAM Cache Temizlendi.")

def on_guard_tick(data):
    if _active_session_id:
        scan_and_kill(_active_session_id)