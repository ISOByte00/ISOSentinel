# 🛡️ YKS Sentinel — Autonomous Study Guardian (v0.1 MVP)
YKS Sentinel, YKS (Yükseköğretim Kurumları Sınavı) hazırlık sürecini planlama, odak koruma, kısıtlama denetimi ve analitik zinciri olarak yöneten bir **çalışma işletim sistemi**dir.
---
## 🚀 Başlangıç ve Çalıştırma
### 1. Sanal Ortamı Aktif Edin
```powershell
.\.venv\Scripts\Activate.ps1
```
### 2. Uygulamayı Başlatın
```powershell
python main.py
```
### 3. Testleri Çalıştırın
```powershell
pytest -v
```
---
## 📦 V0.1 MVP Özellikleri
- **PyQt6 Modern Desktop UI**:
  - **Dashboard**: Pomodoro sayaç halkası, anlık çalışma durumu (State Badge), canlı istatistik kartları.
  - **Ajanda**: TYT/AYT ders ve konu seçimi, süreli çalışma oturumu başlatma, günlük oturum geçmişi.
  - **Soru & İstatistik**: Toplu (batch) soru girişi (`40/32/6/2`), anlık ve deterministik Net hesabı (`Doğru - Yanlış/4`).
  - **İhlaller & Güvenlik**: Engellenen süreçlerin listesi ve "Neden?" (Reason) gerekçe paneli, sistem audit günlüğü.
  - **Ayarlar**: Pomodoro süreleri, sağlıklı çalışma sınırları (uyku penceresi, maks çalışma) ve yasaklı uygulama kural yönetimi.
- **Çekirdek & Durum Yönetimi (Core)**:
  - Deterministik State Machine (`IDLE` ➔ `PREPARING` ➔ `STUDY` ➔ `BREAK` ➔ `COMPLETED` / `INTERRUPTED` / `RECOVERY` / `ERROR`).
  - Thread-safe Event Bus ile modüller arası gevşek bağlılık (decoupled).
  - Startup Crash Recovery: Beklenmedik kapanma sonrası yarım kalan oturumları otomatik kurtarma.
- **Process Guard & Anti-Bypass**:
  - `psutil` ile `Name` + `Path` + `SHA-256` kontrol zinciri.
  - Self-PID ve dahili allowlist koruması.
  - Process/Path bazlı SHA256 önbellekleme (Cache).
  - Sistem başlangıç/kapanış audit (`STARTED` ➔ `HEARTBEAT` ➔ `CLEAN_EXIT` / `UNEXPECTED_SHUTDOWN`).
  - Monotonic zaman sapması ile saat manipülasyonu (`CLOCK_CHANGED`) tespiti.
- **Deterministik Analitik**:
  - Tek merkezden hesaplanan Focus Score (`analytics/focus_score.py`).