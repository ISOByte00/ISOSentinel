import sys
from PyQt6.QtWidgets import QApplication
from database.database import init_db
from ui.dashboard.dashboard import DashboardWindow

def main():
    print("YKS Sentinel Başlatılıyor...")
    
    # Veritabanını hazırla
    init_db()
    
    # Arayüzü Başlat
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    
    # Uygulamayı döngüye sok
    sys.exit(app.exec())

if __name__ == "__main__":
    main()