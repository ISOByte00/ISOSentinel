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
                        return data
            except json.JSONDecodeError:
                pass # Dosya bozulmuşsa görmezden gel
        return None