import sys
from PyQt6.QtWidgets import QApplication

from database.database import init_db
from core.event_bus import bus
import restrictions.process_guard as guard
from ui.dashboard.dashboard import DashboardWindow

def setup_events():
    """Modülleri Event Bus üzerinden birbirine bağlar (Orkestrasyon)"""
    bus.subscribe("SESSION_STARTED", guard.on_session_started)
    bus.subscribe("SESSION_STOPPED", guard.on_session_stopped)
    bus.subscribe("GUARD_TICK", guard.on_guard_tick)
    print("Olay Veriyolu (Event Bus) baglantilari tamamlandi.")

def main():
    print("YKS Sentinel Başlatılıyor...")
    
    # 1. Veritabanını hazırla
    init_db()
    
    # 2. Event Bus (Olay Veriyolu) dinleyicilerini bağla
    setup_events()
    
    # 3. Arayüzü Başlat
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    
    # Uygulamayı döngüye sok
    sys.exit(app.exec())

if __name__ == "__main__":
    main()