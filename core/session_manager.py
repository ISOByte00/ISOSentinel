import time

from database.repositories.session_repository import SessionRepository
from database.models import StudySession
from core.event_bus import bus
from core.states import SessionState, VALID_TRANSITIONS, StateTransitionError
from core.recovery import RecoveryManager


class SessionController:
    def __init__(self):
        self.active_session_id = None
        self.state = SessionState.IDLE
        self.repo = SessionRepository()

        # Gerçek çalışma süresini hesaplamak için
        self._started_monotonic = None
        self._recovered_elapsed_seconds = 0

    def _change_state(self, new_state: SessionState):
        if new_state not in VALID_TRANSITIONS[self.state]:
            raise StateTransitionError(
                f"GECERSIZ DURUM GECISI: "
                f"{self.state.name} -> {new_state.name}"
            )

        old_state = self.state
        self.state = new_state

        print(
            f"[FSM] State Degisti: "
            f"{old_state.name} -> {self.state.name}"
        )

        bus.publish(
            "STATE_CHANGED",
            {
                "old": old_state.name,
                "new": self.state.name,
                "session_id": self.active_session_id,
            },
        )

    def start_session(self, subject, topic, duration):
        """
        Yeni çalışma oturumu başlatır.
        """

        # Aynı anda ikinci session açılmasını engelle
        if (
            self.state != SessionState.IDLE
            or self.active_session_id is not None
        ):
            return

        self._change_state(SessionState.STUDYING)

        new_session = StudySession(
            id=None,
            subject=subject,
            topic=topic,
            planned_duration=duration,
            status=self.state.value,
        )

        self.active_session_id = self.repo.create_session(new_session)

        self._started_monotonic = time.monotonic()
        self._recovered_elapsed_seconds = 0

        print(
            f"OTURUM BASLADI: {subject} - {topic} "
            f"({duration} dk) | ID: {self.active_session_id}"
        )

        bus.publish(
            "SESSION_STARTED",
            {
                "session_id": self.active_session_id
            },
        )

        # İlk recovery state
        RecoveryManager.save_state(
            self.active_session_id,
            subject,
            topic,
            duration * 60,
        )

    def stop_session(self, interrupted=False):
        """
        Aktif oturumu COMPLETED veya INTERRUPTED olarak kapatır.
        """

        if self.active_session_id is None:
            return

        session_id = self.active_session_id

        next_state = (
            SessionState.INTERRUPTED
            if interrupted
            else SessionState.COMPLETED
        )

        # FSM geçişi
        self._change_state(next_state)

        # Veritabanı durumunu güncelle
        self.repo.update_session_status(
            session_id,
            next_state.value,
        )

        # Gerçek çalışma süresini hesapla
        actual_seconds = self._get_elapsed_seconds()
        actual_minutes = actual_seconds // 60

        self.repo.update_actual_duration(
            session_id,
            actual_minutes,
        )

        print(
            f"OTURUM BİTTİ. "
            f"(Durum kayıt edildi: {next_state.value}, "
            f"Gerçek süre: {actual_minutes} dk)"
        )

        # Process Guard ve diğer modüllere bildir
        bus.publish(
            "SESSION_STOPPED",
            {
                "session_id": session_id,
                "status": next_state.value,
            },
        )

        # FSM tekrar IDLE
        self._change_state(SessionState.IDLE)

        # Aktif session temizle
        self.active_session_id = None
        self._started_monotonic = None
        self._recovered_elapsed_seconds = 0

        # Recovery artık gereksiz
        RecoveryManager.clear_state()

    def resume_session(self, session_id, remaining_seconds=None):
        """
        Çöken bir oturumu yeni DB kaydı oluşturmadan kurtarır.
        """

        if (
            self.state != SessionState.IDLE
            or self.active_session_id is not None
        ):
            return

        # Session gerçekten mevcut mu?
        session = self.repo.get_session(session_id)

        if session is None:
            raise ValueError(
                "Kurtarılacak oturum veritabanında bulunamadı."
            )

        # Sadece STUDYING session kurtarılabilir
        if session.status != SessionState.STUDYING.value:
            raise ValueError(
                "Kurtarılacak oturum artık STUDYING durumunda değil."
            )

        self.active_session_id = session_id

        self._change_state(SessionState.STUDYING)

        self._started_monotonic = time.monotonic()

        # Recovery'den önce ne kadar süre çalışılmıştı?
        if remaining_seconds is None:
            remaining_seconds = session.planned_duration * 60

        planned_seconds = session.planned_duration * 60

        self._recovered_elapsed_seconds = max(
            0,
            planned_seconds - int(remaining_seconds),
        )

        print(
            f"OTURUM KURTARILDI: "
            f"ID: {self.active_session_id}"
        )

        bus.publish(
            "SESSION_STARTED",
            {
                "session_id": self.active_session_id
            },
        )

    def mark_as_interrupted(self, session_id):
        """
        Recovery kullanıcı tarafından reddedilirse
        session INTERRUPTED yapılır.
        """

        if session_id is None:
            return

        session = self.repo.get_session(session_id)

        if session is None:
            RecoveryManager.clear_state()
            return

        self.repo.update_session_status(
            session_id,
            SessionState.INTERRUPTED.value,
        )

        RecoveryManager.clear_state()

        print(
            f"OTURUM İPTAL EDİLDİ "
            f"(Kurtarılmadı): ID: {session_id}"
        )

    def _get_elapsed_seconds(self):
        """
        Session'ın toplam gerçek çalışma süresini saniye olarak döndürür.
        Recovery öncesindeki süre + restart sonrası süre.
        """

        if self._started_monotonic is None:
            return self._recovered_elapsed_seconds

        current_elapsed = max(
            0,
            int(
                time.monotonic()
                - self._started_monotonic
            ),
        )

        return (
            self._recovered_elapsed_seconds
            + current_elapsed
        )