import json
import os
from config.settings import RECOVERY_FILE_PATH

class RecoveryManager:
    @staticmethod
    def save_state(session_id: int, subject: str, topic: str, remaining_seconds: int):
        """Oturumun anlık kalp atışını (heartbeat) kaydeder."""
        data = {
            "session_id": session_id,
            "subject": subject,
            "topic": topic,
            "remaining_seconds": remaining_seconds,
            "status": "STUDYING"
        }
        # Geçici bir dosyaya yazıp sonra ismini değiştirmek (Atomic Write)
        # çökme anında dosyanın yarım yazılmasını engeller.
        temp_path = RECOVERY_FILE_PATH + ".tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            os.replace(temp_path, RECOVERY_FILE_PATH)
        except Exception as e:
            print(f"[Recovery Error] State kaydedilemedi: {e}")

    @staticmethod
    def clear_state():
        """Oturum temiz kapandığında kurtarma dosyasını siler."""
        if os.path.exists(RECOVERY_FILE_PATH):
            try:
                os.remove(RECOVERY_FILE_PATH)
            except Exception:
                pass

    @staticmethod
    def get_pending_recovery():
        """Yarım kalan, kurtarılmayı bekleyen bir oturum var mı diye bakar."""
        if os.path.exists(RECOVERY_FILE_PATH):
            try:
                with open(RECOVERY_FILE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if data.get("status") == "STUDYING":
                        # VERİTABANINDAN DOĞRULAMA (JSON var ama DB 'COMPLETED' dediyse iptal et)
                        from database.repositories.session_repository import SessionRepository
                        repo = SessionRepository()
                        session = repo.get_session(data.get("session_id"))
                        
                        if session and session.status != "STUDYING":
                            RecoveryManager.clear_state() # Yalan alarm, sil gitsin
                            return None
                            
                        return data
            except Exception:
                pass
        return None