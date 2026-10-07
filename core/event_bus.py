"""
Event Bus for decoupled intra-application communication.
"""
import logging
import threading
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventBus:
    """Thread-safe publish-subscribe event bus."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_name: str, handler: Callable[[Any], None]):
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            if handler not in self._subscribers[event_name]:
                self._subscribers[event_name].append(handler)
                logger.debug(f"Subscribed {handler} to {event_name}")

    def unsubscribe(self, event_name: str, handler: Callable[[Any], None]):
        with self._lock:
            if event_name in self._subscribers and handler in self._subscribers[event_name]:
                self._subscribers[event_name].remove(handler)
                logger.debug(f"Unsubscribed {handler} from {event_name}")

    def publish(self, event_name: str, data: Any = None):
        with self._lock:
            handlers = list(self._subscribers.get(event_name, []))
            all_handlers = list(self._subscribers.get("*", []))

        logger.debug(f"Publishing event '{event_name}' with data: {data}")
        for handler in handlers + all_handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error handling event '{event_name}' in {handler}: {e}", exc_info=True)


# Global singleton EventBus
event_bus = EventBus()
