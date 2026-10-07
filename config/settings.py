import os

# Proje ana dizinini bulur
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Veritabanı dosyasının yolu
DB_PATH = os.path.join(BASE_DIR, "guardian.db")

# Pomodoro Süreleri (Dakika)
POMODORO_WORK_MIN = 25
POMODORO_SHORT_BREAK_MIN = 5
POMODORO_LONG_BREAK_MIN = 15

# Acil Durum Dokunulmazları (Process Guard bu isimleri pas geçer)
GLOBAL_WHITELIST = [
    "wallpaper32.exe",
    "wallpaper64.exe",
    "explorer.exe",
    "dwm.exe"
]