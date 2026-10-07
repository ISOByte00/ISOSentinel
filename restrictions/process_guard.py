import psutil
import time
from database.database import get_connection

# Asla dokunulmayacak Windows ve sistem yolları (Donanımı ve sistemi korumak için)
SAFE_PATHS = [
    "c:\\windows",
    "c:\\program files\\windows",
    "c:\\program files (x86)\\windows",
    "system32"
]

# İçinde oyun veya dikkat dağıtıcı olduğu kesin olan "Kırmızı Alarm" yolları
DANGER_ZONES = [
    "steamapps",
    "riot games",
    "epic games",
    "xboxgames",
    "origin games",
    "ea games",
    "ubisoft"
]

def log_violation(session_id, process_name, severity="HIGH"):
    """İhlali veritabanına kaydeder."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO violations (session_id, process_name, severity)
        VALUES (?, ?, ?)
    """, (session_id, process_name, severity))
    conn.commit()
    conn.close()
    print(f"[IHLAL] {process_name} yakalandı ve sonlandırıldı!")

def get_cached_status(process_name):
    """Bir process'in daha önce öğrenilip öğrenilmediğini veritabanından çeker."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM process_cache WHERE process_name = ?", (process_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['status']
    return None

def set_cached_status(process_name, status):
    """Sistemin öğrendiği process'i hafızaya kaydeder ('ALLOWED' veya 'BLOCKED')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO process_cache (process_name, status, last_checked)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (process_name, status))
    conn.commit()
    conn.close()

def scan_and_kill(session_id):
    """Aktif süreçleri tarar. Güvenli yolları atlar, tehlikeli yolları avlar."""
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            exe_path = proc.info.get('exe')
            if not exe_path:
                continue
                
            exe_path = exe_path.lower()
            process_name = proc.info['name'].lower()

            # 1. Aşama: Bu işlemi daha önce gördük mü?
            cached_status = get_cached_status(process_name)
            if cached_status == 'ALLOWED':
                continue
            if cached_status == 'BLOCKED':
                proc.kill()
                log_violation(session_id, process_name)
                continue

            # 2. Aşama: Windows veya Sistem dosyası mı? (Hemen Güvenli işaretle)
            if any(safe_path in exe_path for safe_path in SAFE_PATHS):
                set_cached_status(process_name, 'ALLOWED')
                continue

            # 3. Aşama: Klasör Avcılığı (Oyun platformları)
            if any(danger_zone in exe_path for danger_zone in DANGER_ZONES):
                set_cached_status(process_name, 'BLOCKED')
                proc.kill()
                log_violation(session_id, process_name)
                continue

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass