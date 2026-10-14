from core.event_bus import bus

class LockManager:
    """
    Oturum sırasındaki kilit durumunu yönetir.
    Oturum başladığında sistem kilitlerini aktif eder, 
    oturum bittiğinde tüm kilitleri güvenle kaldırır.
    """
    def __init__(self):
        self.is_locked = False
        self.active_session_id = None

    def acquire_lock(self, session_id: int):
        """Kilitleri devreye sokar."""
        if self.is_locked:
            return

        self.is_locked = True
        self.active_session_id = session_id
        
        # Gelecekte eklenecek sistem düzeyi kilitler (Örn: Task Manager kısıtlaması, Alt+Tab / Win tuşu engelleri)
        print(f"[LOCK MANAGER] Oturum Kilitleri Aktif Edildi! (Session ID: {session_id})")

    def release_lock(self):
        """Tüm kilitleri kaldırır ve sistemi serbest bırakır."""
        if not self.is_locked:
            return

        self.is_locked = False
        self.active_session_id = None
        
        # Tüm kilitleri kaldır
        print("[LOCK MANAGER] Oturum Kilitleri Kaldırıldı. Sistem Serbest.")

    def on_session_started(self, data: dict):
        session_id = data.get("session_id")
        if session_id:
            self.acquire_lock(session_id)

    def on_session_stopped(self, data: dict):
        self.release_lock()

lock_manager = LockManager()