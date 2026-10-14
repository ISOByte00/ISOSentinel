import sys
from PyQt6.QtWidgets import QApplication
from ui.dashboard.dashboard import DashboardWindow
from core.event_bus import bus
import restrictions.process_guard as guard
from core.lock_manager import lock_manager

from database.database import init_db

def setup_events():
    # Process Guard Dinleyicileri
    bus.subscribe("SESSION_STARTED", guard.on_session_started)
    bus.subscribe("SESSION_STOPPED", guard.on_session_stopped)
    bus.subscribe("GUARD_TICK", guard.on_guard_tick)
    
    # Lock Manager Dinleyicileri
    bus.subscribe("SESSION_STARTED", lock_manager.on_session_started)
    bus.subscribe("SESSION_STOPPED", lock_manager.on_session_stopped)
    
    print("Olay Veriyolu (Event Bus) baglantilari tamamlandi.")

def main():
    print("YKS Sentinel Başlatılıyor...")
    
    # 1. Veritabanını hazırla ve tabloları/migrasyonları çalıştır
    init_db()
    
    app = QApplication(sys.argv)
    
    # 2. Event Bus (Olay Veriyolu) dinleyicilerini bağla
    setup_events()
    
    # 3. Arayüzü Başlat
    window = DashboardWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
