class EventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type: str, callback):
        """Bir olaya abone olur."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, data=None):
        """Sisteme bir olay fırlatır."""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(data)

# Tüm sistemde tek bir haberleşme ağı (Singleton) olması için global instance
bus = EventBus()