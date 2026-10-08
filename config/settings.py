import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasındaki gizli anahtarları sisteme yükle
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.path.join(BASE_DIR, "guardian.db")
RECOVERY_FILE_PATH = os.path.join(BASE_DIR, "recovery_state.json")

# RAWG API Anahtarını güvenli şekilde al
RAWG_API_KEY = os.getenv("RAWG_API_KEY")

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